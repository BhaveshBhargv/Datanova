"""Database access helpers for datasets."""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.dataset import Dataset


def create(db: Session, **fields) -> Dataset:
    dataset = Dataset(**fields)
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return dataset


def list_for_owner(db: Session, owner_id: uuid.UUID) -> list[Dataset]:
    return list(
        db.scalars(
            select(Dataset)
            .where(Dataset.owner_id == owner_id)
            .order_by(Dataset.created_at.desc())
        )
    )


def get_owned(
    db: Session, owner_id: uuid.UUID, dataset_id: uuid.UUID
) -> Dataset | None:
    return db.scalar(
        select(Dataset).where(
            Dataset.id == dataset_id, Dataset.owner_id == owner_id
        )
    )


def rename(db: Session, dataset: Dataset, name: str) -> Dataset:
    dataset.name = name
    db.commit()
    db.refresh(dataset)
    return dataset


def delete(db: Session, dataset: Dataset) -> None:
    db.delete(dataset)
    db.commit()
