from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Kit, Manual
from app.schemas import ManualOut
from app.storage import upload_bytes, get_public_url, delete_object, object_exists

router = APIRouter(prefix="/kits/{kit_id}/manual", tags=["manuals"])


@router.get("", response_model=ManualOut)
async def get_manual(kit_id: int, db: AsyncSession = Depends(get_db)):
    manual = (await db.execute(
        select(Manual).where(Manual.kit_id == kit_id)
    )).scalar_one_or_none()
    if not manual:
        raise HTTPException(404, "No manual for this kit")
    return ManualOut(
        id=manual.id,
        bandai_manual_id=manual.bandai_manual_id,
        storage_path=manual.storage_path,
        source_url=manual.source_url,
        page_count=manual.page_count,
        manually_uploaded=manual.manually_uploaded,
        url=get_public_url(manual.storage_path) if manual.storage_path else None,
    )


@router.post("", response_model=ManualOut, status_code=201)
async def upload_manual(
    kit_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    kit = (await db.execute(select(Kit).where(Kit.id == kit_id))).scalar_one_or_none()
    if not kit:
        raise HTTPException(404, "Kit not found")

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are accepted")

    data = await file.read()
    path = f"manuals/{kit_id}/manual.pdf"
    upload_bytes(data, path, "application/pdf")

    existing = (await db.execute(
        select(Manual).where(Manual.kit_id == kit_id)
    )).scalar_one_or_none()

    if existing:
        existing.storage_path = path
        existing.manually_uploaded = True
        manual = existing
    else:
        manual = Manual(
            kit_id=kit_id,
            storage_path=path,
            manually_uploaded=True,
        )
        db.add(manual)

    await db.commit()
    await db.refresh(manual)

    return ManualOut(
        id=manual.id,
        bandai_manual_id=manual.bandai_manual_id,
        storage_path=manual.storage_path,
        source_url=manual.source_url,
        page_count=manual.page_count,
        manually_uploaded=manual.manually_uploaded,
        url=get_public_url(manual.storage_path),
    )


@router.delete("", status_code=204)
async def delete_manual(kit_id: int, db: AsyncSession = Depends(get_db)):
    manual = (await db.execute(
        select(Manual).where(Manual.kit_id == kit_id)
    )).scalar_one_or_none()
    if not manual:
        raise HTTPException(404, "No manual for this kit")
    if manual.storage_path:
        delete_object(manual.storage_path)
    await db.delete(manual)
    await db.commit()
