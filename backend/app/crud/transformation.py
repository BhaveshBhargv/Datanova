"""Database access helpers for cleaning transformations."""
import uuid

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.transformation import Transformation


def list_for_dataset(db: Session, dataset_id: uuid.UUID) -> list[Transformation]:
    return list(
        db.scalars(
            select(Transformation)
            .where(Transformation.dataset_id == dataset_id)
            .order_by(Transformation.order_index)
        )
    )


def add(
    db: Session,
    dataset_id: uuid.UUID,
    order_index: int,
    operation: str,
    params: dict,
) -> Transformation:
    step = Transformation(
        dataset_id=dataset_id,
        order_index=order_index,
        operation=operation,
        params=params,
    )
    db.add(step)
    db.commit()
    db.refresh(step)
    return step


def delete_last(db: Session, steps: list[Transformation]) -> None:
    if steps:
        db.delete(steps[-1])
        db.commit()


def clear(db: Session, dataset_id: uuid.UUID) -> None:
    db.execute(
        delete(Transformation).where(Transformation.dataset_id == dataset_id)
    )
    db.commit()
