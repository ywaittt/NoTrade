# NoTrade — Chapter 3: Data Layer (Architecture & Integrity)

## 0. Purpose
Data Layer is the system that:
1) ingests raw market/context data,
2) validates and normalizes it,
3) stores it for replay/audit,
4) produces features for the decision engine.

**Prime directive:** if data integrity or freshness is uncertain, NoTrade outputs **PASS**.
---

## MVP Scope (Daily Hit Price)
**Assets:** BTC, ETH  
**Market type:** Polymarket daily hit/close markets with canonical resolution on **Binance 1m candle close at 12:00 ET**.

**Key concept:** each daily market is a distinct entity:
- `market_id`, `asset`, `event_ts_utc`, `strike_price`, `condition`, `resolution_source`

NoTrade must treat "market-of-the-day" as the primary unit of analysis and logging.

---

## 1. Data Universe (Domains)
NoTrade consumes the following data domains:

### 1.1 Market Price Data (CEX)
- OHLCV candles (1m, 5m, 1h, 4h)
- trades/ticks (price, size, side)
- funding rate, open interest (if available)
- basis / cross-venue price reference

### 1.2 Microstructure
- L2 order book snapshots (Top N levels)
- spread, depth, order book imbalance (OBI)
- trade flow / buy-sell imbalance

### 1.3 News Flow
- titles + timestamp + source
- short summaries (daily + intraday alerts)
- deduplication + source credibility tags

### 1.4 Social / Sentiment
- X/Reddit/communities: volume + sentiment score
- analyst sentiment (optional label source)

### 1.5 On-chain / Flows
- exchange inflow/outflow
- whale accumulation proxies
- stablecoin supply / mint-burn signals (optional)
- BTC spot ETF flows (optional)

### 1.6 Polymarket (Execution Context)
- YES/NO prices
- implied probability (YES price after fees assumptions if needed)
- liquidity, spread
- volume + recent prints (if accessible)
- market metadata (expiry/resolution conditions)

---

## 2. Sources of Truth & Fallback Strategy

### 2.1 Canonical Rule for Polymarket Daily "Hit/Close" Markets
For daily "hit price" style markets that resolve using:
> Binance BTC/USDT or ETH/USDT 1-minute candle at 12:00 ET (Noon) with final "Close"

**Canonical Source:** Binance candle close at the specified timestamp and symbol.

**Important:** "never down" is not a design assumption. We define fallbacks anyway, because reliability is a requirement, not a wish.

### 2.2 Source Priority (per domain)

#### Candles / Trades (CEX)
1) **Binance** (primary)
2) **Coinbase / Kraken** (fallback reference only, not for official Polymarket resolution unless rules allow)
3) **Aggregators (e.g., TradingView/Polygon)** as tertiary reference for anomaly detection

**Conflict rule:**  
- If *primary* is available, it wins.  
- If primary missing, use fallback #1 and mark `data_quality = DEGRADED`.  
- If primary and fallback disagree beyond tolerance, mark `data_quality = CONFLICT` → **PASS**.

#### Order Book / Microstructure
1) Binance WebSocket L2 (primary)
2) REST snapshots as fallback (lower fidelity)
3) disable microstructure features if stale

#### News / Social
1) curated RSS feeds + reputable sources (primary)
2) secondary feed (fallback)
3) if missing → continue with reduced confidence (not automatic PASS unless the model requires it)

#### On-chain / Flows
1) preferred provider/node (primary)
2) backup provider (fallback)
3) if missing → features removed, confidence penalty

#### Polymarket Data
1) Polymarket official endpoints (primary)
2) indexer mirror (fallback if available)
3) if missing execution context (prices/book) → **PASS**

---

## 3. Time Resolution & Windows (Temporal Policy)

### 3.1 Granularity Policy
- **Event resolution moment (daily markets):** exact 1m candle at 12:00 ET
- **Decision-making windows:**
  - trend context: 1h / 4h candles (intraday direction, post-news stabilization)
  - execution context: 1m / 5m candles + L2 book

### 3.2 Max Accepted Latency
- Price feed: **1–3 minutes** max (preferred < 30s)
- Order book snapshots: **≤ 10 seconds** max for execution
- Reference venue price: **≤ 30 seconds** max

### 3.3 Minimum Historical Window
- short-horizon decision: **12–36h** (default target: **24h**)
- optionally longer windows for regime detection (not required for MVP)

---

## 4. Data Schemas (Contracts)

### 4.1 OHLCV Candle (CEX)
Key: `(ts_open, symbol, venue, interval)`

| Field        | Type    | Notes |
|--------------|---------|------|
| ts_open      | uint64  | Unix ms UTC |
| symbol       | string  | e.g. BTCUSDT |
| venue        | string  | e.g. BINANCE |
| interval     | string  | 1m, 5m, 1h |
| open         | decimal | |
| high         | decimal | |
| low          | decimal | |
| close        | decimal | |
| volume       | decimal | |
| vwap         | decimal | optional |
| trade_count  | uint32  | optional |
| is_interpolated | bool | default false |
| data_quality | enum    | OK / DEGRADED / CONFLICT / CORRUPT |

---

### 4.2 Order Book Snapshot (L2)
Key: `(ts, symbol, venue)`

| Field      | Type         | Notes |
|------------|--------------|------|
| ts         | uint64       | Unix ms UTC |
| symbol     | string       | |
| venue      | string       | |
| bids       | array[N][2]  | `[price, size]` sorted desc |
| asks       | array[N][2]  | `[price, size]` sorted asc |
| spread     | decimal      | best_ask - best_bid |
| mid        | decimal      | (best_bid + best_ask)/2 |
| imbalance  | float        | (BidVol-AskVol)/(BidVol+AskVol) over top K |
| data_quality | enum      | OK / STALE / CORRUPT |

Recommended defaults:
- `N = 20` levels stored
- imbalance computed on `K = 10`

---

### 4.3 Value Metrics (Basis / Edge)
Key: `(ts, symbol, target_venue)`

| Field         | Type   | Notes |
|---------------|--------|------|
| ts            | uint64 | Unix ms UTC |
| symbol        | string | |
| target_venue  | string | e.g. POLYMARKET |
| reference_venue | string | e.g. BINANCE |
| implied_prob  | float  | from Polymarket YES price |
| ref_prob      | float  | model-estimated probability |
| edge          | float  | `ref_prob - implied_prob` (signed) |
| abs_edge      | float  | `abs(edge)` |
| data_quality  | enum   | OK / DEGRADED / CONFLICT |

---

### 4.4 Edge Policy (Net Edge Only)
NoTrade evaluates **net edge**, not headline edge.

Definitions:
- `implied_prob_raw` = YES price (converted to probability)
- `fees_estimate` = fees + conversion costs (configurable)
- `slippage_estimate` = estimated execution loss based on spread + depth
- `implied_prob_net` = implied probability after costs
- `edge_net` = `model_prob - implied_prob_net`

**Execution rule:** NoTrade may execute only if `edge_net >= 0.03` (3%) and all DAC checks pass.

If `slippage_estimate` cannot be computed reliably → `edge_net = UNKNOWN` → PASS.

---

## 5. Validation & Data Hygiene Rules (Non-Negotiables)

### 5.1 Time Standardization
1. **UTC only:** all timestamps stored as **Unix ms UTC**.
2. **No local timezone** allowed in internal storage.
3. Every record must include `fetch_ts` (ingestion moment).

### 5.2 Candle Integrity
4. **OHLC constraints:** `high >= max(open, close)` and `low <= min(open, close)`; else `CORRUPT`.
5. **Non-negative volume:** `volume >= 0`. Negative volume → drop record.
6. **Duplicate key rule:** `(ts_open, symbol, venue, interval)` is unique. Latest fetch overwrites, but previous version is logged in audit (see provenance).

### 5.3 Missing Candles (1m gaps)
7. If a 1m candle is missing:
   - **Prefer:** re-fetch / backfill from primary source.
   - If still missing and decision depends on continuity:
     - create synthetic candle with `open=high=low=close=prev_close`, `volume=0`
     - set `is_interpolated=true`, `data_quality=DEGRADED`
8. If more than **2 consecutive** 1m candles missing in the active execution window → **PASS** (`DATA_GAP_TOO_LARGE`).

### 5.4 Outliers & Cross-Venue Validation
9. If 1m close-to-close move exceeds threshold:
   - BTC: > **3%**
   - ETH: > **5%**
   - Polymarket implied prob jump: > **10%**
   then cross-check reference venue. If mismatch persists → `CONFLICT` → **PASS**.

### 5.5 Order Book Validity
10. **Stale book:** if `now_ts - ts > 10s` for execution context → mark STALE; microstructure features disabled.
11. **Bid/Ask flip:** if best_bid >= best_ask → CORRUPT snapshot, drop it.
12. **Depth rule:** if top 5 levels missing/zero on either side → execution liquidity check fails.

### 5.6 Denomination / Symbol Normalization
13. Internal symbol IDs are canonical (e.g., `INTERNAL_BTC`, `INTERNAL_ETH`).
14. USDT/USDC are treated as USD with a depeg correction factor when available; if depeg uncertainty is high → `DEGRADED`.

### 5.7 Conflict & Outlier Policy (Dynamic)
Daily hit markets are validated using dynamic checks:
- If Polymarket implied probability jumps > 12% within 1–3 minutes without a comparable spot move → CONFLICT → PASS
- If spot moves sharply but Polymarket stays stale (or vice versa) → DEGRADED; require stricter liquidity + higher edge or PASS

NoTrade never "guesses" under conflict. PASS is the default safe action.

---

## 6. Storage Architecture

### 6.1 Raw Store (Immutable Truth)
Raw store is append-only (or versioned). Includes:
- trades/ticks
- L2 snapshots
- candles from venues
- raw news/social texts (with source + hash)
- on-chain raw events / provider payloads (where possible)
- ingestion metadata: latency, status, response codes

### 6.2 Feature Store (Derived, Recomputable)
Computed features (versioned by transform code):
- momentum: RSI, MACD, Bollinger, volatility
- microstructure: OBI, spread volatility, depth metrics
- flow features: exchange flow delta, whale absorption score
- time features: time to expiry / time to resolution
- sentiment numeric scores (-1 to 1)
- basis/value gap features (Polymarket implied vs model ref prob)

**Rule:** features can be recomputed; raw must be reproducible.

---

## 7. Provenance, Lineage & Audit Trail

Every decision must be replayable.

Key: `decision_id`

| Field            | Type   | Notes |
|-----------------|--------|------|
| decision_id     | UUID   | unique per decision |
| symbol          | string | |
| decision_ts     | uint64 | Unix ms UTC |
| data_version    | string | snapshot ID (raw store state) |
| source_id       | string | e.g. BINANCE_WSS_01 |
| fetch_ts        | uint64 | ingestion time |
| transform_version | string | feature pipeline version |
| model_version   | string | NoTrade model version |
| inputs_hash     | string | SHA256 of feature vector |
| logic_output    | json   | raw outputs: prob_yes, confidence, etc. |
| execution_status| enum   | PASS_* / EXECUTE_* / REJECT_* |
| notes           | string | short human-readable reason |

---

## 8. Freshness, Caching & Rate Limits (Policy)

| Source | Fetch Interval | Max Req/Min | Cache TTL | Notes |
|--------|----------------|-------------|----------|------|
| CEX Prices (Binance) | 1–5s | high | 1s | real-time reference |
| Polymarket L2/Prices | 2–10s | medium | 2s | execution context |
| On-chain flows | ~12s (1 block) | medium | 15s | block-paced |
| DEX liquidity | 30–60s | low | 30s | slow-moving |
| News/Social | 30–120s | low | 60s | window-based |
| Historical backfill | on demand | low | permanent | closed candles static |

---

## 9. DAC (Data Availability Conditions) — MVP Strict
### 9.0 DAC-0 Market sanity:
- must have `event_ts_utc`, `strike_price`, `condition`, `asset`, `resolution_source`
- else PASS: `INVALID_MARKET_METADATA`

### 9.1 DAC-1 Polymarket execution context freshness:
- latest quotes + spread + liquidity updated within 10s
- else PASS: `STALE_POLYMARKET_CONTEXT`

### 9.2 DAC-2 Reference venue freshness (Binance):
- spot reference updated within 30s
- else PASS: `MISSING_REFERENCE_PRICE`

### 9.3 DAC-3 Integrity:
- if `data_quality in {CONFLICT, CORRUPT}` in the last 10 minutes before decision → PASS: `DATA_INTEGRITY_FAIL`

### 9.4 DAC-4 Liquidity:
- `spread_pct = spread / mid` must be <= 2%
- order book depth must support intended size with acceptable slippage
- else PASS: `INSUFFICIENT_LIQUIDITY`

### 9.5 DAC-5 Net edge:
- `edge_net >= 3%`
- else PASS: `EDGE_TOO_SMALL`

---

## 10. Failure Modes (Examples)
1) **Order book feed delayed by 2 minutes**
   - Action: disable microstructure features; if DAC-1 fails → **PASS**
2) **Missing 1m candle at resolution timestamp**
   - Action: attempt backfill; if still missing → **PASS** (`MISSING_CANONICAL_CANDLE`)
3) **Bid/Ask flip**
   - Action: discard snapshot, mark provider unstable; likely **PASS**
4) **Polymarket spread explodes**
   - Action: DAC-2 fails → **PASS**
5) **Primary vs fallback price conflict**
   - Action: mark CONFLICT → **PASS**

---

## 11. Standard PASS Output (JSON)
Example:

{
  "decision": "PASS",
  "reason": "DATA_AVAILABILITY_VIOLATION",
  "missing_fields": ["order_book_depth_top5", "reference_price_binance"],
  "ts_incident": 1740669000000,
  "action": "HALT_EXECUTION_FOR_SYMBOL",
  "data_quality": "DEGRADED"
}