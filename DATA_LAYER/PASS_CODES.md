# NoTrade — PASS Codes (Stable IDs) — SSOT

This file defines **stable PASS codes** used across the entire system:
- Data Layer (DAC gates)
- Decision/Policy layer (risk/exposure/timeframe)
- Memory / Ledger (`policy.pass_code`)

**Rule:** a PASS code name should never be renamed once it appears in logs.

**Usage rule:** if multiple reasons exist, pick the **dominant** PASS code and keep the rest in `action.reasoning`.

---

## 1) Market definition / parsing (Chapter 2)
- `INVALID_MARKET_METADATA` — required fields missing (market_id, asset, strike, time, rule_type, etc.)
- `UNSUPPORTED_MARKET_TYPE` — market not supported in current MVP scope
- `MARKET_DEFINITION_AMBIGUOUS` — contract rules unclear (boundary, timezone, metric, etc.)

## 2) Freshness (Chapter 3)
- `STALE_POLYMARKET_CONTEXT` — quotes/spread/liquidity too old for execution context
- `MISSING_REFERENCE_PRICE` — spot reference feed missing or stale

## 3) Integrity (Chapter 3)
- `MISSING_CANONICAL_CANDLE` — required Binance candle at snapshot time missing/unverifiable
- `DATA_INTEGRITY_FAIL` — corruption / inconsistent inputs detected

## 4) Data conflict / gaps (Chapter 3)
- `DATA_GAP_TOO_LARGE` — too many consecutive missing candles in active execution window
- `DATA_CONFLICT_DETECTED` — cross-venue mismatch or anomaly implies CONFLICT → PASS

## 5) Liquidity / execution realism (Chapter 1 + 3)
- `INSUFFICIENT_LIQUIDITY` — spread/depth too poor; execution kills edge
- `SLIPPAGE_UNKNOWN` — cannot estimate slippage conservatively

## 6) Value / edge (Chapter 1 + 3)
- `EDGE_TOO_SMALL` — `edge_net < policy.EDGE_NET_THRESHOLD`

## 7) Risk / exposure (Chapter 1)
- `RISK_REWARD_UNFAVORABLE` — edge exists, but risk/reward unacceptable (risk dominates edge)
- `EXPOSURE_LIMIT_REACHED` — violates exposure caps (e.g., `policy.MAX_POSITION_PCT`)
- `CORRELATED_EXPOSURE_LIMIT_REACHED` — violates correlated caps (BTC-direction / total correlated exposure)
- `DRAWDOWN_LIMIT_REACHED` — weekly/monthly drawdown guard tripped

## 8) Timeframe (Chapter 1)
- `TIMEFRAME_TOO_SHORT` — too little time left; default PASS behavior applies

## 9) Infrastructure (Chapter 3)
- `RATE_LIMITED` — source rate-limited (e.g., HTTP 429)
- `SOURCE_UNAVAILABLE` — source outage / unreachable