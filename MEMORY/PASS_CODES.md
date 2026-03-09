# PASS Codes (Memory) — Friendly Mapping (NO NEW IDs)

This file is **not** a source of truth.

✅ **Ledger field `policy.pass_code` MUST use stable IDs from:**
- `DATA_LAYER/PASS_CODES.md`

This file only maps legacy/friendly labels (used in prose) to stable IDs.

---

## Friendly → Stable mapping

Legacy prose labels are kept only for translation into stable IDs. Do not write them into runtime payloads.

- `PASS_NO_EDGE`
  - Use: `EDGE_TOO_SMALL`

- `PASS_RISK_TOO_HIGH`
  - Use: `RISK_REWARD_UNFAVORABLE`

- `PASS_TOO_CLOSE_TO_RESOLUTION`
  - Use: `TIMEFRAME_TOO_SHORT`

- `PASS_ALREADY_MAX_EXPOSURE`
  - Use: `EXPOSURE_LIMIT_REACHED`
  - If correlation-related: `CORRELATED_EXPOSURE_LIMIT_REACHED`

- `PASS_INTEGRITY_FAIL`
  - Use the **most specific** one:
    - Polymarket staleness: `STALE_POLYMARKET_CONTEXT`
    - missing/stale reference: `MISSING_REFERENCE_PRICE`
    - missing canonical candle: `MISSING_CANONICAL_CANDLE`
    - candle gaps too large: `DATA_GAP_TOO_LARGE`
    - conflict/anomaly: `DATA_CONFLICT_DETECTED`
    - generic integrity failure: `DATA_INTEGRITY_FAIL`
    - rate limit: `RATE_LIMITED`
    - source down: `SOURCE_UNAVAILABLE`
    - liquidity: `INSUFFICIENT_LIQUIDITY`
    - slippage unknown: `SLIPPAGE_UNKNOWN`

---

## Counterfactuals (recommended)
When PASS, add a one-liner in ledger:
- `probs.counterfactual`: “I would ENTER on target_side = YES/NO if market_prob_yes reaches X or integrity_ok becomes true.”
