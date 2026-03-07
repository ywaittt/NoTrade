# Ledger (JSONL)

Create the file:
- `trade_ledger.jsonl`

Rules:
- append-only (one JSON object per line)
- do not edit old lines during the week
- fill outcome / post-mortem fields later by appending a *new decision* or by updating the same entry only if you truly need it (your workflow allows edits, but keep it minimal)

Recommended practice:
- periodic decision-time evaluations every `probability_model.PREDICTION_CADENCE_MIN` minutes (default: 30)
- reconsiderations are new entries linked by `decision_group_id`