from decimal import Decimal
from datetime import datetime, timezone, timedelta

from notrade.contracts.market_definition import MarketDefinition
from notrade.contracts.market_snapshot import MarketSnapshot
from notrade.contracts.market_context import MarketContext
from notrade.contracts.probability_snapshot import ProbabilitySnapshot
from notrade.contracts.portfolio_state import PortfolioState
from notrade.contracts.decision_output import DecisionOutput

as_of_ts = datetime(2026, 3, 10, 13, 0, tzinfo=timezone.utc)
event_ts = as_of_ts + timedelta(minutes=180)

market_def = MarketDefinition(
    market_id="btc-mar10-noon-above-105k",
    market_name="BTC above 105k at noon ET",
    market_type="DAILY_HIT_PRICE",
    asset="BTC",
    rule_type="SNAPSHOT_CLOSE_ABOVE",
    event_ts_utc=event_ts,
    resolution_tz="America/New_York",
    resolution_local_time="12:00",
    strike_price=Decimal("105000"),
    ref_source="BINANCE_SPOT",
    ref_pair="BTCUSDT",
    candle_interval="1m",
    price_metric="CLOSE",
)

market_snapshot = MarketSnapshot(
    as_of_ts_utc=as_of_ts,
    market_prob_yes=Decimal("0.47"),
    market_prob_no=Decimal("0.55"),
    best_yes_bid=Decimal("0.46"),
    best_yes_ask=Decimal("0.47"),
    best_no_bid=Decimal("0.54"),
    best_no_ask=Decimal("0.55"),
    yes_depth_usd=Decimal("1200"),
    no_depth_usd=Decimal("1400"),
    time_to_expiry_min=180,
)

market_context = MarketContext(
    definition=market_def,
    snapshot=market_snapshot,
)

prob_snapshot = ProbabilitySnapshot(
    market_id="btc-mar10-noon-above-105k",
    as_of_ts_utc=as_of_ts,
    raw_prob_yes=Decimal("0.53"),
    model_prob_yes=Decimal("0.54"),
    market_prob_yes=Decimal("0.47"),
    edge_net=Decimal("0.06"),
    confidence_band_low=Decimal("0.51"),
    confidence_band_high=Decimal("0.57"),
    uncertainty_score="LOW",
    calibration_status="FRESH",
    model_family="stub_model",
    model_version="v0.1",
)

portfolio = PortfolioState(
    as_of_ts_utc=as_of_ts,
    bankroll_usd=Decimal("1000"),
    cash_usd=Decimal("1000"),
    total_invested_usd=Decimal("0"),
)

decision = DecisionOutput(
    decision_id="dec-001",
    decision_group_id="grp-001",
    market_id="btc-mar10-noon-above-105k",
    as_of_ts_utc=as_of_ts,
    position_state="FLAT",
    action_type="ENTER",
    target_side="YES",
    reasoning="Model probability is above executable market price by a sufficient net edge.",
    stake_usd=Decimal("30"),
    sizing_pct=Decimal("0.03"),
    risk_ok=True,
)

print("MARKET CONTEXT:")
print(market_context.to_json_str())
print()
print("PROBABILITY SNAPSHOT:")
print(prob_snapshot.to_json_str())
print()
print("PORTFOLIO STATE:")
print(portfolio.to_json_str())
print()
print("DECISION OUTPUT:")
print(decision.to_json_str())