# Chapter 4 — Memory (Ledger + Post-Mortems)

This folder defines NoTrade’s memory system: a **Trade Ledger** (append-only log) + **Post-Mortems** (structured learning notes).
The goal is **weekly review + manual improvement**, not automatic self-training.

## What you get
- A **ledger schema** that logs every decision (PASS included)
- A **weekly cycle** (freeze + summary + report reset)
- A **post-mortem system** (fixed tags + freeform tags + AI draft)
- Lightweight PASS codes (optional, not strict)

## Single Source of Truth
All thresholds and guardrails referenced here must match `NOTRADE_CONSTANTS.yaml`:
- `policy.EDGE_NET_THRESHOLD`
- `policy.MAX_POSITION_PCT`
- `policy.MAX_WEEKLY_DRAWDOWN_PCT`
- `data_layer.POLY_MAX_STALENESS_S`
- `data_layer.REF_MAX_STALENESS_S`
- `data_layer.DECISION_INTEGRITY_WINDOW_MIN`
- `data_layer.PROB_JUMP_ALERT` + `data_layer.PROB_JUMP_WINDOW_S`

## Storage layout
- `ledger/`
  - `trade_ledger.jsonl` (append-only; one JSON per line)
- `post_mortems/`
  - post-mortem markdown files (human + AI draft)
- `reports/weekly/`
  - weekly report markdown files (Week freeze protocol)

## Quick start (MVP)
1) Create `ledger/trade_ledger.jsonl` (empty file).
2) Use `TRADE_LEDGER_SCHEMA.md` to log:
   - scheduled decisions (every 8 hours)
   - event-driven reconsiderations
3) After 19:00 local each day:
   - fill outcomes if resolved
   - draft post-mortems for LOSS / learning
4) In weekend:
   - write a `WEEK_SUMMARY` entry + weekly report
   - reset “current week report” to a new file

## Acceptance tests (must be easy)
Your ledger should answer quickly:
- “Show last 20 decisions where `edge_net >= EDGE_NET_THRESHOLD` and outcome was LOSS.”
- “Top 5 loss tags this week.”
- “Current open positions, invested vs remaining bankroll, last transaction timestamp.”