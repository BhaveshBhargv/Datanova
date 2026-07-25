"""Pydantic schemas for cleaning transformations."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.services.transform import OPERATIONS


class TransformationCreate(BaseModel):
    operation: str
    params: dict = {}

    @field_validator("operation")
    @classmethod
    def _known_operation(cls, v: str) -> str:
        if v not in OPERATIONS:
            raise ValueError(
                f"Unknown operation '{v}'. Allowed: {', '.join(OPERATIONS)}"
            )
        return v


class TransformationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_index: int
    operation: str
    params: dict
    created_at: datetime
