from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import ScrapeJob, ScrapeJobStatus
from app.schemas import ScrapeJobOut, ScrapeJobCreate

router = APIRouter(prefix="/scrape", tags=["scrape"])


@router.post("/start", response_model=ScrapeJobOut, status_code=202)
async def start_full_scrape(
    body: ScrapeJobCreate,
    db: AsyncSession = Depends(get_db),
):
    """Trigger a full scrape of gunplacentral.com."""
    from app.tasks import scrape_all_kits

    job = ScrapeJob(job_type="full_scrape")
    db.add(job)
    await db.commit()
    await db.refresh(job)

    task = scrape_all_kits.delay(job.id, body.max_kits)
    job.celery_task_id = task.id
    await db.commit()
    await db.refresh(job)

    return ScrapeJobOut.model_validate(job)


@router.post("/update", response_model=ScrapeJobOut, status_code=202)
async def start_update_scrape(db: AsyncSession = Depends(get_db)):
    """Scrape only kits added since the last scrape."""
    from app.tasks import scrape_new_kits

    job = ScrapeJob(job_type="update_scrape")
    db.add(job)
    await db.commit()
    await db.refresh(job)

    task = scrape_new_kits.delay(job.id)
    job.celery_task_id = task.id
    await db.commit()
    await db.refresh(job)

    return ScrapeJobOut.model_validate(job)


@router.post("/manual/{kit_id}", response_model=ScrapeJobOut, status_code=202)
async def fetch_manual_from_bandai(
    kit_id: int,
    bandai_manual_id: int = Query(..., description="Bandai manual ID from manual.bandai-hobby.net/menus/detail/{id}"),
    db: AsyncSession = Depends(get_db),
):
    """Fetch and store a Bandai instruction manual for a kit."""
    from app.tasks import scrape_manual_task
    from app.models import Kit

    kit = (await db.execute(select(Kit).where(Kit.id == kit_id))).scalar_one_or_none()
    if not kit:
        raise HTTPException(404, "Kit not found")

    job = ScrapeJob(job_type="fetch_manual")
    db.add(job)
    await db.commit()
    await db.refresh(job)

    task = scrape_manual_task.delay(job.id, kit_id, bandai_manual_id)
    job.celery_task_id = task.id
    await db.commit()
    await db.refresh(job)

    return ScrapeJobOut.model_validate(job)


@router.get("/jobs", response_model=list[ScrapeJobOut])
async def list_jobs(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    jobs = (await db.execute(
        select(ScrapeJob).order_by(ScrapeJob.created_at.desc()).limit(limit)
    )).scalars().all()
    return [ScrapeJobOut.model_validate(j) for j in jobs]


@router.get("/jobs/{job_id}", response_model=ScrapeJobOut)
async def get_job(job_id: int, db: AsyncSession = Depends(get_db)):
    job = (await db.execute(select(ScrapeJob).where(ScrapeJob.id == job_id))).scalar_one_or_none()
    if not job:
        raise HTTPException(404, "Job not found")
    return ScrapeJobOut.model_validate(job)
