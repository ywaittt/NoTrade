# Trade Ledger Schema (v1.2, MVP)

**Format:** JSON Lines (JSONL)  
**File:** `MEMORY/ledger/trade_ledger.jsonl`  
**Rule:** append-only; do not rewrite history during the week.

## 1) Why this exists
The ledger is NoTrade’s **memory**:
- forces decision-time reasoning (audit-friendly)
- enables weekly review: mistakes, good calls, patterns
- supports active management (HOLD / SELL / MERGE / CONVERT) without losing context

This is **not** automatic training. Learning happens via weekly review + manual improvements.

---

## 2) Decision cadence (what gets logged)
### 2.1 Periodic decision-time evaluations (baseline)
Default cadence: every `probability_model.PREDICTION_CADENCE_MIN` minutes (MVP default = 30).

At each periodic evaluation:
- compute `raw_prob_yes`
- calibrate into `model_prob_yes`
- read `market_prob_yes` (best executable YES entry price, ask-like when book data exists)
- compute `edge_net = model_prob_yes - market_prob_yes - execution_costs`
- decide: `PASS | ENTER | HOLD | EXIT`
- log reasoning immediately

### 2.2 Reconsideration (event-driven)
Create a **new DECISION entry** when:
- `edge_net` crosses below or above threshold
- market probability jumps by `data_layer.PROB_JUMP_ALERT` within `data_layer.PROB_JUMP_WINDOW_S`
- integrity gates fail then recover (staleness / latency)
- major context shift (news shock, vol regime shift)

Link reconsiderations using `decision_group_id`.

---

## 3) Entry types
- `DECISION` (the main event)
- `WEEK_SUMMARY` (weekly freeze + summary + report pointer)

---

## 4) Core definitions
### 4.1 Probability fields
For DAILY HIT PRICE:
- `probs.market_prob_yes` = executable YES entry price from the current market snapshot;
- `probs.model_prob_yes` = the **calibrated** probability actually used by policy / action logic;
- `logic_output.raw_prob_yes` = the pre-calibration raw model score.

**Fees:** none for DAILY HIT PRICE (MVP).  
**Slippage:** log an estimate in cents for diagnostics.

### 4.2 Actions (Polymarket vocabulary)
A `DECISION` can include one or more transactions:
- `BUY` (enter / add)
- `SELL` (exit / reduce)
- `MERGE` (burn YES + NO into cash equivalent)
- `CONVERT` (shift exposure across legs / branches)
- `HEDGE` (explicit risk-shaping action)

### 4.3 Decision Engine semantics
For policy-layer clarity in Chapter 7:
- `PASS` = no fresh position is opened;
- `ENTER` = the engine wants exposure opened or increased;
- `HOLD` = an existing position remains valid and no full exit is justified;
- `EXIT` = full flatten of the active thesis;
- `HEDGE` remains allowed in the ledger for future portfolio-shaping workflows, but it is outside the core Chapter 7 verdict set;
- partial `SELL` remains a transaction-level operation and should not be confused with `EXIT`.

---

## 5) Integrity gates (data hygiene)
Always log integrity metadata so you can explain “why PASS”.

Probability-layer trust fields should also be logged so later Chapters can distinguish:
- bad market setup
- bad data integrity
- bad calibration / uncertainty

Recommended fields:
- polymarket staleness seconds
- reference staleness seconds
- data latency ms
- integrity_ok boolean
- invalid cooldown window

---

## 6) DECISION schema (v1.2)
**PASS codes rule:** `policy.pass_code` MUST be one stable ID from `DATA_LAYER/PASS_CODES.md`.
If multiple reasons exist, pick the dominant one and write the rest in `action.reasoning`.

### 6.1 DECISION JSON shape
```json
{
  "entry_type": "DECISION",
  "decision_id": "uuid-or-nanoid",
  "decision_group_id": "uuid-or-nanoid",
  "week_id": "YYYY-Www",
  "as_of_ts_utc": "ISO-8601",
  "as_of_ts_local": "ISO-8601",

  "market": {
    "definition": {
      "market_id": "polymarket_id_or_slug",
      "market_name": "string",
      "market_type": "DAILY_HIT_PRICE",
      "asset": "BTC|ETH",
      "condition": "ABOVE|BELOW|RANGE|TOUCH|null",
      "resolution_tz": "America/New_York",
      "resolution_local_time": "12:00",
      "event_ts_utc": "ISO-8601",
      "strike_price": null,
      "ref_source": "BINANCE_SPOT",
      "ref_pair": "BTCUSDT|ETHUSDT",
      "candle_interval": "1m",
      "price_metric": "CLOSE"
    },
    "snapshot": {
      "as_of_ts_utc": "ISO-8601",
      "market_prob_yes": null,
      "market_prob_no": null,
      "best_yes_bid": null,
      "best_yes_ask": null,
      "best_no_bid": null,
      "best_no_ask": null,
      "quoted_spread_pct": null,
      "yes_spread_abs": null,
      "no_spread_abs": null,
      "midpoint_prob_yes": null,
      "midpoint_prob_no": null,
      "executable_overround": null,
      "yes_depth_usd": null,
      "no_depth_usd": null,
      "time_to_expiry_min": null
    }
  },

  "data_integrity": {
    "poly_staleness_s": 0,
    "ref_staleness_s": 0,
    "data_latency_ms": 0,
    "integrity_ok": true,
    "integrity_notes": null,
    "invalid_cooldown_min": 10
  },

  "features": {
    "tf_macro": ["1h", "4h"],
    "tf_micro": ["1m", "5m"],

    "core_features_v1": {
      "trend_ema_state_1h": null,
      "trend_ema_state_4h": null,
      "rsi_5m": null,
      "rsi_1h": null,
      "macd_hist_1h": null,
      "realized_vol_1h": null,
      "atr_1h": null,
      "distance_to_target_pct": null,
      "distance_to_target_atr": null,
      "volume_ratio_1h": null,
      "obv_slope_1h": null,
      "time_to_expiry_min": null
    },

    "context_features_v2": {
      "bollinger_position_5m": null,
      "funding_rate_z": null,
      "open_interest_delta": null,
      "order_book_imbalance_top10": null,
      "spread_pct": null,
      "depth_to_size_ratio": null,
      "vol_regime_ratio": null,
      "news_shock_flag": null
    },

    "raw_window_ref": {
      "ohlcv_tf": "1m",
      "lookback_minutes": 240,
      "snapshot_hash": "sha256:..."
    }
  },

  "probs": {
    "market_prob_yes": null,
    "model_prob_yes": null,
    "edge_net": null,
    "slippage_est_cents": null,
    "counterfactual": null
  },

  "logic_output": {
    "raw_prob_yes": null,
    "confidence_band_low": null,
    "confidence_band_high": null,
    "uncertainty_score": "LOW|MEDIUM|HIGH|CRITICAL|null",
    "calibration_status": "FRESH|AGING|STALE|INVALID|null",
    "calibration_window_id": null,
    "model_family": null,
    "model_version": null,
    "calibration_method": null
  },

  "policy": {
    "edge_threshold": 0.03,
    "max_position_pct": 0.06,

    "bankroll_usd": null,
    "total_invested_usd": null,
    "open_positions_count": null,

    "risk_ok": true,
    "pass": false,
    "pass_code": null,

    "sizing_pct": null,
    "stake_usd": null,

    "rule_violation": {"flag": false, "notes": null}
  },

  "action": {
    "action_type": "PASS|ENTER|HOLD|EXIT",
    "target_side": "YES|NO|null",
    "target_position_id": "string|null",
    "requested_tx_type": "BUY|SELL|null",
    "reasoning": "string (1–4 sentences, decision-time)",
    "reasoning_ts_utc": "ISO-8601",
    "transactions": [
      {
        "tx_type": "BUY|SELL|MERGE|CONVERT|HEDGE",
        "side": "YES|NO|null",
        "amount_type": "USD|SHARES|null",
        "requested_amount": null,
        "requested_price": null,
        "filled_price": null,
        "filled_shares": null,
        "filled_notional_usd": null,
        "slippage_abs": null,
        "notes": null
      }
    ]
  },

  "position_state": {
    "has_yes": null,
    "has_no": null,
    "yes_shares": null,
    "no_shares": null
  },

  "outcome": {
    "resolved": false,
    "resolution": "YES|NO|null",
    "pnl_usd": null,
    "pnl_pct": null,
    "max_adverse_excursion": {"pct": null, "ts_utc": null},
    "max_favorable_excursion": {"pct": null, "ts_utc": null}
  },

  "post_mortem": {
    "required": false,
    "ai_draft": null,
    "tags_fixed": [],
    "tags_freeform": [],
    "notes": null,
    "reviewed_ts_utc": null
  }
}
```

### 6.2 Structural rules
- `features.core_features_v1` contains the minimum deployable feature set from Chapter 5.
- `features.context_features_v2` contains optional enrichments that may be absent without invalidating the entire snapshot.
- `probs.market_prob_yes` remains in `probs`, not in `features`, to preserve model independence and avoid circularity.
- If core v1 features are stale, missing, or contradictory in a critical way, set `policy.pass = true` and use the dominant stable `pass_code`.
- `action.action_type = HOLD` is valid only if `position_state` indicates live exposure already exists.
- `action.target_side` should be populated for `ENTER`, `HOLD`, and `EXIT` so the runtime spine can tie the verdict to a concrete YES/NO thesis.
- `action.target_position_id` should be populated for `HOLD` and `EXIT`.
- `action.requested_tx_type` is a minimal execution intent: `BUY` for `ENTER`, `SELL` for `EXIT`, `null` for `PASS` and `HOLD`.
- `action.action_type = EXIT` should imply full flatten semantics for the relevant thesis, even though the underlying transaction vocabulary still uses `SELL`.

---

## 7) WEEK_SUMMARY schema (week freeze)
A weekly summary is a single entry that “closes” the week and points to the weekly report.

```json
{
  "entry_type": "WEEK_SUMMARY",
  "week_id": "YYYY-Www",
  "closed_ts_local": "ISO-8601",
  "summary": {
    "realized_pnl_usd": 0,
    "ev_total": 0,
    "hit_rate": 0.0,
    "max_drawdown_pct": 0.0,
    "largest_loss_trade_pct": 0.0,
    "top_loss_tags": ["string"]
  },
  "report_ref": "MEMORY/reports/weekly/YYYY-Www.md"
}
```

---

## 8) Post-mortem rules (when required)
Post-mortem is required when:
- LOSS >= 5% (choose a consistent basis: stake or bankroll, but be consistent)
- missed edge (PASS, but trade would have been positive EV)
- any rule violation is flagged

AI drafts it, human finalizes it.

---

## 9) Minimum queries you should support
- Current bankroll: invested vs remaining
- Open positions count + total exposure
- YES and NO on the same branch (merge opportunities)
- Last transaction timestamp (global + per market)
- Time left until close
- Weekly: EV total, realized PnL, hit rate, drawdown, top 5 loss tags

---

## 10) Acceptance tests
If these are painful to answer, the schema is wrong:
1. “Last 20 decisions with `edge_net >= edge_threshold` and outcome LOSS.”
2. “Top 5 tags for LOSS this week.”
3. “List open positions with: asset, yes/no shares, invested_usd, last_tx_ts.”
4. “Show all PASS decisions caused by invalid core v1 feature snapshots.”


## 10) Stage 1 runtime alignment notes
- `market.snapshot.market_prob_yes` / `market_prob_no` are executable entry prices, not midpoint complements.
- `action.target_position_id` should be populated for `HOLD` and `EXIT`.
- `action.requested_tx_type` is a minimal execution intent: `BUY` for `ENTER`, `SELL` for `EXIT`, `null` for `PASS` and `HOLD`.
- Cooldown remains a portfolio guard, not a thesis state.
