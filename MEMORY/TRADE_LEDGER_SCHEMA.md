# Trade Ledger Schema (v1.0, MVP)

**Format:** JSON Lines (JSONL)  
**File:** `MEMORY/ledger/trade_ledger.jsonl`  
**Rule:** append-only; do not rewrite history during the week.

## 1) Why this exists
The ledger is NoTrade’s **memory**:
- forces decision-time reasoning (audit-friendly)
- enables weekly review: mistakes, good calls, patterns
- supports active management (SELL/MERGE/CONVERT) without losing context

This is **not** automatic training. Learning happens via weekly review + manual improvements.

---

## 2) Decision cadence (what gets logged)
### 2.1 Scheduled decisions (baseline)
Every 8 hours (local): e.g. 08:00 / 16:00 / 24:00.

At each scheduled decision:
- compute `model_prob_yes`
- read `market_prob_yes` (Polymarket YES price)
- compute `edge_net = model_prob_yes - market_prob_yes`
- decide: `PASS | ENTER | EXIT | HEDGE`
- log reasoning immediately

### 2.2 Reconsideration (event-driven)
Create a **new DECISION entry** when:
- `edge_net` collapses below threshold
- market probability jumps by `data_layer.PROB_JUMP_ALERT` within `data_layer.PROB_JUMP_WINDOW_S`
- integrity gates fail then recover (staleness/latency)
- major context shift (news shock, vol regime shift)

Link reconsiderations using `decision_group_id`.

---

## 3) Entry types
- `DECISION` (the main event)
- `WEEK_SUMMARY` (weekly freeze + summary + report pointer)

---

## 4) Core definitions
### 4.1 Market probability
For DAILY HIT PRICE: `market_prob_yes` = Polymarket YES price.

**Fees:** none for DAILY HIT PRICE (MVP).  
**Slippage:** log an estimate in cents (usually 1–2c) for diagnostics.

### 4.2 Actions (Polymarket vocabulary)
A `DECISION` can include one or more transactions:
- `BUY`  (enter / add)
- `SELL` (exit / reduce)
- `MERGE` (burn YES+NO into USDC/USDT equivalent)
- `CONVERT` (shift exposure across legs/branches)
- `HEDGE` (explicit “risk-shaping” action)

---

## 5) Integrity gates (data hygiene)
Always log integrity metadata so you can explain “why PASS”.
Recommended fields:
- staleness seconds (polymarket + reference)
- data_latency_ms
- integrity_ok boolean
- invalid cooldown window (5–10 min)

---

## 6) DECISION schema (v1.0)

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
    "market_id": "polymarket_id_or_slug",
    "market_name": "string",
    "market_type": "DAILY_HIT_PRICE",
    "asset": "BTC|ETH",
    "side": "YES|NO|null",

    "resolution_tz": "America/New_York",
    "resolution_local_time": "12:00",
    "ref_source": "BINANCE_SPOT",
    "ref_pair": "BTCUSDT|ETHUSDT",
    "candle_interval": "1m",
    "price_metric": "CLOSE"
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

    "rsi": null,
    "macd": {"line": null, "signal": null, "hist": null},
    "trend": {"ema_fast": null, "ema_slow": null, "direction": null},

    "realized_vol": null,
    "funding_rate": null,
    "open_interest": null,

    "bollinger": {"mid": null, "upper": null, "lower": null},
    "volume": null,
    "obv": null,
    "atr": null,
    "adx": null,

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
    "action_type": "PASS|ENTER|EXIT|HEDGE",
    "reasoning": "string (1–4 sentences, decision-time)",
    "reasoning_ts_utc": "ISO-8601",
    "transactions": [
      {
        "tx_type": "BUY|SELL|MERGE|CONVERT|HEDGE",
        "side": "YES|NO|null",
        "amount_type": "USD|SHARES|null",
        "amount": null,
        "fill_price": null,
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
- LOSS >= 5% (choose consistent basis: stake or bankroll, but be consistent)
- “missed edge” (PASS, but trade would have been positive EV)
- any rule violation is flagged

AI drafts it, human finalizes it.

---

## 9) Minimum queries you should support

- Current bankroll: invested vs remaining
- Open positions count + total exposure
- YES and NO on the same branch (merge opportunities)
- Last transaction timestamp (global + per market)
- Time left until close=
- Weekly: EV total, realized PnL, hit rate, drawdown, top 5 loss tags

---

## 10) Acceptance tests

If these are painful to answer, the schema is wrong:

1. “Last 20 decisions with edge_net >= edge_threshold and outcome LOSS.”
2. “Top 5 tags for LOSS this week.”
3. “List open positions with: (asset, yes/no shares, invested_usd, last_tx_ts).”

---

### `MEMORY/WEEKLY_CYCLE.md`
# Weekly Cycle (Freeze + Summary + Reset)

This defines the “Week X locks, Week X+1 starts fresh” workflow.

## 1) During the week
- Append DECISION entries as they happen.
- Update outcome fields when markets resolve.
- Draft post-mortems after 19:00 local for:
  - LOSS + learning
  - missed-edge
  - rule violations

## 2) Daily cut line (after 19:00 local)
“Draw the line”:
- update outcomes/PnL where resolved
- generate AI draft post-mortems
- mark entries for review where needed

## 3) Weekend freeze (Week close)
On weekend (recommended Sunday after 19:00 local):
1) Generate weekly report `MEMORY/reports/weekly/YYYY-Www.md`
2) Append a single `WEEK_SUMMARY` entry to the ledger pointing to that report
3) Start a new weekly report file for Week+1 (blank template)

## 4) What must go into the weekly report
- realized PnL
- EV total (if tracked)
- hit rate
- max drawdown
- biggest loss (pct)
- top 5 loss tags
- 3 “fixes” for next week (rules/features/process)

## 5) Reset policy
Ledger is **one big file**, never reset.
Reports are per-week, and the “current report” resets when week closes.

---