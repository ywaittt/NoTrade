from __future__ import annotations

"""Live market-level exposure contract."""

from pydantic import AwareDatetime, model_validator

from notrade.constants import ssot_list, ssot_mapping

from .base import NoTradeModel, PositiveDecimal, Probability, ensure_allowed


class OpenPosition(NoTradeModel):
    """Normalized representation of one open thesis.

    Producer:
        portfolio/accounting layer rebuilt from fills or ledger history.

    Consumers:
        decision engine and simulator.
    """

    position_id: str
    decision_group_id: str
    market_id: str
    asset: str
    side: str
    shares: PositiveDecimal
    avg_entry_price: Probability
    stake_usd: PositiveDecimal
    opened_at_utc: AwareDatetime
    last_fill_ts_utc: AwareDatetime | None = None
    thesis_intact: bool = True

    @model_validator(mode="after")
    def validate_position(self) -> "OpenPosition":
        allowed_assets = tuple(ssot_mapping("market_rules", "PAIR_BY_ASSET").keys())
        ensure_allowed(self.asset, allowed_assets, "asset")
        ensure_allowed(self.side, ssot_list("contracts", "SIDES"), "side")

        if self.last_fill_ts_utc is not None and self.last_fill_ts_utc < self.opened_at_utc:
            raise ValueError("last_fill_ts_utc cannot be earlier than opened_at_utc.")

        return self
