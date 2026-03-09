# Chapter 7 — Decision Engine (The CFO Brain)
**Document:** `DECISION_ENGINE.md`  
**Project:** NoTrade  
**Purpose:** convert calibrated probabilities into disciplined portfolio actions without drifting away from market rules, data-integrity gates, or bankroll constraints.

> **Constants:** all stable numeric thresholds and enum names must come from `DATA_LAYER/NOTRADE_CONSTANTS.yaml`.
> **Stable PASS codes:** `DATA_LAYER/PASS_CODES.md` remains the SSOT for `policy.pass_code`.
> **Ledger contract:** actions and reasoning must map cleanly into `MEMORY/TRADE_LEDGER_SCHEMA.md`.

---

## 0. Why Chapter 7 exists
Chapter 6 estimates `P(event)`. Chapter 7 decides what, if anything, should be done with that probability.

This chapter does **not** try to be smarter than the probability model. It acts as the system’s disciplined allocator:
- it blocks low-quality or noisy setups;
- it converts valid edge into a position size;
- it protects the bankroll when the thesis deteriorates;
- it logs actions in a way that can be audited later.

> Design rule: the Decision Engine is a strict gatekeeper, not a creativity engine.

---

## 1. Scope and non-goals

## 1.1 What the Decision Engine does
The Decision Engine:
- consumes the calibrated point estimate from Chapter 6;
- checks whether conditions are clean enough to act;
- applies Constitution-level risk rules;
- chooses one verdict from the allowed action set;
- computes a disciplined sizing recommendation;
- maps the verdict into ledger-ready action semantics.

## 1.2 What it does **not** do
The Decision Engine does **not**:
- estimate raw probability from scratch;
- rewrite market rules from Chapter 2;
- override data-integrity failures from Chapter 3;
- invent new PASS code IDs outside `DATA_LAYER/PASS_CODES.md`;
- force action just because a market is being watched.

---

## 2. Canonical inputs
The Decision Engine should consume the following decision-time fields.

## 2.1 Market and timing context

## 2.1A Snapshot price semantics
- `market_prob_yes` and `market_prob_no` are **best executable entry prices**, not midpoint complements.
- If `best_yes_ask` / `best_no_ask` are present, `market_prob_yes` / `market_prob_no` must match those asks exactly.
- Their sum may be **greater than 1.00** because the book can have spread / overround.
- Mid-like diagnostics can be derived separately from bid/ask data and should not replace the executable fields.

- `market.definition.market_id`
- `market.definition.market_type`
- `market.definition.asset`
- `market.definition.event_ts_utc`
- `market.snapshot.market_prob_yes` (best executable YES entry price; ask-like if book data is present)
- `market.snapshot.market_prob_no` (best executable NO entry price; ask-like if book data is present)
- `market.snapshot.best_yes_bid / best_yes_ask`
- `market.snapshot.best_no_bid / best_no_ask`
- `market.snapshot.quoted_spread_pct` (max observed bid/ask spread on the 0–1 contract-price scale)
- `market.snapshot.yes_depth_usd / no_depth_usd`
- `market.snapshot.time_to_expiry_min`

## 2.2 Integrity and feature validity
- `data_integrity.integrity_ok`
- `data_integrity.poly_staleness_s`
- `data_integrity.ref_staleness_s`
- `data_integrity.data_latency_ms`
- availability / validity of `features.core_features_v1`
- optional availability of `features.context_features_v2`

## 2.3 Probability-layer outputs
- `probs.market_prob_yes`
- `probs.model_prob_yes`
- `probs.edge_net`
- `logic_output.raw_prob_yes`
- `logic_output.confidence_band_low`
- `logic_output.confidence_band_high`
- `logic_output.uncertainty_score`
- `logic_output.calibration_status`
- `logic_output.model_family`
- `logic_output.model_version`

## 2.4 Portfolio and policy context
- `policy.bankroll_usd`
- `policy.total_invested_usd`
- `policy.open_positions_count`
- current correlated exposure across open positions
- current position state for the same market / same thesis
- safety-mode state from Chapter 1

## 2.5 Better-opportunity context
If portfolio rotation is supported later, the engine may also compare:
- current open thesis edge;
- alternative opportunity edge;
- friction to exit and re-enter elsewhere.

---

## 3. Output contract

## 3.1 Allowed verdicts
The canonical Decision Engine verdict set for v1 is:
- `PASS`
- `ENTER`
- `HOLD`
- `EXIT`

These verdict names should remain stable and align with `decision_engine.ACTION_TYPES` in `DATA_LAYER/NOTRADE_CONSTANTS.yaml`.

`HEDGE` may still exist later as a ledger- or execution-level action, but it is not part of the core Chapter 7 verdict set for MVP.

## 3.2 Semantics of each verdict
### `PASS`
Used only when there is **no open position** and the engine declines to initiate one.

Typical causes:
- edge too small;
- data integrity failure;
- noisy signals;
- exposure caps already reached;
- timeframe too short;
- market definition ambiguity.

### `ENTER`
Used when there is no disqualifying gate and the engine recommends opening or adding exposure.

In ledger terms, `ENTER` normally maps to at least one `BUY` transaction. `DecisionOutput.requested_tx_type` should therefore default to `BUY`.

### `HOLD`
Used only when an **open position already exists** and a full exit is **not** justified at the current evaluation.

`HOLD` is not valid in flat state.

### `EXIT`
In Decision Engine semantics, `EXIT` means **full flatten** of the relevant thesis.

In ledger / transaction semantics, `EXIT` must map to a transaction set that fully closes the relevant exposure, typically through `SELL`. `DecisionOutput.target_position_id` should point to the thesis being flattened, and `requested_tx_type` should default to `SELL`.

## 3.3 Partial reductions
Partial `SELL` operations may exist at the **transaction** level, but they are **not** part of the core v1 Decision Engine verdict set.

That means:
- `EXIT` = full exit / full flatten;
- partial selling remains an execution-level adjustment and should not replace the core policy verdict vocabulary in v1.

---

## 4. State model
The Decision Engine should reason from position state first, not last.

## 4.1 Canonical position states
- **FLAT**: no relevant open exposure exists.
- **OPEN**: relevant exposure exists and must be actively managed.

For MVP, `FLAT` and `OPEN` are the only thesis-level position states.

Cooldown is modeled separately as a **portfolio/runtime guard** through a field such as `portfolio.cooldown_until_utc`, rather than as a third position state. This keeps Chapter 7 semantics crisp while still allowing temporary re-entry blocks after integrity shocks or reevaluation events.

## 4.2 Valid verdicts by state
### If state = `FLAT`
Valid verdicts:
- `PASS`
- `ENTER`

### If state = `OPEN`
Valid verdicts:
- `HOLD`
- `EXIT`

This simple split prevents semantic drift such as “PASS while already holding a live position” when what the system really means is “continue holding”.

---

## 5. Decision hierarchy (gating order)
The engine should evaluate conditions in the following order.

## 5.1 Gate 1 — market validity
If the market definition is invalid, unsupported, or ambiguous, the engine must refuse action.

Typical result:
- `PASS` with dominant `pass_code` such as `INVALID_MARKET_METADATA`, `UNSUPPORTED_MARKET_TYPE`, or `MARKET_DEFINITION_AMBIGUOUS`.

## 5.2 Gate 2 — integrity validity
If `data_integrity.integrity_ok = false`, the engine must not initiate fresh exposure.

This gate is controlled by:
- `decision_engine.REQUIRE_INTEGRITY_OK_FOR_ENTER`
- `data_layer.DECISION_INTEGRITY_WINDOW_MIN`

Typical result:
- `PASS` if flat;
- `EXIT` only if an existing thesis is materially invalidated by integrity collapse and continued exposure can no longer be justified.

## 5.3 Gate 3 — core feature validity
If minimum deployable features from Chapter 5 are stale, missing, or contradictory in a critical way, the engine should refuse fresh exposure.

This gate is controlled by:
- `decision_engine.REQUIRE_CORE_V1_VALID_FOR_ENTER`
- `decision_engine.ALLOW_V2_MISSING`

Interpretation:
- missing `context_features_v2` is allowed in v1;
- broken `core_features_v1` is not.

## 5.4 Gate 4 — timeframe feasibility
If time left is too short for realistic execution and edge survival, the engine must refuse new action.

Primary rule:
- if `time_to_expiry_min < policy.TIMEFRAME_PASS_UNDER_MIN` → `PASS` by default.

Caution window:
- `policy.TIMEFRAME_CAUTION_UNDER_MIN` is the zone where only unusually clean, liquid, intraday-relevant setups should survive.

## 5.5 Gate 5 — execution realism
If spread, depth, or slippage likely erase the edge, the engine must refuse the trade.

Typical dominant pass codes:
- `INSUFFICIENT_LIQUIDITY`
- `SLIPPAGE_UNKNOWN`

## 5.6 Gate 6 — value test
If `probs.edge_net < active_edge_threshold`, there is no trade.

The active threshold is normally:
- `policy.EDGE_NET_THRESHOLD`

In Safety Mode, the active threshold should tighten to:
- `policy.SAFETY_MODE_EDGE_THRESHOLD`

Typical dominant pass code:
- `EDGE_TOO_SMALL`

## 5.7 Gate 7 — exposure and bankroll constraints
Even when edge exists, the engine must refuse action if:
- `policy.MAX_POSITION_PCT` would be breached;
- `policy.MAX_BTC_DIRECTION_EXPOSURE_PCT` would be breached;
- `policy.MAX_TOTAL_CORRELATED_EXPOSURE_PCT` would be breached.

Typical dominant pass codes:
- `EXPOSURE_LIMIT_REACHED`
- `CORRELATED_EXPOSURE_LIMIT_REACHED`
- `DRAWDOWN_LIMIT_REACHED`

## 5.8 Gate 8 — position-state action logic
Only after all earlier gates pass should the engine decide between:
- `ENTER` vs `PASS` when flat;
- `HOLD` vs `EXIT` when open.

---

## 6. Clean conditions
In this project, “clean conditions” should not be vague. For MVP they should mean all of the following:
- market definition is valid;
- `data_integrity.integrity_ok = true`;
- core v1 features are valid enough to support probability claims;
- timeframe is still tradable;
- execution friction is conservative and acceptable;
- `probs.edge_net` survives the active threshold after costs;
- exposure caps are not violated;
- no dominant PASS code is present.

Optional v2 enrichments may improve confidence, but they should not be mandatory for basic v1 actionability.

---

## 7. ENTER rules
The engine may emit `ENTER` only when all of the following are true:
- current state is `FLAT`;
- no market-definition veto exists;
- no integrity veto exists;
- no core-feature veto exists;
- timeframe remains tradable;
- execution realism is acceptable;
- `probs.edge_net >= active_edge_threshold`;
- exposure and bankroll rules remain within limits;
- sizing remains positive after all caps.

## 7.1 ENTER reasoning standard
An `ENTER` recommendation must be traceable to:
- the calibrated probability used;
- the executable market-implied probability used;
- the cost assumptions used;
- the threshold that was cleared;
- the position size selected.

## 7.2 ENTER default mapping to transactions
In ledger terms, `ENTER` should usually map to:
- one `BUY` transaction;
- on the selected side (`YES` or `NO`);
- using either `USD` or `SHARES`, as recorded by execution.

---

## 8. HOLD rules
The engine may emit `HOLD` only when all of the following are true:
- current state is `OPEN`;
- the thesis remains sufficiently intact;
- no full-exit condition is triggered;
- no clearly superior alternative justifies rotation;
- integrity remains good enough that the position is still understandable and defensible.

`HOLD` should be the default for an open position when the case is still good enough but no new action is required.

---

## 9. EXIT rules
`EXIT` is reserved for full flattening of the active thesis.

The engine should emit `EXIT` when one or more of the following occurs:
- the thesis is materially invalidated;
- integrity collapses in a way that destroys confidence in the original case;
- `probs.model_prob_yes` shifts against the thesis by at least `decision_engine.MATERIAL_PROB_SHIFT_ABS` and the change is not just noise;
- `probs.edge_net` deteriorates materially below the active threshold, beyond a small hysteresis buffer;
- a clearly better opportunity exists and switching is net beneficial after friction.

## 9.1 Exit hysteresis
To avoid overreacting to tiny wiggles, Chapter 7 uses:
- `decision_engine.EXIT_EDGE_BUFFER`

Interpretation:
- do not force full exit on every microscopic sub-threshold flicker;
- require deterioration that is meaningfully worse than simple threshold noise.

## 9.2 Better opportunity rule
If a different opportunity appears, rotation should be considered only if:
- the alternative edge is superior by at least `decision_engine.BETTER_OPPORTUNITY_MIN_EDGE_DELTA`;
- the switch is still positive after exit and re-entry friction;
- the new trade does not violate exposure caps;
- the alternative is not merely more exciting, but measurably better.

For MVP, the engine may simply emit `EXIT` and let the next evaluation produce a fresh `ENTER`, rather than encoding a complex multi-leg rotation object.

---

## 10. PASS rules
`PASS` should be the default verdict when the system is flat and cannot justify a fresh position.

Typical reasons include:
- edge too small;
- insufficient liquidity;
- timeframe too short;
- integrity failure;
- broken core features;
- ambiguous market rules;
- exposure caps already reached.

## 10.1 Dominant PASS-code discipline
If several problems exist at once, the engine should:
- choose the dominant `policy.pass_code` from `DATA_LAYER/PASS_CODES.md`;
- record secondary issues inside `action.reasoning`.

This preserves SSOT while still keeping decision logs honest.

---

## 11. Sizing policy
Sizing belongs in Chapter 7 because capital allocation is part of the decision, not an afterthought.

## 11.1 Sizing inputs
Sizing should depend on:
- `probs.edge_net`;
- confidence / uncertainty context from Chapter 6;
- execution quality;
- current exposure;
- safety mode status;
- Constitution-level risk caps.

## 11.2 Canonical bucket logic
Recommended bucket mapping for v1:
- if `edge_net` is between `policy.EDGE_NET_THRESHOLD` and 0.05 → `policy.SMALL_EDGE_POSITION_PCT`
- if `edge_net` is between 0.05 and 0.08 → `policy.DEFAULT_POSITION_PCT`
- if `edge_net` is above 0.08 and conditions are exceptionally clean → up to `policy.STRONG_EDGE_MAX_POSITION_PCT`

In all cases:
- never exceed `policy.MAX_POSITION_PCT`;
- never exceed correlation caps;
- reduce size further in Safety Mode.

## 11.3 Confidence interaction
Confidence may shape sizing only if confidence is earned.

That means the engine may size down when:
- `logic_output.uncertainty_score` is high;
- `logic_output.calibration_status` is aging or stale;
- execution conditions are borderline;
- context features disagree with the core case.

Confidence should never be used as an excuse to break hard caps.

---

## 12. Reconsideration policy
NoTrade should be allowed to speak up without being manually asked.

## 12.1 Periodic reconsideration
Periodic reconsideration follows:
- `probability_model.PREDICTION_CADENCE_MIN`

Each periodic evaluation may produce a new `DECISION` entry.

## 12.2 Event-driven reconsideration
A new evaluation should also occur when:
- `probs.edge_net` crosses above or below the active threshold;
- market probability jumps materially within `data_layer.PROB_JUMP_WINDOW_S`;
- data integrity fails or recovers;
- a major news or volatility regime shift changes the evidence set;
- a current thesis experiences a material probability shift.

## 12.3 Reconsideration cooldown
To avoid thrashing, event-driven reconsideration should respect:
- `decision_engine.REEVALUATION_COOLDOWN_MIN`

This is a guardrail, not a gag order. It exists to prevent repetitive noise reactions, not to suppress meaningful new opportunities.

---

## 13. Ledger mapping requirements
The Decision Engine must map cleanly into `MEMORY/TRADE_LEDGER_SCHEMA.md`.

## 13.1 Fields that must be filled by the decision layer
At minimum:
- `policy.edge_threshold`
- `policy.bankroll_usd`
- `policy.risk_ok`
- `policy.pass`
- `policy.pass_code`
- `policy.sizing_pct`
- `policy.stake_usd`
- `action.action_type`
- `action.reasoning`
- `action.transactions`

## 13.2 Action mapping
Recommended mapping:
- `PASS` → no position opened, `policy.pass = true`
- `ENTER` → one or more `BUY` transactions
- `HOLD` → no full-exit transaction, thesis retained
- `EXIT` → transaction set fully closes the active thesis, usually via `SELL`

## 13.3 Partial sell handling
If later versions support partial reduction:
- keep `SELL` as a transaction-level event;
- do not silently overload `EXIT` to mean both “trim” and “flatten”.

That distinction keeps the policy layer auditable.

---

## 14. Pseudocode (repo-aligned)
```text
function decide(context):
    state = get_position_state(context)
    active_threshold = policy.EDGE_NET_THRESHOLD

    if safety_mode(context):
        active_threshold = policy.SAFETY_MODE_EDGE_THRESHOLD

    if market_invalid(context):
        return PASS(dominant_pass_code)

    if state == FLAT:
        if integrity_blocked(context):
            return PASS(dominant_pass_code)

        if core_v1_invalid(context):
            return PASS(dominant_pass_code)

        if timeframe_too_short(context):
            return PASS(TIMEFRAME_TOO_SHORT)

        if execution_unreliable(context):
            return PASS(INSUFFICIENT_LIQUIDITY or SLIPPAGE_UNKNOWN)

        if edge_net(context) < active_threshold:
            return PASS(EDGE_TOO_SMALL)

        if exposure_blocked(context):
            return PASS(EXPOSURE_LIMIT_REACHED or CORRELATED_EXPOSURE_LIMIT_REACHED)

        size = compute_size(context, active_threshold)

        if size <= 0:
            return PASS(EXPOSURE_LIMIT_REACHED)

        return ENTER(size)

    if state == OPEN:
        if integrity_materially_breaks_thesis(context):
            return EXIT

        if material_prob_shift_against_position(context, decision_engine.MATERIAL_PROB_SHIFT_ABS)
           and edge_deteriorated_beyond_buffer(context, decision_engine.EXIT_EDGE_BUFFER):
            return EXIT

        if better_opportunity_exists(context, decision_engine.BETTER_OPPORTUNITY_MIN_EDGE_DELTA)
           and switch_is_net_positive_after_friction(context):
            return EXIT

        return HOLD
```

---

## 15. Acceptance tests
A Chapter 7 implementation should satisfy examples like these.

## 15.1 Clean edge while flat
- integrity good
- core v1 valid
- edge_net above threshold
- exposure available

Expected result:
- `ENTER`

## 15.2 Small edge while flat
- `edge_net < policy.EDGE_NET_THRESHOLD`

Expected result:
- `PASS` with `EDGE_TOO_SMALL`

## 15.3 Integrity failure while flat
- `data_integrity.integrity_ok = false`

Expected result:
- `PASS` with the dominant integrity-related pass code

## 15.4 Open position, thesis intact
- position open
- no material deterioration
- no superior alternative

Expected result:
- `HOLD`

## 15.5 Open position, thesis breaks
- position open
- model probability shifts materially against the thesis
- edge deteriorates beyond the exit buffer

Expected result:
- `EXIT`

## 15.6 Better opportunity appears, but not enough
- alternative exists
- edge improvement is smaller than `decision_engine.BETTER_OPPORTUNITY_MIN_EDGE_DELTA`

Expected result:
- remain `HOLD`

---

## 16. Chapter 7 completion criteria
Chapter 7 is “done enough” for MVP when:
- the verdict vocabulary is stable and SSOT-aligned;
- sizing is deterministic and constrained;
- `HOLD` exists only for open positions;
- `EXIT` clearly means full flatten;
- event-driven reconsideration can surface both defensive and offensive opportunities;
- logs map cleanly into the ledger without semantic confusion.

> If the engine is ever unsure whether action is justified, it should choose restraint over improvisation.
