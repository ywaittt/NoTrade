from __future__ import annotations

"""Decision-engine output contract."""

from decimal import Decimal

from pydantic import AwareDatetime, Field, model_validator

from notrade.constants import get_pass_codes, ssot_list, ssot_value

from .base import NoTradeModel, NonNegativeDecimal, ensure_allowed


class DecisionOutput(NoTradeModel):
    """Final policy verdict for one market and evaluation timestamp.

    Producer:
        decision engine.

    Consumers:
        CLI/runtime spine, ledger writer, simulator.

    Notes:
        `target_side` makes the verdict executable for runtime and simulator use.
        `requested_tx_type` is a minimal execution intent, not a full order plan.
        In MVP semantics:
        - PASS = no transaction intent
        - ENTER = BUY intent on target_side
        - HOLD = no transaction intent, thesis remains active
        - EXIT = SELL intent that fully flattens target_position_id
    """

    decision_id: str
    decision_group_id: str
    market_id: str
    as_of_ts_utc: AwareDatetime
    position_state: str
    action_type: str
    target_side: str | None = None
    target_position_id: str | None = None
    requested_tx_type: str | None = None
    reasoning: str
    safety_mode: bool = False
    edge_threshold_used: NonNegativeDecimal | None = None
    sizing_pct: NonNegativeDecimal = Field(default=0)
    stake_usd: NonNegativeDecimal = Field(default=0)
    risk_ok: bool = True
    pass_code: str | None = None
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_decision(self) -> "DecisionOutput":
        ensure_allowed(
            self.position_state,
            ssot_list("contracts", "POSITION_STATES"),
            "position_state",
        )
        ensure_allowed(
            self.action_type,
            ssot_list("decision_engine", "ACTION_TYPES"),
            "action_type",
        )

        if self.target_side is not None:
            ensure_allowed(self.target_side, ssot_list("contracts", "SIDES"), "target_side")

        if self.requested_tx_type is not None:
            ensure_allowed(
                self.requested_tx_type,
                ssot_list("contracts", "FILL_EVENT_TYPES"),
                "requested_tx_type",
            )

        if self.pass_code is not None:
            ensure_allowed(self.pass_code, get_pass_codes(), "pass_code")

        if self.edge_threshold_used is None:
            threshold_key = (
                "SAFETY_MODE_EDGE_THRESHOLD" if self.safety_mode else "EDGE_NET_THRESHOLD"
            )
            object.__setattr__(
                self,
                "edge_threshold_used",
                Decimal(str(ssot_value("policy", threshold_key))),
            )

        if self.action_type == "PASS":
            if self.position_state != "FLAT":
                raise ValueError("PASS is only valid when position_state is FLAT.")
            if self.pass_code is None:
                raise ValueError("pass_code is required when action_type is PASS.")
            if self.target_side is not None:
                raise ValueError("target_side must be null when action_type is PASS.")
            if self.target_position_id is not None:
                raise ValueError("target_position_id must be null when action_type is PASS.")
            if self.requested_tx_type is not None:
                raise ValueError("requested_tx_type must be null when action_type is PASS.")
            if self.sizing_pct != 0 or self.stake_usd != 0:
                raise ValueError("PASS must have sizing_pct = 0 and stake_usd = 0.")

        elif self.action_type == "ENTER":
            if self.position_state != "FLAT":
                raise ValueError("ENTER is only valid when position_state is FLAT.")
            if self.target_side is None:
                raise ValueError("target_side is required when action_type is ENTER.")
            if self.target_position_id is not None:
                raise ValueError("target_position_id must be null when action_type is ENTER.")
            if self.pass_code is not None:
                raise ValueError("pass_code must be null when action_type is ENTER.")
            if self.requested_tx_type is None:
                object.__setattr__(self, "requested_tx_type", "BUY")
            elif self.requested_tx_type != "BUY":
                raise ValueError("ENTER must use requested_tx_type = BUY.")
            if self.sizing_pct <= 0 or self.stake_usd <= 0:
                raise ValueError("ENTER requires positive sizing_pct and stake_usd.")

        elif self.action_type == "HOLD":
            if self.position_state != "OPEN":
                raise ValueError("HOLD is only valid when position_state is OPEN.")
            if self.target_side is None:
                raise ValueError("target_side is required when action_type is HOLD.")
            if self.target_position_id is None:
                raise ValueError("target_position_id is required when action_type is HOLD.")
            if self.pass_code is not None:
                raise ValueError("pass_code must be null when action_type is HOLD.")
            if self.requested_tx_type is not None:
                raise ValueError("requested_tx_type must be null when action_type is HOLD.")
            if self.sizing_pct != 0 or self.stake_usd != 0:
                raise ValueError("HOLD must not carry a fresh sizing recommendation.")

        elif self.action_type == "EXIT":
            if self.position_state != "OPEN":
                raise ValueError("EXIT is only valid when position_state is OPEN.")
            if self.target_side is None:
                raise ValueError("target_side is required when action_type is EXIT.")
            if self.target_position_id is None:
                raise ValueError("target_position_id is required when action_type is EXIT.")
            if self.pass_code is not None:
                raise ValueError("pass_code must be null when action_type is EXIT.")
            if self.requested_tx_type is None:
                object.__setattr__(self, "requested_tx_type", "SELL")
            elif self.requested_tx_type != "SELL":
                raise ValueError("EXIT must use requested_tx_type = SELL.")
            if self.sizing_pct != 0 or self.stake_usd != 0:
                raise ValueError("EXIT must not carry a fresh sizing recommendation.")

        return self
