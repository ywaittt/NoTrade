from __future__ import annotations

"""Probability-layer contract consumed by downstream policy logic."""

from pydantic import AwareDatetime, model_validator

from notrade.constants import ssot_list

from .base import NoTradeModel, NonNegativeDecimal, Probability, SignedUnitDecimal, ensure_allowed


class ProbabilitySnapshot(NoTradeModel):
    """Calibrated probability payload for one market and timestamp.

    Producer:
        probability provider / model stub.

    Consumers:
        decision engine, simulator, ledger writer.
    """

    market_id: str
    as_of_ts_utc: AwareDatetime
    market_prob_yes: Probability
    model_prob_yes: Probability
    edge_net: SignedUnitDecimal
    raw_prob_yes: Probability
    confidence_band_low: Probability
    confidence_band_high: Probability
    uncertainty_score: str
    calibration_status: str
    model_family: str
    model_version: str
    calibration_window_id: str | None = None
    calibration_method: str | None = None
    slippage_est_cents: NonNegativeDecimal | None = None

    @model_validator(mode="after")
    def validate_probability_shape(self) -> "ProbabilitySnapshot":
        ensure_allowed(
            self.uncertainty_score,
            ssot_list("probability_model", "UNCERTAINTY_LEVELS"),
            "uncertainty_score",
        )
        ensure_allowed(
            self.calibration_status,
            ssot_list("probability_model", "CALIBRATION_STATUS"),
            "calibration_status",
        )

        if self.confidence_band_low > self.confidence_band_high:
            raise ValueError("confidence_band_low must be <= confidence_band_high.")
        if not (self.confidence_band_low <= self.model_prob_yes <= self.confidence_band_high):
            raise ValueError(
                "model_prob_yes must lie inside [confidence_band_low, confidence_band_high]."
            )

        return self
