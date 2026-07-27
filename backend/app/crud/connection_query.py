"""Database access helpers for NL->SQL query history."""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.connection_query import ConnectionQuery


def create(db: Session, connection_id: uuid.UUID, **fields) -> ConnectionQuery:
    query = ConnectionQuery(connection_id=connection_id, **fields)
    db.add(query)
    db.commit()
    db.refresh(query)
    return query


def list_for_connection(
    db: Session, connection_id: uuid.UUID, limit: int = 50
) -> list[ConnectionQuery]:
    return list(
        db.scalars(
            select(ConnectionQuery)
            .where(ConnectionQuery.connection_id == connection_id)
            .order_by(ConnectionQuery.created_at.desc())
            .limit(limit)
        )
    )


def get(db: Session, query_id: uuid.UUID) -> ConnectionQuery | None:
    return db.get(ConnectionQuery, query_id)


def delete(db: Session, query: ConnectionQuery) -> None:
    db.delete(query)
    db.commit()
