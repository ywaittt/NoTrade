from __future__ import annotations

"""Shared model helpers for NoTrade runtime contracts."""

from decimal import Decimal
from typing import Annotated, Any, Iterable

from pydantic import BaseModel, ConfigDict, Field


Probability = Annotated[Decimal, Field(ge=Decimal("0"), le=Decimal("1"))]
SignedUnitDecimal = Annotated[Decimal, Field(ge=Decimal("-1"), le=Decimal("1"))]
NonNegativeDecimal = Annotated[Decimal, Field(ge=Decimal("0"))]
PositiveDecimal = Annotated[Decimal, Field(gt=Decimal("0"))]


class NoTradeModel(BaseModel):
    """Base model for all executable contracts.

    The runtime contracts should reject unknown fields to catch schema drift early.
    The helper dump methods keep logging / fixture generation ergonomic without adding
    extra wrappers around Pydantic in later stages.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
        populate_by_name=True,
    )

    def to_python_dict(self, *, exclude_none: bool = True) -> dict[str, Any]:
        """Return a Python-mode dictionary for in-process runtime use."""
        return self.model_dump(mode="python", by_alias=True, exclude_none=exclude_none)

    def to_json_dict(self, *, exclude_none: bool = True) -> dict[str, Any]:
        """Return a JSON-safe dictionary for logs, fixtures, and CLI I/O."""
        return self.model_dump(mode="json", by_alias=True, exclude_none=exclude_none)

    def to_json_str(self, *, exclude_none: bool = True, indent: int | None = 2) -> str:
        """Return a JSON string using the contract's canonical serialization settings."""
        return self.model_dump_json(by_alias=True, exclude_none=exclude_none, indent=indent)


def ensure_allowed(value: str | None, allowed: Iterable[str], field_name: str) -> str | None:
    """Validate membership against a canonical allowed-value collection."""
    if value is None:
        return None

    allowed_values = tuple(allowed)
    if value not in allowed_values:
        allowed_str = ", ".join(allowed_values)
        raise ValueError(f"{field_name} must be one of: {allowed_str}")

    return value
