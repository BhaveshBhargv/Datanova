"""AutoML experiment routes."""
import io
import uuid
from datetime import datetime, timezone

import joblib
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.storage import storage
from app.crud import dataset as dataset_crud
from app.crud import experiment as experiment_crud
from app.models.dataset import Dataset
from app.models.experiment import (
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_RUNNING,
    Experiment,
)
from app.models.user import User
from app.schemas.experiment import ExperimentCreate, ExperimentRead
from app.services import automl, cleaning

router = APIRouter(tags=["automl"])


def _dataset_or_404(db: Session, user: User, dataset_id: uuid.UUID) -> Dataset:
    dataset = dataset_crud.get_owned(db, user.id, dataset_id)
    if dataset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found."
        )
    return dataset


def _experiment_or_404(
    db: Session, user: User, experiment_id: uuid.UUID
) -> Experiment:
    exp = experiment_crud.get(db, experiment_id)
    if exp is None or dataset_crud.get_owned(db, user.id, exp.dataset_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found."
        )
    return exp


@router.post(
    "/datasets/{dataset_id}/experiments",
    response_model=ExperimentRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_experiment(
    dataset_id: uuid.UUID,
    data: ExperimentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Experiment:
    dataset = _dataset_or_404(db, user, dataset_id)
    df = cleaning.load_current(dataset)

    if data.target not in df.columns:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Target column '{data.target}' is not in the dataset.",
        )
    features = data.features or [c for c in df.columns if c != data.target]
    features = [c for c in features if c != data.target]
    unknown = [c for c in features if c not in df.columns]
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown feature column(s): {', '.join(unknown)}",
        )
    if not features:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one feature column is required.",
        )

    try:
        problem_type = automl.detect_problem_type(df[data.target])
    except automl.AutoMLError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    experiment = experiment_crud.create(
        db,
        dataset_id=dataset.id,
        target_column=data.target,
        feature_columns=features,
        problem_type=problem_type,
        status=STATUS_RUNNING,
        test_size=data.test_size,
    )

    try:
        result = await run_in_threadpool(
            automl.train, df, data.target, features, problem_type, data.test_size
        )
    except automl.AutoMLError as exc:
        experiment.status = STATUS_FAILED
        experiment.error = str(exc)
        return experiment_crud.save(db, experiment)
    except Exception as exc:  # noqa: BLE001 - surface unexpected training failures
        experiment.status = STATUS_FAILED
        experiment.error = f"Training failed: {exc}"
        return experiment_crud.save(db, experiment)

    # Persist the best pipeline as a joblib artifact.
    buffer = io.BytesIO()
    joblib.dump(result["pipeline"], buffer)
    model_rel = f"{dataset.owner_id}/{experiment.id}.model.joblib"
    storage.write(model_rel, buffer.getvalue())

    experiment.results = result["results"]
    experiment.best_model_name = result["best_model_name"]
    experiment.feature_columns = result["used_features"]
    experiment.model_path = model_rel
    experiment.status = STATUS_COMPLETED
    experiment.completed_at = datetime.now(timezone.utc)
    return experiment_crud.save(db, experiment)


@router.get(
    "/datasets/{dataset_id}/experiments", response_model=list[ExperimentRead]
)
def list_experiments(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    dataset = _dataset_or_404(db, user, dataset_id)
    return experiment_crud.list_for_dataset(db, dataset.id)


@router.get("/experiments/{experiment_id}", response_model=ExperimentRead)
def get_experiment(
    experiment_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Experiment:
    return _experiment_or_404(db, user, experiment_id)


@router.delete(
    "/experiments/{experiment_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_experiment(
    experiment_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    exp = _experiment_or_404(db, user, experiment_id)
    if exp.model_path:
        storage.delete(exp.model_path)
    experiment_crud.delete(db, exp)
