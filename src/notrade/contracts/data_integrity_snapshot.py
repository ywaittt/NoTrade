from __future__ import annotations

"""Integrity and feature-validity contract for decision-time snapshots."""

from pydantic import AwareDatetime, Field, model_validator

from notrade.constants import get_pass_codes, ssot_value

from .base import NoTradeModel, ensure_allowed


class DataIntegritySnapshot(NoTradeModel):
    """Decision-time integrity verdict.

    Producer:
        data layer / feature validation layer.

    Consumers:
        probability provider, decision engine, runtime logging.
    """

    as_of_ts_utc: AwareDatetime
    poly_staleness_s: int = Field(ge=0)
    ref_staleness_s: int = Field(ge=0)
    data_latency_ms: int = Field(ge=0)
    integrity_ok: bool
    core_features_valid: bool
    v2_features_available: bool = False
    dominant_pass_code: str | None = None
    integrity_notes: str | None = None
    invalid_cooldown_min: int = Field(
        default_factory=lambda: int(ssot_value("data_layer", "DECISION_INTEGRITY_WINDOW_MIN")),
        ge=0,
    )

    @model_validator(mode="after")
    def validate_integrity_contract(self) -> "DataIntegritySnapshot":
        if self.dominant_pass_code is not None:
            ensure_allowed(self.dominant_pass_code, get_pass_codes(), "dominant_pass_code")

        max_poly = int(ssot_value("data_layer", "POLY_MAX_STALENESS_S"))
        max_ref = int(ssot_value("data_layer", "REF_MAX_STALENESS_S"))

        if self.integrity_ok:
            if self.poly_staleness_s > max_poly:
                raise ValueError(
                    f"integrity_ok cannot be true when poly_staleness_s > {max_poly}."
                )
            if self.ref_staleness_s > max_ref:
                raise ValueError(
                    f"integrity_ok cannot be true when ref_staleness_s > {max_ref}."
                )
            if not self.core_features_valid:
                raise ValueError(
                    "integrity_ok cannot be true when core_features_valid is false."
                )
            if self.dominant_pass_code is not None:
                raise ValueError(
                    "dominant_pass_code must be null when integrity_ok is true."
                )
        else:
            if self.dominant_pass_code is None:
                raise ValueError(
                    "dominant_pass_code is required when integrity_ok is false."
                )

        return self
