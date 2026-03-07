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
- update outcomes / PnL where resolved
- generate AI draft post-mortems
- mark entries for review where needed

## 3) Weekend freeze (Week close)
On weekend (recommended Sunday after 19:00 local):
1. Generate weekly report `MEMORY/reports/weekly/YYYY-Www.md`
2. Append a single `WEEK_SUMMARY` entry to the ledger pointing to that report
3. Start a new weekly report file for Week+1 (blank template)

## 4) What must go into the weekly report
- realized PnL
- EV total (if tracked)
- hit rate
- max drawdown
- biggest loss (pct)
- top 5 loss tags
- 3 fixes for next week (rules / features / process)

## 5) Reset policy
Ledger is **one big file**, never reset.
Reports are per-week, and the “current report” resets when the week closes.
