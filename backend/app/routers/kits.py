import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Kit, KitImage, Manual
from app.schemas import KitCreate, KitUpdate, KitOut, KitListOut, KitListResponse
from app.storage import upload_bytes, get_public_url, delete_object

router = APIRouter(prefix="/kits", tags=["kits"])


def _image_url(path: str) -> str:
    return get_public_url(path)


def _kit_list_item(kit: Kit) -> KitListOut:
    thumb = None
    if kit.images:
        main = next((i for i in kit.images if i.image_type == "main"), kit.images[0])
        thumb = _image_url(main.storage_path)
    return KitListOut(
        id=kit.id,
        external_id=kit.external_id,
        name=kit.name,
        franchise=kit.franchise,
        series=kit.series,
        grade=kit.grade,
        scale=kit.scale,
        release_date=kit.release_date,
        avg_rating=kit.avg_rating,
        thumbnail_url=thumb,
        has_manual=kit.manual is not None,
    )


def _kit_detail(kit: Kit) -> KitOut:
    from app.schemas import KitImageOut, ManualOut

    images = [
        KitImageOut(
            id=i.id,
            storage_path=i.storage_path,
            source_url=i.source_url,
            image_type=i.image_type,
            sort_order=i.sort_order,
            url=_image_url(i.storage_path),
        )
        for i in sorted(kit.images, key=lambda x: x.sort_order)
    ]

    manual = None
    if kit.manual:
        m = kit.manual
        manual = ManualOut(
            id=m.id,
            bandai_manual_id=m.bandai_manual_id,
            storage_path=m.storage_path,
            source_url=m.source_url,
            page_count=m.page_count,
            manually_uploaded=m.manually_uploaded,
            url=_image_url(m.storage_path) if m.storage_path else None,
        )

    return KitOut(
        id=kit.id,
        external_id=kit.external_id,
        name=kit.name,
        franchise=kit.franchise,
        series=kit.series,
        grade=kit.grade,
        scale=kit.scale,
        release_date=kit.release_date,
        brand=kit.brand,
        description=kit.description,
        avg_rating=kit.avg_rating,
        total_owners=kit.total_owners,
        source_url=kit.source_url,
        is_gundam=kit.is_gundam,
        manually_added=kit.manually_added,
        created_at=kit.created_at,
        updated_at=kit.updated_at,
        images=images,
        manual=manual,
    )


@router.get("", response_model=KitListResponse)
async def list_kits(
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
    search: Optional[str] = Query(None),
    franchise: Optional[str] = Query(None),
    series: Optional[str] = Query(None),
    grade: Optional[str] = Query(None),
    has_manual: Optional[bool] = Query(None),
    sort: str = Query("name"),
    db: AsyncSession = Depends(get_db),
):
    q = select(Kit).options(selectinload(Kit.images), selectinload(Kit.manual))

    if search:
        q = q.where(or_(
            Kit.name.ilike(f"%{search}%"),
            Kit.series.ilike(f"%{search}%"),
            Kit.franchise.ilike(f"%{search}%"),
        ))
    if franchise:
        q = q.where(Kit.franchise.ilike(f"%{franchise}%"))
    if series:
        q = q.where(Kit.series.ilike(f"%{series}%"))
    if grade:
        q = q.where(Kit.grade == grade)
    if has_manual is True:
        q = q.where(Kit.manual != None)
    if has_manual is False:
        q = q.where(Kit.manual == None)

    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar_one()

    sort_map = {
        "name": Kit.name,
        "release_date": Kit.release_date,
        "rating": Kit.avg_rating.desc(),
        "newest": Kit.created_at.desc(),
    }
    q = q.order_by(sort_map.get(sort, Kit.name))
    q = q.offset((page - 1) * page_size).limit(page_size)

    kits = (await db.execute(q)).scalars().all()
    return KitListResponse(
        items=[_kit_list_item(k) for k in kits],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size),
    )


@router.get("/filters", tags=["kits"])
async def get_filter_options(db: AsyncSession = Depends(get_db)):
    """Return distinct values for filter dropdowns."""
    franchises = (await db.execute(
        select(Kit.franchise).distinct().where(Kit.franchise != None).order_by(Kit.franchise)
    )).scalars().all()
    series = (await db.execute(
        select(Kit.series).distinct().where(Kit.series != None).order_by(Kit.series)
    )).scalars().all()
    grades = (await db.execute(
        select(Kit.grade).distinct().where(Kit.grade != None).order_by(Kit.grade)
    )).scalars().all()
    return {"franchises": franchises, "series": series, "grades": grades}


@router.get("/{kit_id}", response_model=KitOut)
async def get_kit(kit_id: int, db: AsyncSession = Depends(get_db)):
    q = select(Kit).where(Kit.id == kit_id).options(
        selectinload(Kit.images), selectinload(Kit.manual)
    )
    kit = (await db.execute(q)).scalar_one_or_none()
    if not kit:
        raise HTTPException(404, "Kit not found")
    return _kit_detail(kit)


@router.post("", response_model=KitOut, status_code=201)
async def create_kit(body: KitCreate, db: AsyncSession = Depends(get_db)):
    kit = Kit(**body.model_dump(), manually_added=True)
    db.add(kit)
    await db.commit()
    await db.refresh(kit)
    return _kit_detail(kit)


@router.patch("/{kit_id}", response_model=KitOut)
async def update_kit(kit_id: int, body: KitUpdate, db: AsyncSession = Depends(get_db)):
    q = select(Kit).where(Kit.id == kit_id).options(
        selectinload(Kit.images), selectinload(Kit.manual)
    )
    kit = (await db.execute(q)).scalar_one_or_none()
    if not kit:
        raise HTTPException(404, "Kit not found")

    for field, value in body.model_dump(exclude_none=True).items():
        if field != "bandai_manual_id":
            setattr(kit, field, value)

    await db.commit()
    await db.refresh(kit)
    return _kit_detail(kit)


@router.delete("/{kit_id}", status_code=204)
async def delete_kit(kit_id: int, db: AsyncSession = Depends(get_db)):
    kit = (await db.execute(select(Kit).where(Kit.id == kit_id))).scalar_one_or_none()
    if not kit:
        raise HTTPException(404, "Kit not found")
    await db.delete(kit)
    await db.commit()


@router.post("/{kit_id}/images", response_model=KitOut)
async def upload_kit_image(
    kit_id: int,
    file: UploadFile = File(...),
    image_type: str = "main",
    db: AsyncSession = Depends(get_db),
):
    q = select(Kit).where(Kit.id == kit_id).options(
        selectinload(Kit.images), selectinload(Kit.manual)
    )
    kit = (await db.execute(q)).scalar_one_or_none()
    if not kit:
        raise HTTPException(404, "Kit not found")

    data = await file.read()
    ext = (file.filename or "image.jpg").rsplit(".", 1)[-1].lower()
    sort_order = len(kit.images)
    path = f"images/kits/{kit_id}/{sort_order}.{ext}"
    upload_bytes(data, path, file.content_type or f"image/{ext}")

    img = KitImage(kit_id=kit_id, storage_path=path, image_type=image_type, sort_order=sort_order)
    db.add(img)
    await db.commit()

    result = (await db.execute(q)).scalar_one()
    return _kit_detail(result)


@router.delete("/{kit_id}/images/{image_id}", status_code=204)
async def delete_kit_image(kit_id: int, image_id: int, db: AsyncSession = Depends(get_db)):
    img = (await db.execute(
        select(KitImage).where(KitImage.id == image_id, KitImage.kit_id == kit_id)
    )).scalar_one_or_none()
    if not img:
        raise HTTPException(404, "Image not found")
    delete_object(img.storage_path)
    await db.delete(img)
    await db.commit()
