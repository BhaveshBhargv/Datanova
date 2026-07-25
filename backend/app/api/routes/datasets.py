"""Dataset routes: upload, list, detail, preview, rename, delete."""
import uuid
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.storage import storage
from app.crud import dataset as dataset_crud
from app.models.dataset import SOURCE_UPLOAD, STATUS_READY, Dataset
from app.models.user import User
from app.schemas.dataset import DatasetPreview, DatasetRead, DatasetUpdate
from app.services import ingest

router = APIRouter(prefix="/datasets", tags=["datasets"])


def _get_or_404(db: Session, user: User, dataset_id: uuid.UUID) -> Dataset:
    dataset = dataset_crud.get_owned(db, user.id, dataset_id)
    if dataset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found."
        )
    return dataset


@router.post("/upload", response_model=DatasetRead, status_code=status.HTTP_201_CREATED)
async def upload_dataset(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Dataset:
    raw = await file.read()
    try:
        df, fmt = ingest.parse_upload(file.filename or "upload", raw)
    except ingest.IngestError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    dataset_id = uuid.uuid4()
    parquet_rel = ingest.parquet_rel_path(user.id, dataset_id)
    original_rel = ingest.original_rel_path(user.id, dataset_id, fmt)
    ingest.write_parquet(parquet_rel, df)
    storage.write(original_rel, raw)

    return dataset_crud.create(
        db,
        id=dataset_id,
        owner_id=user.id,
        name=Path(file.filename or "dataset").stem or "dataset",
        source_type=SOURCE_UPLOAD,
        file_format=fmt,
        original_path=original_rel,
        parquet_path=parquet_rel,
        n_rows=int(df.shape[0]),
        n_columns=int(df.shape[1]),
        size_bytes=len(raw),
        columns=ingest.column_schema(df),
        status=STATUS_READY,
    )


@router.get("", response_model=list[DatasetRead])
def list_datasets(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Dataset]:
    return dataset_crud.list_for_owner(db, user.id)


@router.get("/{dataset_id}", response_model=DatasetRead)
def get_dataset(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Dataset:
    return _get_or_404(db, user, dataset_id)


@router.get("/{dataset_id}/preview", response_model=DatasetPreview)
def preview_dataset(
    dataset_id: uuid.UUID,
    rows: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DatasetPreview:
    dataset = _get_or_404(db, user, dataset_id)
    if not dataset.parquet_path:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Dataset has no stored data to preview.",
        )
    columns, records = ingest.preview(dataset.parquet_path, rows)
    return DatasetPreview(columns=columns, rows=records)


@router.patch("/{dataset_id}", response_model=DatasetRead)
def rename_dataset(
    dataset_id: uuid.UUID,
    data: DatasetUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Dataset:
    dataset = _get_or_404(db, user, dataset_id)
    return dataset_crud.rename(db, dataset, data.name)


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dataset(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    dataset = _get_or_404(db, user, dataset_id)
    for rel in (dataset.parquet_path, dataset.original_path):
        if rel:
            storage.delete(rel)
    dataset_crud.delete(db, dataset)
