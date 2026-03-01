# NoTrade — PASS Codes (Stable IDs)

This file defines **stable PASS codes** used across documents.

Rule: a PASS code name should never be renamed once it appears in logs.

---

## 1) Market definition / parsing (Chapter 2 + 3)
- `INVALID_MARKET_METADATA` — required fields missing (market_id, asset, strike, time, rule_type, etc.)
- `UNSUPPORTED_MARKET_TYPE` — the market is not supported in current MVP scope
- `MARKET_DEFINITION_AMBIGUOUS` — the contract rules are unclear (boundary, timezone, metric, etc.)

## 2) Freshness (Chapter 3)
- `STALE_POLYMARKET_CONTEXT` — quotes/spread/liquidity are too old
- `MISSING_REFERENCE_PRICE` — spot reference feed missing or stale

## 3) Integrity (Chapter 3)
- `MISSING_CANONICAL_CANDLE` — required Binance candle at snapshot time is missing/unverifiable
- `DATA_INTEGRITY_FAIL` — conflict/corruption detected in required inputs

## 4) Liquidity / execution (Chapter 1 + 3)
- `INSUFFICIENT_LIQUIDITY` — spread/depth too poor to execute without killing edge
- `SLIPPAGE_UNKNOWN` — cannot estimate slippage conservatively

## 5) Value / edge (Chapter 1 + 3)
- `EDGE_TOO_SMALL` — `edge_net < EDGE_NET_THRESHOLD`

## 6) Timeframe (Chapter 1)
- `TIMEFRAME_TOO_SHORT` — too little time left; default PASS behavior applies

## 7) Infrastructure (Chapter 3)
- `RATE_LIMITED` — source rate-limited (e.g., HTTP 429)
- `SOURCE_UNAVAILABLE` — source outage or unreachable
