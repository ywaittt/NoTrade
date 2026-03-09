from __future__ import annotations
from decimal import Decimal

"""Portfolio-level state consumed by policy logic."""

from pydantic import AwareDatetime, Field, computed_field, model_validator

from notrade.constants import get_pass_codes

from .base import NoTradeModel, NonNegativeDecimal, PositiveDecimal, Probability, ensure_allowed
from .open_position import OpenPosition


class PortfolioState(NoTradeModel):
    """Portfolio snapshot for one evaluation timestamp.

    Producer:
        paper-trading simulator or future portfolio/accounting spine.

    Consumers:
        decision engine, CLI/runtime summary, ledger writer.

    Notes:
        Cooldown is modeled as a portfolio/runtime guard through cooldown_until_utc,
        not as a standalone position_state. This keeps the core state machine clean:
        FLAT or OPEN at the thesis level, cooldown as a temporary policy gate.
    """

    as_of_ts_utc: AwareDatetime
    bankroll_usd: PositiveDecimal
    cash_usd: NonNegativeDecimal
    total_invested_usd: NonNegativeDecimal
    weekly_drawdown_pct: Decimal = Decimal("0")
    monthly_drawdown_pct: Decimal = Decimal("0")
    btc_direction_exposure_pct: Decimal = Decimal("0")
    total_correlated_exposure_pct: Decimal = Decimal("0")
    safety_mode: bool = False
    open_positions: list[OpenPosition] = Field(default_factory=list)
    open_positions_count: int | None = Field(default=None, ge=0)
    cooldown_until_utc: AwareDatetime | None = None
    cooldown_reason_pass_code: str | None = None

    @computed_field(return_type=bool)
    @property
    def in_cooldown(self) -> bool:
        return self.cooldown_until_utc is not None and self.cooldown_until_utc > self.as_of_ts_utc

    @model_validator(mode="after")
    def validate_portfolio(self) -> "PortfolioState":
        if self.cash_usd > self.bankroll_usd:
            raise ValueError("cash_usd cannot exceed bankroll_usd.")
        if self.total_invested_usd > self.bankroll_usd:
            raise ValueError("total_invested_usd cannot exceed bankroll_usd.")

        expected_count = len(self.open_positions)
        if self.open_positions_count is None:
            object.__setattr__(self, "open_positions_count", expected_count)
        elif self.open_positions_count != expected_count:
            raise ValueError("open_positions_count must match len(open_positions).")

        if not self.open_positions and self.total_invested_usd != 0:
            raise ValueError(
                "total_invested_usd must be 0 when there are no open_positions."
            )

        position_ids = [position.position_id for position in self.open_positions]
        if len(position_ids) != len(set(position_ids)):
            raise ValueError("open_positions cannot contain duplicate position_id values.")

        thesis_keys = [(position.market_id, position.side) for position in self.open_positions]
        if len(thesis_keys) != len(set(thesis_keys)):
            raise ValueError(
                "open_positions must be normalized to one position per (market_id, side) thesis."
            )

        if self.cooldown_reason_pass_code is not None:
            ensure_allowed(
                self.cooldown_reason_pass_code,
                get_pass_codes(),
                "cooldown_reason_pass_code",
            )

        if self.cooldown_until_utc is None and self.cooldown_reason_pass_code is not None:
            raise ValueError(
                "cooldown_reason_pass_code cannot be set when cooldown_until_utc is null."
            )
        if self.cooldown_until_utc is not None and self.cooldown_reason_pass_code is None:
            raise ValueError(
                "cooldown_reason_pass_code is required when cooldown_until_utc is set."
            )
        if self.cooldown_until_utc is not None and self.cooldown_until_utc < self.as_of_ts_utc:
            raise ValueError("cooldown_until_utc cannot be earlier than as_of_ts_utc.")

        return self
