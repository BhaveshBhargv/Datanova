"""Database access helpers for AutoML experiments."""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.experiment import Experiment


def create(db: Session, **fields) -> Experiment:
    experiment = Experiment(**fields)
    db.add(experiment)
    db.commit()
    db.refresh(experiment)
    return experiment


def list_for_dataset(db: Session, dataset_id: uuid.UUID) -> list[Experiment]:
    return list(
        db.scalars(
            select(Experiment)
            .where(Experiment.dataset_id == dataset_id)
            .order_by(Experiment.created_at.desc())
        )
    )


def get(db: Session, experiment_id: uuid.UUID) -> Experiment | None:
    return db.get(Experiment, experiment_id)


def save(db: Session, experiment: Experiment) -> Experiment:
    db.commit()
    db.refresh(experiment)
    return experiment


def delete(db: Session, experiment: Experiment) -> None:
    db.delete(experiment)
    db.commit()
