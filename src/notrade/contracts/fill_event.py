from __future__ import annotations

"""Execution-level fill contract for real or simulated trades."""

from decimal import Decimal

from pydantic import AwareDatetime, AliasChoices, Field, model_validator

from notrade.constants import ssot_list

from .base import NoTradeModel, NonNegativeDecimal, PositiveDecimal, Probability, ensure_allowed


class FillEvent(NoTradeModel):
    """Normalized fill payload.

    Producer:
        paper-trading simulator or future execution adapter.

    Consumers:
        portfolio/accounting spine and ledger writer.

    Notes:
        `requested_amount` uses a validation alias for the older `amount` field so the
        contract can absorb early-stage payloads without forcing immediate upstream churn.

        Order type assumptions stay outside this contract for now. The simulator can keep
        them in its own fill-policy config, while the fill event records only what was
        requested and what was actually obtained.
    """

    event_id: str
    market_id: str
    decision_group_id: str
    tx_type: str
    amount_type: str
    requested_amount: PositiveDecimal = Field(
        validation_alias=AliasChoices("requested_amount", "amount")
    )
    occurred_at_utc: AwareDatetime
    side: str | None = None
    requested_price: Probability | None = None
    filled_price: Probability | None = Field(
        default=None,
        validation_alias=AliasChoices("filled_price", "fill_price"),
    )
    filled_shares: PositiveDecimal | None = None
    filled_notional_usd: NonNegativeDecimal | None = None
    fee_usd: NonNegativeDecimal = Field(default=0)
    slippage_abs: NonNegativeDecimal | None = None
    requested_at_utc: AwareDatetime | None = None
    venue: str = "POLYMARKET_PAPER"
    notes: str | None = None

    @model_validator(mode="after")
    def validate_fill(self) -> "FillEvent":
        ensure_allowed(self.tx_type, ssot_list("contracts", "FILL_EVENT_TYPES"), "tx_type")
        ensure_allowed(self.amount_type, ssot_list("contracts", "AMOUNT_TYPES"), "amount_type")

        if self.side is not None:
            ensure_allowed(self.side, ssot_list("contracts", "SIDES"), "side")

        if self.requested_at_utc is not None and self.occurred_at_utc < self.requested_at_utc:
            raise ValueError("occurred_at_utc cannot be earlier than requested_at_utc.")

        if self.tx_type in {"BUY", "SELL"}:
            if self.side is None:
                raise ValueError(f"side is required for {self.tx_type} events.")
            if self.requested_price is None:
                raise ValueError(f"requested_price is required for {self.tx_type} events.")
            if self.filled_price is None:
                raise ValueError(f"filled_price is required for {self.tx_type} events.")
            if self.filled_shares is None:
                raise ValueError(f"filled_shares is required for {self.tx_type} events.")
        elif self.tx_type in {"MERGE", "CONVERT"} and self.side is not None:
            raise ValueError(f"side must be null for {self.tx_type} events.")

        if self.slippage_abs is not None:
            if self.requested_price is None or self.filled_price is None:
                raise ValueError(
                    "slippage_abs requires both requested_price and filled_price to be present."
                )

        if (
            self.slippage_abs is None
            and self.requested_price is not None
            and self.filled_price is not None
        ):
            object.__setattr__(
                self,
                "slippage_abs",
                abs(Decimal(self.filled_price) - Decimal(self.requested_price)),
            )

        if self.filled_notional_usd is not None:
            if self.filled_price is None or self.filled_shares is None:
                raise ValueError(
                    "filled_notional_usd requires both filled_price and filled_shares to be present."
                )
            expected = Decimal(self.filled_price) * Decimal(self.filled_shares)
            if self.filled_notional_usd != expected:
                raise ValueError(
                    "filled_notional_usd must equal filled_price * filled_shares exactly."
                )

        if (
            self.filled_notional_usd is None
            and self.filled_price is not None
            and self.filled_shares is not None
        ):
            object.__setattr__(
                self,
                "filled_notional_usd",
                Decimal(self.filled_price) * Decimal(self.filled_shares),
            )

        return self
