"""Dataset ORM model."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.database import Base
from app.core.types import GUID

# JSONB on PostgreSQL, plain JSON elsewhere (e.g. SQLite in tests).
JSONVariant = JSON().with_variant(JSONB(), "postgresql")

# String values for source_type / status (validated at the app layer; kept as
# plain strings so migrations stay portable across PostgreSQL and SQLite).
SOURCE_UPLOAD = "upload"
SOURCE_DATABASE = "database"

STATUS_READY = "ready"
STATUS_FAILED = "failed"


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid.uuid4
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    file_format: Mapped[str | None] = mapped_column(String(20), nullable=True)

    original_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    parquet_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # Parquet of the current cleaned data; null means the original is current.
    cleaned_path: Mapped[str | None] = mapped_column(String(512), nullable=True)

    n_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    n_columns: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # [{ "name": str, "dtype": str, "nullable": bool }]
    columns: Mapped[list] = mapped_column(JSONVariant, default=list, nullable=False)

    status: Mapped[str] = mapped_column(
        String(20), default=STATUS_READY, nullable=False
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
