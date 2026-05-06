from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class KitImageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    storage_path: str
    source_url: Optional[str] = None
    image_type: str
    sort_order: int
    url: Optional[str] = None


class ManualOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    bandai_manual_id: Optional[int] = None
    storage_path: Optional[str] = None
    source_url: Optional[str] = None
    page_count: Optional[int] = None
    manually_uploaded: bool
    url: Optional[str] = None


class KitBase(BaseModel):
    name: str
    franchise: Optional[str] = None
    series: Optional[str] = None
    grade: Optional[str] = None
    scale: Optional[str] = None
    release_date: Optional[str] = None
    brand: Optional[str] = None
    description: Optional[str] = None
    avg_rating: Optional[float] = None
    total_owners: Optional[int] = None
    source_url: Optional[str] = None


class KitCreate(KitBase):
    pass


class KitUpdate(BaseModel):
    name: Optional[str] = None
    franchise: Optional[str] = None
    series: Optional[str] = None
    grade: Optional[str] = None
    scale: Optional[str] = None
    release_date: Optional[str] = None
    brand: Optional[str] = None
    description: Optional[str] = None
    avg_rating: Optional[float] = None
    total_owners: Optional[int] = None
    bandai_manual_id: Optional[int] = None


class KitOut(KitBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    external_id: Optional[int] = None
    is_gundam: bool
    manually_added: bool
    created_at: datetime
    updated_at: datetime
    images: list[KitImageOut] = []
    manual: Optional[ManualOut] = None


class KitListOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    external_id: Optional[int] = None
    name: str
    franchise: Optional[str] = None
    series: Optional[str] = None
    grade: Optional[str] = None
    scale: Optional[str] = None
    release_date: Optional[str] = None
    avg_rating: Optional[float] = None
    thumbnail_url: Optional[str] = None
    has_manual: bool = False


class KitListResponse(BaseModel):
    items: list[KitListOut]
    total: int
    page: int
    page_size: int
    pages: int


class ScrapeJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_type: str
    status: str
    celery_task_id: Optional[str] = None
    items_found: int
    items_processed: int
    items_failed: int
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime


class ScrapeJobCreate(BaseModel):
    job_type: str
    max_kits: Optional[int] = None
    bandai_manual_id_start: Optional[int] = None
    bandai_manual_id_end: Optional[int] = None
