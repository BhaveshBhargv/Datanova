"""Analytics workspace: cross-resource summary for the user's home."""
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.connection_query import ConnectionQuery
from app.models.conversation import Conversation
from app.models.dataset import Dataset
from app.models.db_connection import DBConnection
from app.models.experiment import STATUS_COMPLETED, Experiment
from app.models.user import User
from app.schemas.workspace import (
    RecentDataset,
    RecentModel,
    RecentQuery,
    WorkspaceCounts,
    WorkspaceSummary,
)

router = APIRouter(prefix="/workspace", tags=["workspace"])


@router.get("/summary", response_model=WorkspaceSummary)
def workspace_summary(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WorkspaceSummary:
    owned_datasets = select(Dataset.id).where(Dataset.owner_id == user.id)

    counts = WorkspaceCounts(
        datasets=db.scalar(
            select(func.count()).select_from(Dataset).where(Dataset.owner_id == user.id)
        )
        or 0,
        connections=db.scalar(
            select(func.count())
            .select_from(DBConnection)
            .where(DBConnection.owner_id == user.id)
        )
        or 0,
        models=db.scalar(
            select(func.count())
            .select_from(Experiment)
            .where(
                Experiment.dataset_id.in_(owned_datasets),
                Experiment.status == STATUS_COMPLETED,
            )
        )
        or 0,
        chats=db.scalar(
            select(func.count())
            .select_from(Conversation)
            .where(Conversation.dataset_id.in_(owned_datasets))
        )
        or 0,
    )

    recent_datasets = [
        RecentDataset(
            id=d.id,
            name=d.name,
            n_rows=d.n_rows,
            n_columns=d.n_columns,
            source_type=d.source_type,
            created_at=d.created_at,
        )
        for d in db.scalars(
            select(Dataset)
            .where(Dataset.owner_id == user.id)
            .order_by(Dataset.created_at.desc())
            .limit(6)
        )
    ]

    recent_models = [
        RecentModel(
            id=exp.id,
            dataset_id=exp.dataset_id,
            dataset_name=name,
            target=exp.target_column,
            problem_type=exp.problem_type,
            best_model_name=exp.best_model_name,
            created_at=exp.completed_at or exp.created_at,
        )
        for exp, name in db.execute(
            select(Experiment, Dataset.name)
            .join(Dataset, Experiment.dataset_id == Dataset.id)
            .where(Dataset.owner_id == user.id, Experiment.status == STATUS_COMPLETED)
            .order_by(Experiment.created_at.desc())
            .limit(5)
        )
    ]

    recent_queries = [
        RecentQuery(
            id=q.id,
            connection_id=q.connection_id,
            connection_name=name,
            question=q.question,
            created_at=q.created_at,
        )
        for q, name in db.execute(
            select(ConnectionQuery, DBConnection.name)
            .join(DBConnection, ConnectionQuery.connection_id == DBConnection.id)
            .where(DBConnection.owner_id == user.id)
            .order_by(ConnectionQuery.created_at.desc())
            .limit(5)
        )
    ]

    return WorkspaceSummary(
        counts=counts,
        recent_datasets=recent_datasets,
        recent_models=recent_models,
        recent_queries=recent_queries,
    )
