"""Database access helpers for external DB connections."""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.db_connection import DBConnection
from app.schemas.connection import ConnectionCreate


def create(
    db: Session,
    owner_id: uuid.UUID,
    data: ConnectionCreate,
    encrypted_password: bytes | None,
) -> DBConnection:
    conn = DBConnection(
        owner_id=owner_id,
        name=data.name,
        dialect=data.dialect,
        host=data.host,
        port=data.port,
        database=data.database,
        username=data.username,
        encrypted_password=encrypted_password,
    )
    db.add(conn)
    db.commit()
    db.refresh(conn)
    return conn


def list_for_owner(db: Session, owner_id: uuid.UUID) -> list[DBConnection]:
    return list(
        db.scalars(
            select(DBConnection)
            .where(DBConnection.owner_id == owner_id)
            .order_by(DBConnection.created_at.desc())
        )
    )


def get_owned(
    db: Session, owner_id: uuid.UUID, connection_id: uuid.UUID
) -> DBConnection | None:
    return db.scalar(
        select(DBConnection).where(
            DBConnection.id == connection_id, DBConnection.owner_id == owner_id
        )
    )


def delete(db: Session, connection: DBConnection) -> None:
    db.delete(connection)
    db.commit()
