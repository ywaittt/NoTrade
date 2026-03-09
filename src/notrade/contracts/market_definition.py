from __future__ import annotations

"""Canonical market-definition contract used across the runtime spine."""

from datetime import time

from pydantic import AwareDatetime, field_validator, model_validator

from notrade.constants import ssot_list, ssot_mapping, ssot_value

from .base import NoTradeModel, PositiveDecimal, ensure_allowed


class MarketDefinition(NoTradeModel):
    """Canonical market definition for one supported market instance.

    Producer:
        market parsing / normalization layer.

    Consumers:
        probability provider, decision engine, simulator, ledger writer.

    Notes:
        `event_ts_utc` is the canonical expiry / resolution timestamp for the contract.
        It is intentionally separate from the live market snapshot.
    """

    market_id: str
    market_name: str
    market_type: str
    asset: str
    rule_type: str
    event_ts_utc: AwareDatetime
    resolution_tz: str
    resolution_local_time: time
    ref_source: str
    ref_pair: str
    candle_interval: str
    price_metric: str
    strike_price: PositiveDecimal | None = None
    range_low: PositiveDecimal | None = None
    range_high: PositiveDecimal | None = None
    external_url: str | None = None
    notes: str | None = None

    @property
    def expires_at_utc(self) -> AwareDatetime:
        """Alias for event_ts_utc to make expiry semantics explicit in runtime code."""
        return self.event_ts_utc

    @field_validator("market_type")
    @classmethod
    def validate_market_type(cls, value: str) -> str:
        return ensure_allowed(value, ssot_list("contracts", "MARKET_TYPES"), "market_type") or value

    @field_validator("rule_type")
    @classmethod
    def validate_rule_type(cls, value: str) -> str:
        return ensure_allowed(value, ssot_list("market_rules", "RULE_TYPES"), "rule_type") or value

    @field_validator("asset")
    @classmethod
    def validate_asset(cls, value: str) -> str:
        allowed_assets = tuple(ssot_mapping("market_rules", "PAIR_BY_ASSET").keys())
        return ensure_allowed(value, allowed_assets, "asset") or value

    @model_validator(mode="after")
    def validate_market_shape(self) -> "MarketDefinition":
        pair_by_asset = ssot_mapping("market_rules", "PAIR_BY_ASSET")
        expected_pair = pair_by_asset[self.asset]
        if self.ref_pair != expected_pair:
            raise ValueError(
                f"ref_pair must match the canonical pair for {self.asset}: {expected_pair}"
            )

        if self.market_type == "DAILY_HIT_PRICE":
            canon_tz = ssot_value("market_rules", "CANON_TZ")
            canon_source = ssot_value("market_rules", "CANON_SOURCE")
            canon_interval = ssot_value("market_rules", "CANON_CANDLE_INTERVAL")
            canon_metric = ssot_value("market_rules", "CANON_PRICE_METRIC")
            canon_snapshot_time = time.fromisoformat(
                ssot_value("market_rules", "CANON_SNAPSHOT_TIME_LOCAL")
            )

            if self.resolution_tz != canon_tz:
                raise ValueError(
                    f"resolution_tz must be {canon_tz} for DAILY_HIT_PRICE markets."
                )
            if self.ref_source != canon_source:
                raise ValueError(
                    f"ref_source must be {canon_source} for DAILY_HIT_PRICE markets."
                )
            if self.candle_interval != canon_interval:
                raise ValueError(
                    f"candle_interval must be {canon_interval} for DAILY_HIT_PRICE markets."
                )
            if self.price_metric != canon_metric:
                raise ValueError(
                    f"price_metric must be {canon_metric} for DAILY_HIT_PRICE markets."
                )
            if self.resolution_local_time != canon_snapshot_time:
                raise ValueError(
                    "resolution_local_time must be "
                    f"{canon_snapshot_time.isoformat(timespec='minutes')} "
                    "for DAILY_HIT_PRICE markets."
                )

        if self.rule_type == "SNAPSHOT_CLOSE_IN_RANGE":
            if self.range_low is None or self.range_high is None:
                raise ValueError("Range markets require both range_low and range_high.")
            if self.range_low >= self.range_high:
                raise ValueError("range_low must be smaller than range_high.")
            if self.strike_price is not None:
                raise ValueError("strike_price must be null for range markets.")
        else:
            if self.strike_price is None:
                raise ValueError("strike_price is required for non-range rule types.")
            if self.range_low is not None or self.range_high is not None:
                raise ValueError("range_low/range_high are allowed only for range markets.")

        return self
