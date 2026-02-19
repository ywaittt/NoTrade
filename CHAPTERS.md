## Project Chapters (Architecture)

Each chapter will be developed in a separate conversation and ends with a clear deliverable.

### 1) Constitution: Rules, Metrics, and Identity
**Goal:** define what NoTrade is allowed to do and what success means.  
**Deliverable:** a “Constitution” document:
- success metrics (weekly/monthly profit, EV targets, drawdown limits)
- the net-edge threshold (e.g., ≥ 3% after all costs)
- when NoTrade must output PASS
- risk constraints and sizing philosophy

### 2) Market Rules: “Reality is the Rules”
**Goal:** ensure every prediction matches the market’s resolution conditions.  
**Deliverable:** a standard **Market Spec** template:
- asset, timeframe, strike/target
- resolution source and rule logic (high/last, interval, timezone)
- anything that could break assumptions

### 3) Data Layer: Collection and Storage
**Goal:** decide what data is used, from where, and at what frequency.  
**Deliverable:** a **Data Dictionary**:
- APIs, rate limits, reliability notes
- raw data schema (OHLCV, indicators, market implied prob)
- storage format and folder structure

### 4) Memory: Ledger + Post-Mortems
**Goal:** make the AI learn from decisions and mistakes.  
**Deliverable:** a **Trade Ledger schema**:
- features at decision time
- model probability vs market probability
- action taken (ENTER/PASS/EXIT)
- outcome and post-mortem tags (“false signal”, “news shock”, etc.)

### 5) Feature Engineering: Turning Data into Signals
**Goal:** define feature sets (v1 simple, v2 richer).  
**Deliverable:** a feature list with notes:
- what it measures
- when it is reliable
- known failure modes

### 6) Probability Model + Calibration
**Goal:** predict **P(event)** and ensure probabilities are trustworthy.  
**Deliverable:** evaluation framework:
- calibration checks (are 60% predictions actually ~60%?)
- scoring metrics (e.g., Brier score)
- overconfidence controls

### 7) Decision Engine: The CFO Brain
**Goal:** convert probabilities into disciplined actions.  
**Deliverable:** decision rules (pseudocode-level):
- ENTER if net edge ≥ threshold and conditions are clean
- EXIT if probability materially shifts or better opportunity appears
- PASS by default when signals are noisy

### 8) Paper Trading Simulator
**Goal:** test behavior safely with a virtual bankroll.  
**Deliverable:** a simulator definition:
- fills assumptions (market vs limit behavior)
- fees/slippage model (even if simplified first)
- performance reports (PnL, drawdown, trade frequency, EV)

### 9) Interface: Terminal and/or Dashboard
**Goal:** make it usable across devices (PC + laptop + iPad as viewer).  
**Deliverable:** UI mock outputs:
- daily brief
- trade ticket
- alert format (only when something meaningful changes)
- weekly review report

### 10) Ops: Local → Cloud
**Goal:** run reliably and safely long-term.  
**Deliverable:** operating rules:
- config management
- logging + backups
- separating secrets from repo
- reproducible runs

---

## Phase 1 Commitment (Paper Trading)

For the first month:
- No real money.
- A virtual bankroll (e.g., $500).
- NoTrade generates decisions + reasoning + logs.
- We review weekly and update the model incrementally.

If NoTrade cannot demonstrate discipline and net EV in paper trading, it does not get promoted to real capital.

---
