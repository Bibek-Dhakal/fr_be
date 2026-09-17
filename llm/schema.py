from enum import Enum

from pydantic import BaseModel, Field, field_validator


class TriageCategory(str, Enum):
    BILLING = "billing"
    BUG = "bug"
    FEATURE = "feature"
    OTHER = "other"


class TriageUrgency(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class TriageRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)

    @field_validator("text")
    @classmethod
    def text_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must not be blank")
        return value


class TriageResult(BaseModel):
    category: TriageCategory
    urgency: TriageUrgency
    confidence: float = Field(..., ge=0.0, le=1.0)
    reason: str = Field(..., min_length=1, max_length=300)
