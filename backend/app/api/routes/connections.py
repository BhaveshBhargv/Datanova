"""External database connection routes: create, list, test, tables, import, delete."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.crypto import decrypt, encrypt
from app.core.database import get_db
from fastapi.concurrency import run_in_threadpool

from app.crud import connection as connection_crud
from app.crud import connection_query as query_crud
from app.crud import dataset as dataset_crud
from app.models.db_connection import DBConnection
from app.models.dataset import SOURCE_DATABASE, STATUS_READY
from app.models.user import User
from app.schemas.connection import (
    ConnectionCreate,
    ConnectionRead,
    ConnectionTestResult,
    ImportRequest,
    TableList,
)
from app.schemas.dataset import DatasetRead
from app.schemas.nl_sql import (
    NLQueryRequest,
    NLQueryResponse,
    QueryHistoryItem,
    SchemaResponse,
)
from app.services import db_import, ingest, nl_sql

router = APIRouter(prefix="/connections", tags=["connections"])


def _get_or_404(db: Session, user: User, connection_id: uuid.UUID) -> DBConnection:
    conn = connection_crud.get_owned(db, user.id, connection_id)
    if conn is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found."
        )
    return conn


def _engine_for(conn: DBConnection) -> Engine:
    password = decrypt(conn.encrypted_password) if conn.encrypted_password else None
    return db_import.build_engine(
        dialect=conn.dialect,
        database=conn.database,
        host=conn.host,
        port=conn.port,
        username=conn.username,
        password=password,
    )


@router.post("", response_model=ConnectionRead, status_code=status.HTTP_201_CREATED)
def create_connection(
    data: ConnectionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DBConnection:
    # Verify connectivity before persisting.
    engine = db_import.build_engine(
        dialect=data.dialect,
        database=data.database,
        host=data.host,
        port=data.port,
        username=data.username,
        password=data.password,
    )
    try:
        db_import.test_connection(engine)
    except db_import.DBImportError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    encrypted = encrypt(data.password) if data.password else None
    return connection_crud.create(db, user.id, data, encrypted)


@router.get("", response_model=list[ConnectionRead])
def list_connections(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[DBConnection]:
    return connection_crud.list_for_owner(db, user.id)


@router.post("/{connection_id}/test", response_model=ConnectionTestResult)
def test_connection(
    connection_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ConnectionTestResult:
    conn = _get_or_404(db, user, connection_id)
    try:
        db_import.test_connection(_engine_for(conn))
    except db_import.DBImportError as exc:
        return ConnectionTestResult(ok=False, message=str(exc))
    return ConnectionTestResult(ok=True, message="Connection successful.")


@router.get("/{connection_id}/tables", response_model=TableList)
def list_connection_tables(
    connection_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TableList:
    conn = _get_or_404(db, user, connection_id)
    try:
        tables = db_import.list_tables(_engine_for(conn))
    except db_import.DBImportError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return TableList(tables=tables)


@router.post(
    "/{connection_id}/import",
    response_model=DatasetRead,
    status_code=status.HTTP_201_CREATED,
)
def import_from_connection(
    connection_id: uuid.UUID,
    data: ImportRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> object:
    conn = _get_or_404(db, user, connection_id)
    engine = _engine_for(conn)
    try:
        if data.table:
            df = db_import.import_table(engine, data.table)
            default_name = data.table
        else:
            df = db_import.import_query(engine, data.query)  # type: ignore[arg-type]
            default_name = "query_result"
    except db_import.DBImportError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    if df.shape[0] == 0 or df.shape[1] == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The import returned no rows or columns.",
        )
    df.columns = [str(c) for c in df.columns]

    dataset_id = uuid.uuid4()
    parquet_rel = ingest.parquet_rel_path(user.id, dataset_id)
    ingest.write_parquet(parquet_rel, df)

    return dataset_crud.create(
        db,
        id=dataset_id,
        owner_id=user.id,
        name=data.name or default_name,
        source_type=SOURCE_DATABASE,
        file_format=None,
        original_path=None,
        parquet_path=parquet_rel,
        n_rows=int(df.shape[0]),
        n_columns=int(df.shape[1]),
        size_bytes=None,
        columns=ingest.column_schema(df),
        status=STATUS_READY,
    )


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_connection(
    connection_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    conn = _get_or_404(db, user, connection_id)
    connection_crud.delete(db, conn)


# --- NL -> SQL (Phase 8) ---------------------------------------------------


@router.get("/{connection_id}/schema", response_model=SchemaResponse)
async def get_schema(
    connection_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SchemaResponse:
    conn = _get_or_404(db, user, connection_id)
    try:
        tables = await run_in_threadpool(nl_sql.introspect_schema, _engine_for(conn))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not read schema: {exc.__class__.__name__}",
        )
    return SchemaResponse(tables=tables)


@router.post("/{connection_id}/query", response_model=NLQueryResponse)
async def run_nl_query(
    connection_id: uuid.UUID,
    data: NLQueryRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> NLQueryResponse:
    conn = _get_or_404(db, user, connection_id)
    result = await run_in_threadpool(nl_sql.answer, conn, data.question)

    # Persist a lightweight history entry.
    query_crud.create(
        db,
        conn.id,
        question=data.question,
        sql=result.get("sql"),
        explanation=result.get("explanation"),
        source=result.get("source"),
        row_count=result.get("row_count"),
        error=result.get("error"),
    )
    return NLQueryResponse(**result)


@router.get("/{connection_id}/queries", response_model=list[QueryHistoryItem])
def list_queries(
    connection_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conn = _get_or_404(db, user, connection_id)
    return query_crud.list_for_connection(db, conn.id)


@router.delete(
    "/{connection_id}/queries/{query_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_query(
    connection_id: uuid.UUID,
    query_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    _get_or_404(db, user, connection_id)
    query = query_crud.get(db, query_id)
    if query is None or query.connection_id != connection_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Query not found."
        )
    query_crud.delete(db, query)
