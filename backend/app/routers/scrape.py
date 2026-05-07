from datetime import datetime, timezone
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


@router.post("/jobs/{job_id}/cancel", response_model=ScrapeJobOut)
async def cancel_job(job_id: int, db: AsyncSession = Depends(get_db)):
    job = (await db.execute(select(ScrapeJob).where(ScrapeJob.id == job_id))).scalar_one_or_none()
    if not job:
        raise HTTPException(404, "Job not found")
    if job.status not in (ScrapeJobStatus.PENDING, ScrapeJobStatus.RUNNING, ScrapeJobStatus.PAUSED):
        raise HTTPException(400, f"Cannot cancel a job with status '{job.status}'")

    if job.celery_task_id:
        from app.tasks import celery_app
        celery_app.control.revoke(job.celery_task_id, terminate=True, signal="SIGTERM")

    job.status = ScrapeJobStatus.CANCELLED
    job.completed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(job)
    return ScrapeJobOut.model_validate(job)


@router.post("/jobs/{job_id}/pause", response_model=ScrapeJobOut)
async def pause_job(job_id: int, db: AsyncSession = Depends(get_db)):
    job = (await db.execute(select(ScrapeJob).where(ScrapeJob.id == job_id))).scalar_one_or_none()
    if not job:
        raise HTTPException(404, "Job not found")
    if job.status != ScrapeJobStatus.RUNNING:
        raise HTTPException(400, f"Can only pause a running job (current status: '{job.status}')")

    job.status = ScrapeJobStatus.PAUSED
    await db.commit()
    await db.refresh(job)
    return ScrapeJobOut.model_validate(job)


@router.post("/jobs/{job_id}/resume", response_model=ScrapeJobOut)
async def resume_job(job_id: int, db: AsyncSession = Depends(get_db)):
    job = (await db.execute(select(ScrapeJob).where(ScrapeJob.id == job_id))).scalar_one_or_none()
    if not job:
        raise HTTPException(404, "Job not found")

    if job.status == ScrapeJobStatus.PAUSED:
        job.status = ScrapeJobStatus.RUNNING
        await db.commit()
        await db.refresh(job)
        return ScrapeJobOut.model_validate(job)

    if job.status in (ScrapeJobStatus.FAILED, ScrapeJobStatus.CANCELLED):
        if job.job_type == "fetch_manual":
            raise HTTPException(400, "Cannot retry a fetch_manual job — parameters are not stored")

        from app.tasks import scrape_all_kits, scrape_new_kits

        job.status = ScrapeJobStatus.PENDING
        job.items_found = 0
        job.items_processed = 0
        job.items_failed = 0
        job.error_message = None
        job.started_at = None
        job.completed_at = None
        await db.commit()
        await db.refresh(job)

        if job.job_type == "full_scrape":
            task = scrape_all_kits.delay(job.id)
        else:
            task = scrape_new_kits.delay(job.id)

        job.celery_task_id = task.id
        await db.commit()
        await db.refresh(job)
        return ScrapeJobOut.model_validate(job)

    raise HTTPException(400, f"Cannot resume a job with status '{job.status}'")


@router.delete("/jobs/{job_id}", status_code=204)
async def delete_job(job_id: int, db: AsyncSession = Depends(get_db)):
    job = (await db.execute(select(ScrapeJob).where(ScrapeJob.id == job_id))).scalar_one_or_none()
    if not job:
        raise HTTPException(404, "Job not found")
    if job.status in (ScrapeJobStatus.PENDING, ScrapeJobStatus.RUNNING, ScrapeJobStatus.PAUSED):
        raise HTTPException(400, "Cannot delete an active job — cancel it first")

    await db.delete(job)
    await db.commit()
