"""Database access helpers for conversations and messages."""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.conversation import Conversation, Message


def create_conversation(
    db: Session, dataset_id: uuid.UUID, title: str = "Chat"
) -> Conversation:
    conv = Conversation(dataset_id=dataset_id, title=title)
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


def list_for_dataset(db: Session, dataset_id: uuid.UUID) -> list[Conversation]:
    return list(
        db.scalars(
            select(Conversation)
            .where(Conversation.dataset_id == dataset_id)
            .order_by(Conversation.created_at.desc())
        )
    )


def get(db: Session, conversation_id: uuid.UUID) -> Conversation | None:
    return db.get(Conversation, conversation_id)


def add_message(db: Session, conversation_id: uuid.UUID, role: str, **fields) -> Message:
    message = Message(conversation_id=conversation_id, role=role, **fields)
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def list_messages(db: Session, conversation_id: uuid.UUID) -> list[Message]:
    return list(
        db.scalars(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
        )
    )


def delete(db: Session, conversation: Conversation) -> None:
    db.delete(conversation)
    db.commit()
