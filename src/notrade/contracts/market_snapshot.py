from __future__ import annotations

"""Live decision-time market snapshot for one Polymarket market."""

from decimal import Decimal

from pydantic import AwareDatetime, Field, computed_field, model_validator

from .base import NoTradeModel, NonNegativeDecimal, Probability, SignedUnitDecimal


class MarketSnapshot(NoTradeModel):
    """Decision-time live snapshot for one market.

    Producer:
        live market-data adapter or simulator snapshot builder.

    Consumers:
        decision engine, simulator, probability provider, ledger writer.

    Semantics:
        `market_prob_yes` and `market_prob_no` are the best currently executable
        entry prices for taking YES or NO exposure. In a normal Polymarket book,
        these correspond to the taker-side asks for YES and NO.

        Because they represent side-specific executable prices rather than a single
        midpoint probability, they are *not* required to sum to exactly 1.00.
        They may exceed 1.00 in total because of spread / overround.
    """

    as_of_ts_utc: AwareDatetime
    market_prob_yes: Probability
    market_prob_no: Probability
    best_yes_bid: Probability | None = None
    best_yes_ask: Probability | None = None
    best_no_bid: Probability | None = None
    best_no_ask: Probability | None = None
    quoted_spread_pct: NonNegativeDecimal | None = None
    yes_depth_usd: NonNegativeDecimal | None = None
    no_depth_usd: NonNegativeDecimal | None = None
    liquidity_score: NonNegativeDecimal | None = None
    time_to_expiry_min: int = Field(ge=0)
    quote_source: str = "POLYMARKET"

    @computed_field(return_type=NonNegativeDecimal | None)
    @property
    def yes_spread_abs(self) -> Decimal | None:
        if self.best_yes_bid is None or self.best_yes_ask is None:
            return None
        return self.best_yes_ask - self.best_yes_bid

    @computed_field(return_type=NonNegativeDecimal | None)
    @property
    def no_spread_abs(self) -> Decimal | None:
        if self.best_no_bid is None or self.best_no_ask is None:
            return None
        return self.best_no_ask - self.best_no_bid

    @computed_field(return_type=Probability | None)
    @property
    def midpoint_prob_yes(self) -> Decimal | None:
        if self.best_yes_bid is None or self.best_yes_ask is None:
            return None
        return (self.best_yes_bid + self.best_yes_ask) / Decimal("2")

    @computed_field(return_type=Probability | None)
    @property
    def midpoint_prob_no(self) -> Decimal | None:
        if self.best_no_bid is None or self.best_no_ask is None:
            return None
        return (self.best_no_bid + self.best_no_ask) / Decimal("2")

    @computed_field(return_type=SignedUnitDecimal)
    @property
    def executable_overround(self) -> Decimal:
        return self.market_prob_yes + self.market_prob_no - Decimal("1")

    @model_validator(mode="after")
    def validate_snapshot(self) -> "MarketSnapshot":
        observed_spreads: list[Decimal] = []

        for bid_attr, ask_attr, label, market_prob_attr in (
            ("best_yes_bid", "best_yes_ask", "YES", "market_prob_yes"),
            ("best_no_bid", "best_no_ask", "NO", "market_prob_no"),
        ):
            bid = getattr(self, bid_attr)
            ask = getattr(self, ask_attr)
            market_prob = getattr(self, market_prob_attr)

            if bid is not None and ask is not None:
                if bid > ask:
                    raise ValueError(f"{label} bid cannot exceed {label} ask.")
                observed_spreads.append(ask - bid)

            if ask is not None and market_prob != ask:
                raise ValueError(
                    f"{market_prob_attr} must match {ask_attr} when executable ask data is present."
                )

        if self.quoted_spread_pct is None and observed_spreads:
            object.__setattr__(self, "quoted_spread_pct", max(observed_spreads))

        if self.quoted_spread_pct is not None and observed_spreads:
            for observed in observed_spreads:
                if observed > self.quoted_spread_pct:
                    raise ValueError(
                        "quoted_spread_pct cannot be smaller than the observed bid/ask spread."
                    )

        return self
