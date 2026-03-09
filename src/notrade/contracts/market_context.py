from __future__ import annotations

"""Composite decision-time market context for the runtime spine."""

from datetime import timedelta

from pydantic import AwareDatetime, model_validator

from .base import NoTradeModel
from .market_definition import MarketDefinition
from .market_snapshot import MarketSnapshot


class MarketContext(NoTradeModel):
    """Composite decision-time market context.

    This keeps the long-lived contract definition separate from the live snapshot,
    while preserving a single runtime object for the decision engine.
    """

    definition: MarketDefinition
    snapshot: MarketSnapshot

    @property
    def market_id(self) -> str:
        return self.definition.market_id

    @property
    def market_type(self) -> str:
        return self.definition.market_type

    @property
    def asset(self) -> str:
        return self.definition.asset

    @property
    def event_ts_utc(self) -> AwareDatetime:
        return self.definition.event_ts_utc

    @property
    def as_of_ts_utc(self) -> AwareDatetime:
        return self.snapshot.as_of_ts_utc

    @property
    def time_to_expiry(self) -> timedelta:
        return self.definition.event_ts_utc - self.snapshot.as_of_ts_utc

    @model_validator(mode="after")
    def validate_context(self) -> "MarketContext":
        if self.snapshot.as_of_ts_utc > self.definition.event_ts_utc:
            raise ValueError("snapshot.as_of_ts_utc cannot be later than definition.event_ts_utc.")

        computed_minutes = max(0, int(self.time_to_expiry.total_seconds() // 60))
        if abs(computed_minutes - self.snapshot.time_to_expiry_min) > 1:
            raise ValueError(
                "snapshot.time_to_expiry_min must match definition.event_ts_utc within a 1-minute tolerance."
            )

        return self
