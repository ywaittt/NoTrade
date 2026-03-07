# Chapter 5 — Feature Engineering (NoTrade)

**Document:** `FEATURE_ENGINEERING.md`  
**Project:** NoTrade  
**Purpose:** transform raw market and context data into decision-time signals that help NoTrade estimate `P(event)` for a defined market.

This chapter defines:
- a **v1 feature set**: simple, robust, easy to compute, easy to audit
- a **v2 feature set**: richer, broader, more regime-aware
- for each feature:
  - **what it measures**
  - **when it is reliable**
  - **known failure modes**

> Design rule: start with features that are explainable, stable, and aligned with the actual market resolution logic. Add complexity only when it improves calibration, discipline, or net EV.

---

# 1. Core principles

## 1.1 Features are derived, not magical
A feature is a transformation of raw data into a signal that may carry predictive value.

Examples:
- raw data: 1m BTCUSDT candles
- feature: RSI(14) on 5m
- raw data: order book levels
- feature: order book imbalance

## 1.2 Raw is reproducible, features are recomputable
Raw data must remain the source of truth.

Features are allowed to evolve across versions, as long as:
- feature definitions are explicit
- transform versions are tracked
- old decisions remain replayable

## 1.3 v1 favors robustness over cleverness
v1 should prioritize:
- high-quality CEX price data
- simple formulas
- low dependency on fragile feeds
- low risk of leakage or narrative contamination

## 1.4 Market-implied probability is not a core predictive feature in v1
`P(market)` is used to compute edge, not to become the model itself.

Rule for v1:
- log `market_prob_yes`
- compare `model_prob_yes` against `market_prob_yes`
- do **not** let the feature set collapse into “predict the market using the market”

This avoids circular logic and preserves model independence.

## 1.5 Features must be timeframe-aware
Signals are valid only if their horizon matches the market’s horizon.

A 4h trend feature may be useful as background context. A 1m scalp signal should not dominate a daily snapshot model.

## 1.6 Features must remain aligned with market rules
Feature usefulness is downstream from market definition.

If the market resolves on a 1m Binance close at a specific timestamp, the feature stack should be built to support that resolution logic. A brilliant feature built on the wrong event definition is still wrong.

## 1.7 Invalid feature snapshots are not “low confidence”, they are decision hazards
A feature snapshot is invalid if the required inputs are stale, contradictory, missing, or mismatched to the decision horizon.

> If core v1 features are unavailable, contradictory, or stale, the feature snapshot is invalid and NoTrade defaults to PASS.

---

# 2. Feature families

NoTrade feature families:
1. Trend
2. Momentum
3. Volatility
4. Participation / Volume
5. Target-distance / Event geometry
6. Execution / Microstructure
7. Market-context / Regime
8. Event / News flags

---

# 3. v1 Feature Set (MVP: simple, auditable, strong baseline)

## 3.1 v1 philosophy
v1 should answer one question:

> “Given the current trend, momentum, volatility, participation, and distance to target, is this event realistically underpriced or overpriced?”

v1 deliberately avoids:
- social sentiment
- noisy on-chain proxies
- fragile cross-source composites
- exotic microstructure metrics

## 3.2 v1 architecture
v1 is split into two logical layers:
- **core_features_v1**: features that directly support the first deployable model
- **context_features_v2**: optional enrichments that may later improve regime-awareness and execution realism

For MVP, only `core_features_v1` should be required for decision validity.

## 3.3 v1 feature catalog

| Feature ID | Inputs | What it measures | When it is reliable | Known failure modes |
|---|---|---|---|---|
| `trend_ema_state_1h` | 1h candles, EMA fast/slow | Direction of the short intraday trend | Best in liquid, non-chaotic sessions when trend is persistent | Whipsaws in chop; delayed after violent reversals; weak near major news |
| `trend_ema_state_4h` | 4h candles, EMA fast/slow | Higher-timeframe directional bias | Best as macro filter, not as precise entry trigger | Too slow for late-session reversals; can stay bullish while local setup already broke |
| `rsi_5m` | 5m candles | Short-term momentum / stretch | Useful in stable intraday conditions and pullback detection | Can stay overbought/oversold during strong trends; noisy during event spikes |
| `rsi_1h` | 1h candles | Broader momentum state | Useful as context for trend continuation or exhaustion | Lags turning points; can flatten into irrelevance in sideways markets |
| `macd_hist_1h` | 1h candles | Momentum acceleration or deceleration | Reliable when trend exists and market structure is not hyper-noisy | Late on reversals; weak in range-bound chop |
| `realized_vol_1h` | 1m/5m/1h returns | Actual recent movement intensity | Useful for deciding whether target distance is realistic | Can overreact after one shock candle; volatility mean-reverts unpredictably |
| `atr_1h` | 1h candles | Typical recent price travel range | Strong for normalizing distance to target | Underestimates jump risk before news; overstates after abnormal spike |
| `distance_to_target_pct` | spot, strike | Raw percentage distance from current price to target | Useful as an intuitive feasibility anchor and for dashboards | Misleading without volatility normalization; sign handling must match market condition |
| `distance_to_target_atr` | spot, strike, ATR | How far the market is from target, scaled by current movement regime | Very important for hit-price markets, especially away from expiry | Becomes misleading when ATR is distorted; sign logic must match ABOVE/BELOW market |
| `bollinger_position_5m` | 5m candles, Bollinger bands | Where price sits inside local distribution | Useful for stretch/reversion context in calm-to-moderate regimes | Breaks during trend expansions; bands widen too late |
| `volume_ratio_1h` | 1h volume vs rolling median | Whether current participation is above normal | Helpful when confirming real moves vs weak drift | Distorted by exchange anomalies, rollover effects, session changes |
| `obv_slope_1h` | price + volume | Whether volume supports directional move | Useful as confirmation, not standalone | Divergences can persist for a long time; poor during thin or mechanical flow |
| `time_to_expiry_min` | market metadata | Remaining time until resolution | Crucial for event feasibility and feature weighting | None conceptually, but dangerous if timezone handling is wrong |

## 3.4 v1 scoring logic
v1 does **not** need a fancy model at first. It can begin as a disciplined composite signal.

Example structure:

### Trend block
- `trend_ema_state_1h`
- `trend_ema_state_4h`

### Momentum block
- `rsi_5m`
- `rsi_1h`
- `macd_hist_1h`

### Volatility / feasibility block
- `realized_vol_1h`
- `atr_1h`
- `distance_to_target_pct`
- `distance_to_target_atr`
- `time_to_expiry_min`

### Participation block
- `volume_ratio_1h`
- `obv_slope_1h`

## 3.5 Minimum deployable v1 subset
For MVP, the most important v1 features are:
1. `distance_to_target_atr`
2. `time_to_expiry_min`
3. `trend_ema_state_1h`
4. `trend_ema_state_4h`
5. `realized_vol_1h`
6. `volume_ratio_1h`

If these six are weak, contradictory, or invalid, PASS should become much more likely.

---

# 4. v2 Feature Set (richer, more inclusive, more regime-aware)

## 4.1 v2 philosophy
v2 expands from “basic market structure” to “market structure + execution + regime + event awareness”.

v2 should only be adopted when:
- data integrity is good enough
- feature definitions are stable
- ledger reviews show clear blind spots in v1
- added complexity improves calibration, not just storytelling

## 4.2 v2 role
v2 should improve four things:
- execution realism
- crowding awareness
- regime awareness
- event awareness

## 4.3 v2 feature catalog

| Feature ID | Inputs | What it measures | When it is reliable | Known failure modes |
|---|---|---|---|---|
| `order_book_imbalance_top10` | L2 order book | Near-term pressure from bids vs asks | Best when book is fresh and market is liquid | Spoofing; stale snapshots; weak predictive power in chaotic bursts |
| `spread_pct` | best bid/ask | Execution friction / quality of entry | Always important for real execution | Can look fine just before liquidity disappears |
| `depth_to_size_ratio` | L2 book + intended stake | Whether the book can absorb planned size | Reliable in stable books with frequent updates | Fast-moving books invalidate static depth assumptions |
| `microprice_deviation` | order book | Short-horizon directional pressure around the mid | Useful in liquid intraday markets | Very noisy; degrades fast outside execution windows |
| `funding_rate_z` | perp funding history | Whether positioning is crowded one way | Useful in leverage-driven regimes | Funding can stay extreme for a long time without reversal |
| `open_interest_delta` | OI data | Whether participation is entering or leaving | Useful when paired with price and funding | OI alone is ambiguous; liquidations can invert interpretation |
| `basis_spot_perp` | spot + perp prices | Stress / leverage premium or discount | Helpful during macro and liquidation phases | Exchange differences and timestamp mismatch |
| `vol_regime_ratio` | short vol / long vol | Whether current volatility regime is expanding or compressing | Strong for deciding which features deserve weight | Can flip abruptly after single shock events |
| `prob_spot_divergence` | Polymarket prob + spot move | Whether market pricing is moving too fast or too slow vs spot reality | Useful as decision-context feature, not pure prediction feature | Circularity risk; can overfit market micro-noise |
| `cross_asset_leadlag_btc_eth` | BTC + ETH returns | Whether one asset is leading the other | Useful when ETH markets follow BTC structure | Relationship weakens during asset-specific news |
| `wickiness_score_5m` | candle structure | Whether moves are accepted or being rejected | Useful in breakout vs rejection environments | Noisy during low liquidity or sudden news |
| `news_shock_flag` | curated news feed | Whether price action is likely being dominated by event shock | Useful as override or caution flag | Missed news, false positives, latency |
| `macro_event_proximity` | event calendar | Whether a major known catalyst is near the resolution window | Useful for volatility expectations | Scheduled event may end up irrelevant |
| `session_context` | time-of-day / market session | Whether the current session tends to support or weaken movement | Useful for intraday behavior patterns | Can create fake seasonality if overused |

## 4.4 Best first upgrades
Not all v2 features deserve equal priority.

Best first upgrades:
1. `order_book_imbalance_top10`
2. `spread_pct`
3. `depth_to_size_ratio`
4. `funding_rate_z`
5. `open_interest_delta`
6. `vol_regime_ratio`
7. `news_shock_flag`

These seven give the biggest jump in realism:
- execution realism
- crowding awareness
- regime awareness
- event awareness

---

# 5. Reliability rules across all features

## 5.1 General reliability test
A feature is usable only if:
- required raw inputs are present
- timestamps are aligned
- source freshness is acceptable
- no integrity conflict is active
- the feature horizon matches the market horizon

## 5.2 Feature invalidation rules
A feature snapshot should be marked invalid if:
- required candle(s) are missing
- source is stale
- source conflict is unresolved
- the decision is too close to resolution for the feature to matter
- formula output is numerically unstable or undefined

## 5.3 Degrade, then PASS
Some feature groups may be disabled without killing the full decision:
- v2 microstructure can be disabled first
- v2 event/context can be disabled next

But if core v1 features are missing or contradictory in a critical way, NoTrade should PASS.

---

# 6. Known cross-feature failure modes
These are not individual feature failures, but system-level traps.

## 6.1 Timeframe mismatch
A strong 1m signal fights a strong 4h move and the system overweights the wrong one.

## 6.2 Volatility regime shift
Indicators calibrated in normal volatility become weak or misleading during expansion.

## 6.3 News shock override
Technical structure becomes secondary because a headline dominates flow.

## 6.4 Late-expiry illusion
A setup looks attractive statistically, but there is simply not enough time left for the move.

## 6.5 Execution blindness
A signal is correct in theory, but spread, depth, and slippage destroy the edge.

## 6.6 Circularity
The model “learns the market price” instead of the event probability.

---

# 7. Feature versioning policy

## 7.1 v1
Stable, simple, auditable baseline.

## 7.2 v2
Expanded feature space with execution, regime, and event context.

## 7.3 Rule
Do not rename feature IDs casually.

If a formula changes materially:
- keep the old feature archived
- create a new versioned feature name if needed
- record `transform_version` in decision logs

---

# 8. Minimum recommended MVP set
If we need the absolute leanest deployable set, use this:
- `trend_ema_state_1h`
- `trend_ema_state_4h`
- `rsi_5m`
- `macd_hist_1h`
- `realized_vol_1h`
- `atr_1h`
- `distance_to_target_pct`
- `distance_to_target_atr`
- `volume_ratio_1h`
- `time_to_expiry_min`

This is enough to build a first disciplined probability engine without drowning in complexity.

---

# 9. Final design rule
> A feature is good only if it improves decisions under real-world constraints.  
> If it adds noise, excuses, or fragile complexity, it does not belong in NoTrade.
