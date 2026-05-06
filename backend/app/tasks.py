"""Celery tasks for background scraping jobs."""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from celery import Celery
from sqlalchemy import select, update

from app.config import settings

logger = logging.getLogger(__name__)

celery_app = Celery("gunpladb", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)


def _get_sync_session():
    """Get a synchronous DB session for use inside Celery tasks."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    sync_url = settings.database_url.replace("+asyncpg", "").replace("asyncpg://", "postgresql://")
    # Use psycopg2-style sync URL
    sync_url = sync_url.replace("postgresql+asyncpg", "postgresql")
    engine = create_engine(sync_url)
    Session = sessionmaker(bind=engine)
    return Session()


@celery_app.task(bind=True, name="gunpladb.scrape_all_kits")
def scrape_all_kits(self, job_id: int, max_kits: Optional[int] = None):
    from app.models import ScrapeJob, ScrapeJobStatus, Kit, KitImage
    from app.scrapers.gunplacentral import discover_kit_ids, scrape_kits
    from app.storage import upload_bytes, get_public_url
    import httpx

    session = _get_sync_session()

    try:
        # Mark job as running
        job = session.get(ScrapeJob, job_id)
        job.status = ScrapeJobStatus.RUNNING
        job.started_at = datetime.now(timezone.utc)
        job.celery_task_id = self.request.id
        session.commit()

        # Discover IDs
        logger.info("Discovering kit IDs...")
        kit_ids = asyncio.run(discover_kit_ids(max_id=max_kits or 5000))
        job.items_found = len(kit_ids)
        session.commit()

        logger.info(f"Found {len(kit_ids)} kit IDs, scraping details...")

        def progress(done, total, kit):
            job.items_processed = done
            session.commit()

        kits = asyncio.run(scrape_kits(kit_ids, progress_callback=progress))

        # Save to DB
        saved = 0
        failed = 0
        for scraped in kits:
            try:
                existing = session.execute(
                    select(Kit).where(Kit.external_id == scraped.external_id)
                ).scalar_one_or_none()

                if existing:
                    # Update existing
                    existing.name = scraped.name
                    existing.franchise = scraped.franchise
                    existing.series = scraped.series
                    existing.grade = scraped.grade
                    existing.scale = scraped.scale
                    existing.release_date = scraped.release_date
                    existing.brand = scraped.brand
                    existing.description = scraped.description
                    existing.avg_rating = scraped.avg_rating
                    existing.total_owners = scraped.total_owners
                    existing.source_url = scraped.source_url
                    kit_db = existing
                else:
                    kit_db = Kit(
                        external_id=scraped.external_id,
                        name=scraped.name,
                        franchise=scraped.franchise,
                        series=scraped.series,
                        grade=scraped.grade,
                        scale=scraped.scale,
                        release_date=scraped.release_date,
                        brand=scraped.brand,
                        description=scraped.description,
                        avg_rating=scraped.avg_rating,
                        total_owners=scraped.total_owners,
                        source_url=scraped.source_url,
                        is_gundam=True,
                    )
                    session.add(kit_db)
                    session.flush()

                # Download and store images
                for idx, img_url in enumerate(scraped.image_urls[:5]):
                    try:
                        with httpx.Client(timeout=15, follow_redirects=True) as client:
                            resp = client.get(img_url)
                        if resp.status_code == 200:
                            ext = img_url.split(".")[-1].split("?")[0].lower() or "jpg"
                            path = f"images/kits/{kit_db.id}/{idx}.{ext}"
                            upload_bytes(resp.content, path, f"image/{ext}")
                            img_rec = KitImage(
                                kit_id=kit_db.id,
                                storage_path=path,
                                source_url=img_url,
                                image_type="main" if idx == 0 else "gallery",
                                sort_order=idx,
                            )
                            session.add(img_rec)
                    except Exception as e:
                        logger.warning(f"Image download failed for {img_url}: {e}")

                session.commit()
                saved += 1
            except Exception as e:
                logger.error(f"Failed to save kit {scraped.external_id}: {e}")
                session.rollback()
                failed += 1

        job.status = ScrapeJobStatus.COMPLETED
        job.items_processed = saved
        job.items_failed = failed
        job.completed_at = datetime.now(timezone.utc)
        session.commit()

    except Exception as e:
        logger.error(f"Scrape job {job_id} failed: {e}")
        job = session.get(ScrapeJob, job_id)
        if job:
            job.status = ScrapeJobStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.now(timezone.utc)
            session.commit()
        raise
    finally:
        session.close()


@celery_app.task(bind=True, name="gunpladb.scrape_new_kits")
def scrape_new_kits(self, job_id: int):
    """Only scrape kits that don't exist in the DB yet."""
    from app.models import ScrapeJob, ScrapeJobStatus, Kit, KitImage
    from app.scrapers.gunplacentral import get_latest_kit_id, scrape_kits
    from app.storage import upload_bytes
    import httpx

    session = _get_sync_session()

    try:
        job = session.get(ScrapeJob, job_id)
        job.status = ScrapeJobStatus.RUNNING
        job.started_at = datetime.now(timezone.utc)
        job.celery_task_id = self.request.id
        session.commit()

        # Find highest external_id we already have
        result = session.execute(
            select(Kit.external_id).order_by(Kit.external_id.desc()).limit(1)
        ).scalar_one_or_none()
        last_known = result or 0

        # Find latest on the site
        latest_id = asyncio.run(get_latest_kit_id())
        if not latest_id or latest_id <= last_known:
            job.status = ScrapeJobStatus.COMPLETED
            job.completed_at = datetime.now(timezone.utc)
            session.commit()
            return

        new_ids = list(range(last_known + 1, latest_id + 1))
        job.items_found = len(new_ids)
        session.commit()

        kits = asyncio.run(scrape_kits(new_ids))

        saved = 0
        failed = 0
        for scraped in kits:
            try:
                kit_db = Kit(
                    external_id=scraped.external_id,
                    name=scraped.name,
                    franchise=scraped.franchise,
                    series=scraped.series,
                    grade=scraped.grade,
                    scale=scraped.scale,
                    release_date=scraped.release_date,
                    brand=scraped.brand,
                    description=scraped.description,
                    avg_rating=scraped.avg_rating,
                    total_owners=scraped.total_owners,
                    source_url=scraped.source_url,
                    is_gundam=True,
                )
                session.add(kit_db)
                session.flush()

                for idx, img_url in enumerate(scraped.image_urls[:5]):
                    try:
                        with httpx.Client(timeout=15, follow_redirects=True) as client:
                            resp = client.get(img_url)
                        if resp.status_code == 200:
                            ext = img_url.split(".")[-1].split("?")[0].lower() or "jpg"
                            path = f"images/kits/{kit_db.id}/{idx}.{ext}"
                            upload_bytes(resp.content, path, f"image/{ext}")
                            session.add(KitImage(
                                kit_id=kit_db.id,
                                storage_path=path,
                                source_url=img_url,
                                image_type="main" if idx == 0 else "gallery",
                                sort_order=idx,
                            ))
                    except Exception as e:
                        logger.warning(f"Image failed: {e}")

                session.commit()
                saved += 1
            except Exception as e:
                logger.error(f"Failed saving kit {scraped.external_id}: {e}")
                session.rollback()
                failed += 1

        job.status = ScrapeJobStatus.COMPLETED
        job.items_processed = saved
        job.items_failed = failed
        job.completed_at = datetime.now(timezone.utc)
        session.commit()

    except Exception as e:
        logger.error(f"New-kits job {job_id} failed: {e}")
        job = session.get(ScrapeJob, job_id)
        if job:
            job.status = ScrapeJobStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.now(timezone.utc)
            session.commit()
        raise
    finally:
        session.close()


@celery_app.task(bind=True, name="gunpladb.scrape_manual")
def scrape_manual_task(self, job_id: int, kit_id: int, bandai_manual_id: int):
    from app.models import ScrapeJob, ScrapeJobStatus, Manual
    from app.scrapers.bandai_manual import scrape_manual
    from app.storage import upload_bytes

    session = _get_sync_session()
    try:
        job = session.get(ScrapeJob, job_id)
        job.status = ScrapeJobStatus.RUNNING
        job.started_at = datetime.now(timezone.utc)
        job.celery_task_id = self.request.id
        session.commit()

        manual_data = asyncio.run(scrape_manual(bandai_manual_id))

        if not manual_data or not manual_data.pdf_bytes:
            raise ValueError(f"No manual content found for Bandai ID {bandai_manual_id}")

        path = f"manuals/{kit_id}/manual.pdf"
        upload_bytes(manual_data.pdf_bytes, path, "application/pdf")

        existing = session.execute(
            select(Manual).where(Manual.kit_id == kit_id)
        ).scalar_one_or_none()

        if existing:
            existing.bandai_manual_id = bandai_manual_id
            existing.storage_path = path
            existing.source_url = manual_data.source_url
            existing.page_count = manual_data.page_count
        else:
            session.add(Manual(
                kit_id=kit_id,
                bandai_manual_id=bandai_manual_id,
                storage_path=path,
                source_url=manual_data.source_url,
                page_count=manual_data.page_count,
            ))

        session.commit()

        job.status = ScrapeJobStatus.COMPLETED
        job.items_processed = 1
        job.completed_at = datetime.now(timezone.utc)
        session.commit()

    except Exception as e:
        logger.error(f"Manual job {job_id} failed: {e}")
        job = session.get(ScrapeJob, job_id)
        if job:
            job.status = ScrapeJobStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.now(timezone.utc)
            session.commit()
        raise
    finally:
        session.close()
