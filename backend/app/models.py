from datetime import datetime
from typing import Optional
import enum

from sqlalchemy import (
    String, Integer, Float, DateTime, Text, Boolean, Enum,
    ForeignKey, UniqueConstraint, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class GradeEnum(str, enum.Enum):
    HG = "HG"
    RG = "RG"
    MG = "MG"
    MG_VER_KA = "MG Ver.Ka"
    PG = "PG"
    SD = "SD"
    BB = "BB"
    FG = "FG"
    EG = "EG"
    RE100 = "RE/100"
    HGUC = "HGUC"
    HGCE = "HGCE"
    HGIBO = "HGIBO"
    HGAC = "HGAC"
    HGFC = "HGFC"
    HGAW = "HGAW"
    HGCC = "HGCC"
    HGBF = "HGBF"
    HGBFR = "HGBFR"
    HGBD = "HGBD"
    HGWFM = "HGWFM"
    OTHER = "OTHER"


class ScrapeJobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Kit(Base):
    __tablename__ = "kits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[Optional[int]] = mapped_column(Integer, unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    franchise: Mapped[Optional[str]] = mapped_column(String(200))
    series: Mapped[Optional[str]] = mapped_column(String(200))
    grade: Mapped[Optional[str]] = mapped_column(String(50))
    scale: Mapped[Optional[str]] = mapped_column(String(50))
    release_date: Mapped[Optional[str]] = mapped_column(String(100))
    brand: Mapped[Optional[str]] = mapped_column(String(100))
    description: Mapped[Optional[str]] = mapped_column(Text)
    avg_rating: Mapped[Optional[float]] = mapped_column(Float)
    total_owners: Mapped[Optional[int]] = mapped_column(Integer)
    source_url: Mapped[Optional[str]] = mapped_column(String(500))
    is_gundam: Mapped[bool] = mapped_column(Boolean, default=True)
    manually_added: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    images: Mapped[list["KitImage"]] = relationship("KitImage", back_populates="kit", cascade="all, delete-orphan")
    manual: Mapped[Optional["Manual"]] = relationship("Manual", back_populates="kit", uselist=False, cascade="all, delete-orphan")


class KitImage(Base):
    __tablename__ = "kit_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kit_id: Mapped[int] = mapped_column(Integer, ForeignKey("kits.id", ondelete="CASCADE"))
    storage_path: Mapped[str] = mapped_column(String(500))
    source_url: Mapped[Optional[str]] = mapped_column(String(500))
    image_type: Mapped[str] = mapped_column(String(50), default="main")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    kit: Mapped["Kit"] = relationship("Kit", back_populates="images")


class Manual(Base):
    __tablename__ = "manuals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kit_id: Mapped[int] = mapped_column(Integer, ForeignKey("kits.id", ondelete="CASCADE"), unique=True)
    bandai_manual_id: Mapped[Optional[int]] = mapped_column(Integer)
    storage_path: Mapped[Optional[str]] = mapped_column(String(500))
    source_url: Mapped[Optional[str]] = mapped_column(String(500))
    page_count: Mapped[Optional[int]] = mapped_column(Integer)
    manually_uploaded: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    kit: Mapped["Kit"] = relationship("Kit", back_populates="manual")


class ScrapeJob(Base):
    __tablename__ = "scrape_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_type: Mapped[str] = mapped_column(String(50))
    status: Mapped[ScrapeJobStatus] = mapped_column(Enum(ScrapeJobStatus), default=ScrapeJobStatus.PENDING)
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(200))
    items_found: Mapped[int] = mapped_column(Integer, default=0)
    items_processed: Mapped[int] = mapped_column(Integer, default=0)
    items_failed: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
