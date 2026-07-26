"""Conversational AI assistant routes."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.crud import conversation as conv_crud
from app.crud import dataset as dataset_crud
from app.models.conversation import Conversation
from app.models.dataset import Dataset
from app.models.user import User
from app.schemas.conversation import (
    ConversationCreate,
    ConversationDetail,
    ConversationRead,
    MessageCreate,
    MessageRead,
)
from app.services import assistant, cleaning

router = APIRouter(tags=["assistant"])


def _dataset_or_404(db: Session, user: User, dataset_id: uuid.UUID) -> Dataset:
    dataset = dataset_crud.get_owned(db, user.id, dataset_id)
    if dataset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found."
        )
    return dataset


def _conversation_or_404(
    db: Session, user: User, conversation_id: uuid.UUID
) -> tuple[Conversation, Dataset]:
    conv = conv_crud.get(db, conversation_id)
    if conv is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found."
        )
    dataset = dataset_crud.get_owned(db, user.id, conv.dataset_id)
    if dataset is None:  # not owned by this user
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found."
        )
    return conv, dataset


@router.get(
    "/datasets/{dataset_id}/conversations", response_model=list[ConversationRead]
)
def list_conversations(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    dataset = _dataset_or_404(db, user, dataset_id)
    return conv_crud.list_for_dataset(db, dataset.id)


@router.post(
    "/datasets/{dataset_id}/conversations",
    response_model=ConversationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_conversation(
    dataset_id: uuid.UUID,
    data: ConversationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Conversation:
    dataset = _dataset_or_404(db, user, dataset_id)
    return conv_crud.create_conversation(db, dataset.id, data.title)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Conversation:
    conv, _ = _conversation_or_404(db, user, conversation_id)
    return conv


@router.post(
    "/conversations/{conversation_id}/messages", response_model=MessageRead
)
def post_message(
    conversation_id: uuid.UUID,
    data: MessageCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conv, dataset = _conversation_or_404(db, user, conversation_id)

    # Persist the user's question.
    conv_crud.add_message(db, conv.id, "user", content=data.content)

    # Build recent history and run the assistant against the current data.
    history = [
        (m.role, m.content) for m in conv_crud.list_messages(db, conv.id)
    ]
    df = cleaning.load_current(dataset)
    result = assistant.answer(df, data.content, history)

    return conv_crud.add_message(db, conv.id, "assistant", **result)


@router.delete(
    "/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_conversation(
    conversation_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    conv, _ = _conversation_or_404(db, user, conversation_id)
    conv_crud.delete(db, conv)
