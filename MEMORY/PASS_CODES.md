# PASS Codes (lightweight, optional)

PASS codes are helpful but not mandatory. Use them when they add clarity.

## Core PASS codes
- `PASS_NO_EDGE`
  - Meaning: `edge_net < policy.EDGE_NET_THRESHOLD`
- `PASS_RISK_TOO_HIGH`
  - Meaning: `edge_net >= threshold` but risk/reward is unacceptable (risk > edge)
- `PASS_INTEGRITY_FAIL`
  - Meaning: data integrity gates failed (staleness/latency/out-of-window)
- `PASS_TOO_CLOSE_TO_RESOLUTION`
  - Meaning: not enough time left until close; low confidence window
- `PASS_ALREADY_MAX_EXPOSURE`
  - Meaning: exposure cap hit (e.g. `policy.MAX_POSITION_PCT` or correlated exposure caps)

## “Invalid window” behaviour
If integrity fails:
1) retry shortly
2) if still unstable, mark invalid for 5–10 minutes
3) log the PASS with `PASS_INTEGRITY_FAIL` (or leave pass_code null and write it in reasoning)

## Counterfactuals (recommended)
When PASS, add a one-liner:
- “I would ENTER if market_prob_yes <= X OR if integrity_ok becomes true.”