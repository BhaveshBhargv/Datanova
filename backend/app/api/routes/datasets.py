"""Dataset routes: upload, list, detail, preview, rename, delete."""
import uuid
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.storage import storage
from app.crud import dataset as dataset_crud
from app.crud import experiment as experiment_crud
from app.crud import transformation as transformation_crud
from app.models.dataset import SOURCE_UPLOAD, STATUS_READY, Dataset
from app.models.user import User
from app.schemas.chart import ChartData, ChartSpec
from app.schemas.dataset import DatasetPreview, DatasetRead, DatasetUpdate
from app.schemas.eda import EdaSummary, ExplainRequest, ExplainResponse
from app.schemas.insights import InsightsResponse
from app.schemas.profile import DatasetProfile
from app.schemas.transformation import TransformationCreate, TransformationRead
from app.models.experiment import STATUS_COMPLETED
from app.services import (
    charts,
    cleaning,
    eda,
    ingest,
    insights as insights_service,
    narrate,
    profile,
    report as report_service,
    report_excel,
    report_pdf,
    transform,
)

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
    columns, records = ingest.preview(cleaning.current_path(dataset), rows)
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
    for rel in (dataset.parquet_path, dataset.original_path, dataset.cleaned_path):
        if rel:
            storage.delete(rel)
    dataset_crud.delete(db, dataset)


# --- Profiling & cleaning (Phase 3) ---------------------------------------


@router.get("/{dataset_id}/profile", response_model=DatasetProfile)
def profile_dataset(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    dataset = _get_or_404(db, user, dataset_id)
    return profile.profile_dataframe(cleaning.load_current(dataset))


@router.get("/{dataset_id}/transformations", response_model=list[TransformationRead])
def list_transformations(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    dataset = _get_or_404(db, user, dataset_id)
    return transformation_crud.list_for_dataset(db, dataset.id)


@router.post("/{dataset_id}/transformations", response_model=DatasetRead)
def apply_transformation(
    dataset_id: uuid.UUID,
    step: TransformationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Dataset:
    dataset = _get_or_404(db, user, dataset_id)
    steps = transformation_crud.list_for_dataset(db, dataset.id)

    # Validate by dry-running the step against the current data before saving.
    try:
        transform.apply_step(cleaning.load_current(dataset), step.operation, step.params)
    except transform.TransformError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    transformation_crud.add(
        db, dataset.id, len(steps), step.operation, step.params
    )
    steps = transformation_crud.list_for_dataset(db, dataset.id)
    cleaning.rebuild(db, dataset, steps)
    return dataset


@router.post("/{dataset_id}/transformations/undo", response_model=DatasetRead)
def undo_transformation(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Dataset:
    dataset = _get_or_404(db, user, dataset_id)
    steps = transformation_crud.list_for_dataset(db, dataset.id)
    if steps:
        transformation_crud.delete_last(db, steps)
        cleaning.rebuild(db, dataset, transformation_crud.list_for_dataset(db, dataset.id))
    return dataset


@router.post("/{dataset_id}/transformations/reset", response_model=DatasetRead)
def reset_transformations(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Dataset:
    dataset = _get_or_404(db, user, dataset_id)
    transformation_crud.clear(db, dataset.id)
    cleaning.rebuild(db, dataset, [])
    return dataset


# --- EDA & visualization (Phase 4) ----------------------------------------


@router.get("/{dataset_id}/eda/summary", response_model=EdaSummary)
def eda_summary(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    dataset = _get_or_404(db, user, dataset_id)
    return eda.summary(cleaning.load_current(dataset))


@router.post("/{dataset_id}/chart", response_model=ChartData)
def build_chart(
    dataset_id: uuid.UUID,
    spec: ChartSpec,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    dataset = _get_or_404(db, user, dataset_id)
    try:
        return charts.build(cleaning.load_current(dataset), spec.model_dump())
    except charts.ChartError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/{dataset_id}/explain", response_model=ExplainResponse)
def explain(
    dataset_id: uuid.UUID,
    req: ExplainRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ExplainResponse:
    dataset = _get_or_404(db, user, dataset_id)
    try:
        text, source = narrate.explain(
            cleaning.load_current(dataset),
            req.kind,
            req.spec.model_dump() if req.spec else None,
        )
    except (charts.ChartError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return ExplainResponse(text=text, source=source)


# --- Insights & recommendations (Phase 9) ---------------------------------


def _latest_completed_experiment(db: Session, dataset_id: uuid.UUID):
    for exp in experiment_crud.list_for_dataset(db, dataset_id):
        if exp.status == STATUS_COMPLETED and exp.model_path:
            return exp
    return None


@router.get("/{dataset_id}/insights", response_model=InsightsResponse)
async def get_insights(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> InsightsResponse:
    dataset = _get_or_404(db, user, dataset_id)
    df = cleaning.load_current(dataset)
    experiment = _latest_completed_experiment(db, dataset.id)
    items = await run_in_threadpool(
        insights_service.generate_insights, df, experiment
    )
    return InsightsResponse(
        total=len(items), counts=insights_service.counts(items), insights=items
    )


@router.post("/{dataset_id}/insights/narrative", response_model=ExplainResponse)
async def insights_narrative(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ExplainResponse:
    dataset = _get_or_404(db, user, dataset_id)
    df = cleaning.load_current(dataset)
    experiment = _latest_completed_experiment(db, dataset.id)
    items = await run_in_threadpool(
        insights_service.generate_insights, df, experiment
    )
    text, source = narrate.explain_insights(items)
    return ExplainResponse(text=text, source=source)


# --- Reporting & export (Phase 10) ----------------------------------------


def _safe_filename(name: str) -> str:
    keep = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in name)
    return keep or "report"


@router.get("/{dataset_id}/report")
async def report_json(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    dataset = _get_or_404(db, user, dataset_id)
    return await run_in_threadpool(report_service.assemble, db, dataset)


@router.get("/{dataset_id}/report/pdf")
async def report_pdf_download(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    dataset = _get_or_404(db, user, dataset_id)
    report = await run_in_threadpool(report_service.assemble, db, dataset)
    pdf = await run_in_threadpool(report_pdf.build_pdf, report)
    filename = f"{_safe_filename(dataset.name)}_report.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{dataset_id}/report/excel")
async def report_excel_download(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    dataset = _get_or_404(db, user, dataset_id)
    report = await run_in_threadpool(report_service.assemble, db, dataset)
    xlsx = await run_in_threadpool(report_excel.build_excel, report)
    filename = f"{_safe_filename(dataset.name)}_report.xlsx"
    return Response(
        content=xlsx,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
