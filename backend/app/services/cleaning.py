"""Orchestrates the replay-from-original cleaning model.

The dataset's `parquet_path` is the immutable original. The current data is the
original replayed through all stored transformation steps and cached at
`cleaned_path`. Any change to the step list triggers a full rebuild.
"""
from __future__ import annotations

import pandas as pd
from sqlalchemy.orm import Session

from app.core.storage import storage
from app.models.dataset import Dataset
from app.models.transformation import Transformation
from app.services import ingest, transform


def current_path(dataset: Dataset) -> str:
    """Storage path of the data to read now (cleaned if present, else original)."""
    return dataset.cleaned_path or dataset.parquet_path


def load_current(dataset: Dataset) -> pd.DataFrame:
    return ingest.read_parquet(current_path(dataset))


def rebuild(
    db: Session, dataset: Dataset, steps: list[Transformation]
) -> pd.DataFrame:
    """Replay `steps` on the original, refresh the cached data + dataset shape."""
    df = ingest.read_parquet(dataset.parquet_path)
    df = transform.replay(df, [(s.operation, s.params) for s in steps])

    if steps:
        cleaned_rel = ingest.cleaned_rel_path(dataset.owner_id, dataset.id)
        ingest.write_parquet(cleaned_rel, df)
        dataset.cleaned_path = cleaned_rel
    else:
        if dataset.cleaned_path:
            storage.delete(dataset.cleaned_path)
        dataset.cleaned_path = None

    dataset.n_rows = int(df.shape[0])
    dataset.n_columns = int(df.shape[1])
    dataset.columns = ingest.column_schema(df)
    db.commit()
    db.refresh(dataset)
    return df
