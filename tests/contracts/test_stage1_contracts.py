from datetime import datetime, time, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from notrade.contracts import (
    DataIntegritySnapshot,
    DecisionOutput,
    FillEvent,
    MarketContext,
    MarketDefinition,
    MarketSnapshot,
    OpenPosition,
    PortfolioState,
    ProbabilitySnapshot,
)


UTC = timezone.utc


def build_market_context() -> MarketContext:
    definition = MarketDefinition(
        market_id="btc-2026-03-09-58k",
        market_name="BTC above 58k at 12:00 ET?",
        market_type="DAILY_HIT_PRICE",
        asset="BTC",
        rule_type="SNAPSHOT_CLOSE_ABOVE",
        event_ts_utc=datetime(2026, 3, 9, 16, 0, tzinfo=UTC),
        resolution_tz="America/New_York",
        resolution_local_time=time(12, 0),
        ref_source="BINANCE_SPOT",
        ref_pair="BTCUSDT",
        candle_interval="1m",
        price_metric="CLOSE",
        strike_price=Decimal("58000"),
    )
    snapshot = MarketSnapshot(
        as_of_ts_utc=datetime(2026, 3, 9, 14, 0, tzinfo=UTC),
        market_prob_yes=Decimal("0.42"),
        market_prob_no=Decimal("0.62"),
        best_yes_bid=Decimal("0.40"),
        best_yes_ask=Decimal("0.42"),
        best_no_bid=Decimal("0.60"),
        best_no_ask=Decimal("0.62"),
        yes_depth_usd=Decimal("1200"),
        no_depth_usd=Decimal("1100"),
        time_to_expiry_min=120,
    )
    return MarketContext(definition=definition, snapshot=snapshot)


def build_open_position() -> OpenPosition:
    return OpenPosition(
        position_id="pos-1",
        decision_group_id="grp-1",
        market_id="btc-2026-03-09-58k",
        asset="BTC",
        side="YES",
        shares=Decimal("100"),
        avg_entry_price=Decimal("0.42"),
        stake_usd=Decimal("42"),
        opened_at_utc=datetime(2026, 3, 9, 13, 0, tzinfo=UTC),
    )


def test_market_context_accepts_composed_context() -> None:
    market = build_market_context()
    assert market.asset == "BTC"
    assert market.snapshot.quoted_spread_pct == Decimal("0.02")
    assert market.snapshot.midpoint_prob_yes == Decimal("0.41")
    assert market.snapshot.executable_overround == Decimal("0.04")


def test_market_snapshot_rejects_non_executable_market_prob_when_ask_present() -> None:
    with pytest.raises(ValidationError):
        MarketSnapshot(
            as_of_ts_utc=datetime(2026, 3, 9, 14, 0, tzinfo=UTC),
            market_prob_yes=Decimal("0.41"),
            market_prob_no=Decimal("0.62"),
            best_yes_bid=Decimal("0.40"),
            best_yes_ask=Decimal("0.42"),
            best_no_bid=Decimal("0.60"),
            best_no_ask=Decimal("0.62"),
            time_to_expiry_min=120,
        )


def test_market_context_rejects_bad_time_to_expiry() -> None:
    definition = build_market_context().definition
    with pytest.raises(ValidationError):
        MarketContext(
            definition=definition,
            snapshot=MarketSnapshot(
                as_of_ts_utc=datetime(2026, 3, 9, 14, 0, tzinfo=UTC),
                market_prob_yes=Decimal("0.41"),
                market_prob_no=Decimal("0.61"),
                time_to_expiry_min=50,
            ),
        )


def test_probability_snapshot_rejects_model_prob_outside_band() -> None:
    with pytest.raises(ValidationError):
        ProbabilitySnapshot(
            market_id="btc-2026-03-09-58k",
            as_of_ts_utc=datetime(2026, 3, 9, 14, 0, tzinfo=UTC),
            market_prob_yes=Decimal("0.41"),
            model_prob_yes=Decimal("0.72"),
            edge_net=Decimal("0.26"),
            raw_prob_yes=Decimal("0.74"),
            confidence_band_low=Decimal("0.50"),
            confidence_band_high=Decimal("0.70"),
            uncertainty_score="LOW",
            calibration_status="FRESH",
            model_family="stub-logit",
            model_version="0.1.0",
        )


def test_decision_output_requires_target_side_for_enter() -> None:
    with pytest.raises(ValidationError):
        DecisionOutput(
            decision_id="dec-1",
            decision_group_id="grp-1",
            market_id="btc-2026-03-09-58k",
            as_of_ts_utc=datetime(2026, 3, 9, 14, 0, tzinfo=UTC),
            position_state="FLAT",
            action_type="ENTER",
            reasoning="Edge is clear after costs.",
            sizing_pct=Decimal("0.03"),
            stake_usd=Decimal("15"),
        )


def test_decision_output_requires_pass_code_for_pass() -> None:
    with pytest.raises(ValidationError):
        DecisionOutput(
            decision_id="dec-1",
            decision_group_id="grp-1",
            market_id="btc-2026-03-09-58k",
            as_of_ts_utc=datetime(2026, 3, 9, 14, 0, tzinfo=UTC),
            position_state="FLAT",
            action_type="PASS",
            reasoning="Edge is not large enough after costs.",
        )


def test_decision_output_autosets_requested_tx_type_for_enter() -> None:
    decision = DecisionOutput(
        decision_id="dec-1",
        decision_group_id="grp-1",
        market_id="btc-2026-03-09-58k",
        as_of_ts_utc=datetime(2026, 3, 9, 14, 0, tzinfo=UTC),
        position_state="FLAT",
        action_type="ENTER",
        target_side="YES",
        reasoning="Edge is clear after costs.",
        sizing_pct=Decimal("0.03"),
        stake_usd=Decimal("15"),
    )
    assert decision.requested_tx_type == "BUY"


def test_decision_output_requires_position_id_for_exit() -> None:
    with pytest.raises(ValidationError):
        DecisionOutput(
            decision_id="dec-1",
            decision_group_id="grp-1",
            market_id="btc-2026-03-09-58k",
            as_of_ts_utc=datetime(2026, 3, 9, 14, 0, tzinfo=UTC),
            position_state="OPEN",
            action_type="EXIT",
            target_side="YES",
            reasoning="Edge collapsed.",
        )




def test_decision_output_autosets_requested_tx_type_for_exit() -> None:
    decision = DecisionOutput(
        decision_id="dec-1",
        decision_group_id="grp-1",
        market_id="btc-2026-03-09-58k",
        as_of_ts_utc=datetime(2026, 3, 9, 14, 0, tzinfo=UTC),
        position_state="OPEN",
        action_type="EXIT",
        target_side="YES",
        target_position_id="pos-1",
        reasoning="Edge collapsed.",
    )
    assert decision.requested_tx_type == "SELL"

def test_portfolio_state_matches_open_positions_count_and_cooldown() -> None:
    portfolio = PortfolioState(
        as_of_ts_utc=datetime(2026, 3, 9, 14, 0, tzinfo=UTC),
        bankroll_usd=Decimal("500"),
        cash_usd=Decimal("458"),
        total_invested_usd=Decimal("42"),
        open_positions=[build_open_position()],
        cooldown_until_utc=datetime(2026, 3, 9, 14, 5, tzinfo=UTC),
        cooldown_reason_pass_code="EDGE_TOO_SMALL",
    )

    assert portfolio.open_positions_count == 1
    assert portfolio.in_cooldown is True


def test_portfolio_state_rejects_duplicate_thesis() -> None:
    pos = build_open_position()
    with pytest.raises(ValidationError):
        PortfolioState(
            as_of_ts_utc=datetime(2026, 3, 9, 14, 0, tzinfo=UTC),
            bankroll_usd=Decimal("500"),
            cash_usd=Decimal("416"),
            total_invested_usd=Decimal("84"),
            open_positions=[pos, pos.model_copy(update={"position_id": "pos-2"})],
        )


def test_fill_event_requires_requested_price_for_buy() -> None:
    with pytest.raises(ValidationError):
        FillEvent(
            event_id="fill-1",
            market_id="btc-2026-03-09-58k",
            decision_group_id="grp-1",
            tx_type="BUY",
            amount_type="USD",
            requested_amount=Decimal("25"),
            filled_price=Decimal("0.43"),
            filled_shares=Decimal("58.1395"),
            side="YES",
            occurred_at_utc=datetime(2026, 3, 9, 14, 1, tzinfo=UTC),
        )


def test_fill_event_autocomputes_slippage_and_notional() -> None:
    fill = FillEvent(
        event_id="fill-1",
        market_id="btc-2026-03-09-58k",
        decision_group_id="grp-1",
        tx_type="BUY",
        amount_type="USD",
        requested_amount=Decimal("25"),
        requested_price=Decimal("0.41"),
        filled_price=Decimal("0.43"),
        filled_shares=Decimal("58.1395"),
        side="YES",
        requested_at_utc=datetime(2026, 3, 9, 14, 0, tzinfo=UTC),
        occurred_at_utc=datetime(2026, 3, 9, 14, 1, tzinfo=UTC),
    )

    assert fill.slippage_abs == Decimal("0.02")
    assert fill.filled_notional_usd == Decimal("24.999985")


def test_integrity_snapshot_requires_pass_code_when_invalid() -> None:
    with pytest.raises(ValidationError):
        DataIntegritySnapshot(
            as_of_ts_utc=datetime(2026, 3, 9, 14, 0, tzinfo=UTC),
            poly_staleness_s=35,
            ref_staleness_s=10,
            data_latency_ms=120,
            integrity_ok=False,
            core_features_valid=False,
        )


def test_contract_serialization_is_json_ready() -> None:
    payload = build_market_context().to_json_dict()
    assert payload["definition"]["market_id"] == "btc-2026-03-09-58k"
    assert payload["snapshot"]["executable_overround"] == "0.04"
