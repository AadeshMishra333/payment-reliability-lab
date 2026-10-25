"""Input contracts for synthetic payments."""

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator


class PaymentInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    amount_minor: int = Field(gt=0, le=10_000_000)
    currency: Literal["INR"] = "INR"
    merchant_reference: str = Field(min_length=1, max_length=80)

    @field_validator("merchant_reference")
    @classmethod
    def nonblank_reference(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Enter a merchant reference.")
        return value


class EventInput(BaseModel):
    """A manually simulated provider event, not an external webhook."""

    model_config = ConfigDict(extra="forbid", strict=True)

    event_id: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    status: Literal["pending", "succeeded", "failed"]
