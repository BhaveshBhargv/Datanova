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
from app.schemas.eda import ExplainResponse
from app.schemas.experiment import ExperimentCreate, ExperimentRead
from app.schemas.explain_ml import (
    ImportanceResponse,
    PredictionExplainRequest,
    PredictionExplainResponse,
)
from app.services import automl, cleaning, explain_ml, narrate

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


# --- Explainability / SHAP (Phase 7) --------------------------------------


def _completed_or_409(db: Session, user: User, experiment_id: uuid.UUID) -> Experiment:
    exp = _experiment_or_404(db, user, experiment_id)
    if exp.status != STATUS_COMPLETED or not exp.model_path:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This experiment has no completed model to explain.",
        )
    return exp


def _dataset_for(db: Session, user: User, exp: Experiment) -> Dataset:
    return dataset_crud.get_owned(db, user.id, exp.dataset_id)


@router.get("/experiments/{experiment_id}/importance", response_model=ImportanceResponse)
async def feature_importance(
    experiment_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    exp = _completed_or_409(db, user, experiment_id)
    df = cleaning.load_current(_dataset_for(db, user, exp))
    try:
        return await run_in_threadpool(explain_ml.global_importance, exp, df)
    except explain_ml.ExplainError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/experiments/{experiment_id}/predictions/explain",
    response_model=PredictionExplainResponse,
)
async def explain_prediction(
    experiment_id: uuid.UUID,
    req: PredictionExplainRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    exp = _completed_or_409(db, user, experiment_id)
    df = cleaning.load_current(_dataset_for(db, user, exp))
    try:
        return await run_in_threadpool(
            explain_ml.explain_prediction, exp, df, req.index
        )
    except explain_ml.ExplainError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/experiments/{experiment_id}/narrative", response_model=ExplainResponse)
async def explain_drivers(
    experiment_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ExplainResponse:
    exp = _completed_or_409(db, user, experiment_id)
    df = cleaning.load_current(_dataset_for(db, user, exp))
    importance = await run_in_threadpool(explain_ml.global_importance, exp, df)
    text, source = narrate.explain_drivers(
        importance["importance"], exp.problem_type, exp.target_column
    )
    return ExplainResponse(text=text, source=source)
