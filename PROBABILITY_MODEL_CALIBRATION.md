# Chapter 6 — Probability Model + Calibration (NoTrade)
**Document:** `PROBABILITY_MODEL_CALIBRATION.md`  
**Project:** NoTrade  
**Purpose:** estimate `P(event)` at decision time and ensure that the probabilities used by the Decision Engine are honest enough to survive real-world evaluation.

> **Constants:** all stable numeric thresholds and enum names live in `DATA_LAYER/NOTRADE_CONSTANTS.yaml`.
> **Stable PASS codes:** `DATA_LAYER/PASS_CODES.md` remains the SSOT.
> This chapter introduces **no new PASS code IDs** in v1.

---

## 0. Why Chapter 6 exists
NoTrade does not need a number generator. It needs a **probability engine**.

That means two separate jobs:
1. estimate whether the event will resolve **YES**;
2. verify that the estimated probability is actually trustworthy.

A model that outputs `0.70` is useful only if outcomes near 70% really happen at roughly that rate over time.
If not, the system is not calibrated. And if it is not calibrated, `edge_net` can look real while being made of smoke.

This chapter defines:
- what exactly the model predicts;
- how training examples are formed;
- how repeated decision-time predictions are handled;
- which metrics matter;
- how calibration is checked;
- how overconfidence is controlled;
- how model outputs map into existing repo fields without breaking current schemas.

> Design rule: NoTrade should prefer a less exciting but more truthful probability over an impressive-looking number that collapses under audit.

---

# 1. Core principles

## 1.1 The model predicts contract reality, not abstract price direction
NoTrade does not predict “BTC goes up” in a vague sense.
It predicts the probability that a **specific market event** resolves YES under the exact rules defined in `MARKET_RULES.md`.

Canonical target:

`P(event | information available at decision time t)`

Where:
- `event` is defined by the market’s real settlement logic;
- `t` is the actual decision timestamp;
- all inputs must be available strictly at or before `t`.

## 1.2 Family-specific models are the default
NoTrade uses **separate probability models by market family**, not one universal model for all crypto contracts.

Examples:
- BTC daily hit-price
- ETH daily hit-price
- future families added later

Reason:
- different event geometry;
- different volatility behavior;
- different sample sizes;
- different failure modes;
- targeted upgrades are easier and safer.

This matches the project architecture: separate families improve control without forcing global refactors.

## 1.3 Decision-time purity is non-negotiable
A probability is valid only if it uses data available at the exact moment the decision is made.

NoTrade must never train or infer using:
- future candles;
- future market prices;
- future liquidity states;
- future news outcomes;
- post-resolution information disguised as features.

If decision-time purity fails, the probability is invalid no matter how good backtests look.

## 1.4 Calibration matters more than bravado
For MVP, NoTrade values:
1. calibration quality;
2. stability;
3. auditability;
4. only then raw edge extraction.

A model that is directionally clever but badly calibrated is dangerous because it distorts EV.

## 1.5 Overconfidence is a systems problem, not just a numeric one
NoTrade should not automatically “trim” high probabilities just because they are high.
Instead, it should ask whether the confidence is supported by:
- feature quality;
- data integrity;
- regime familiarity;
- calibration health;
- evidence coherence.

When confidence is not justified, the system should widen uncertainty, tighten action rules, or PASS.

---

# 2. Prediction target and model output

## 2.1 Canonical target
For each market instance `m` at timestamp `t`:

`P_yes(m, t) = P(event_m = 1 | X_m,t)`

Where:
- `event_m = 1` means the market resolves YES;
- `X_m,t` is the feature vector computed from decision-time data;
- `m` belongs to one specific market family.

## 2.2 Point estimate used by the repo
To stay aligned with the current schema:
- `probs.model_prob_yes` in `MEMORY/TRADE_LEDGER_SCHEMA.md` should store the **calibrated point estimate actually used for the decision**;
- `probs.market_prob_yes` remains the executable YES entry price from Polymarket, not a midpoint complement;
- `probs.edge_net` remains the decision-time edge after costs.

This means the ledger stores the probability that actually mattered, not an intermediate raw score.

## 2.3 Where raw model internals should live
The current repo already allows structured model internals through `logic_output` in `DATA_LAYER/DATA_LAYER.md`.
That is the correct place for v1 extras such as:
- `raw_prob_yes`
- `confidence_band_low`
- `confidence_band_high`
- `uncertainty_score`
- `calibration_status`
- `calibration_window_id`
- `model_family`
- `model_version`
- `calibration_method`

This keeps the ledger stable while still preserving replayability and audit depth.

## 2.4 Recommended v1 output contract
At decision time, the probability layer should produce:

- `logic_output.raw_prob_yes`
- `probs.model_prob_yes`  ← calibrated point estimate used by the decision
- `logic_output.confidence_band_low`
- `logic_output.confidence_band_high`
- `logic_output.uncertainty_score`
- `logic_output.calibration_status`
- `logic_output.model_family`
- `logic_output.model_version`
- `logic_output.calibration_method`

Recommended `calibration_status` values:
- `FRESH`
- `AGING`
- `STALE`
- `INVALID`

Recommended `uncertainty_score` values:
- `LOW`
- `MEDIUM`
- `HIGH`
- `CRITICAL`

---

# 3. Repeated prediction policy

## 3.1 Same market, many decision-time evaluations
NoTrade may evaluate the same market multiple times before resolution.
For MVP, the canonical cadence is `probability_model.PREDICTION_CADENCE_MIN` minutes (default: 30).
That means:
- periodic re-evaluation every configured cadence step;
- plus event-driven re-evaluation when context changes materially.

This matches the current memory design, where a new `DECISION` entry may be created whenever the setup materially changes.

## 3.2 Repo-aligned logging rule
Each re-evaluation should be logged as a new `DECISION` entry linked through:
- `decision_group_id`
- `market.market_id`
- `as_of_ts_utc`
- `as_of_ts_local`

This preserves the full evolution of the probability through time instead of pretending the market was analyzed only once.

## 3.3 Event-driven reconsideration triggers
The model should be reconsidered when any of the following happens:
- `probs.edge_net` crosses below or above the action threshold;
- Polymarket probability jumps materially within `data_layer.PROB_JUMP_WINDOW_S`;
- data integrity fails or recovers;
- a major context shift changes the evidence set;
- time-to-resolution changes the feasibility geometry.

This is consistent with the existing reconsideration logic in `MEMORY/TRADE_LEDGER_SCHEMA.md`.

---

# 4. Labels and training rows

## 4.1 Label definition
For each resolved market:
- label `1` if the market resolves YES;
- label `0` if the market resolves NO.

Labels must be created strictly from the canonical rule system defined in `MARKET_RULES.md`.

## 4.2 Snapshot-based rows
Because the same market may be evaluated many times before close, one market can generate multiple training rows:
- same final label;
- different `as_of_ts_utc`;
- different feature values;
- different time-to-expiry;
- different market-implied probabilities.

This is valid, but it creates dependence between rows from the same market.

## 4.3 Anti-leakage split rule
Evaluation must remain chronological and group-aware.

NoTrade should avoid training on future snapshots of a market and testing on earlier snapshots of that same market.
At minimum:
- use time-based splits;
- keep same-market snapshots grouped where possible;
- never let future information leak backward.

If a validation method breaks this rule, the evaluation is not admissible.

---

# 5. Evaluation framework

## 5.1 Time-based evaluation only
NoTrade should use **walk-forward** or other chronological validation.
Random shuffles are not acceptable for model acceptance because they:
- blur regime changes;
- exaggerate stability;
- create hidden leakage in repeated-snapshot datasets.

## 5.2 Family-specific evaluation
Each market family should be evaluated independently.
Do not mix BTC daily hit-price performance with ETH daily hit-price performance and call it a single model score.

Reason:
- different base rates;
- different signal behavior;
- different calibration curves;
- different execution conditions.

## 5.3 Two evaluation planes
The model must pass on two planes:

### Statistical plane
Are the probabilities numerically honest?

### Economic plane
Would those probabilities have produced useful decisions under the Constitution and execution constraints?

A model that looks good statistically but cannot survive edge filtering is incomplete.
A model that made money in a short sample while being miscalibrated is not trustworthy either.

---

# 6. Scoring metrics

## 6.1 Primary v1 metric: Brier Score
The main metric for MVP is the **Brier Score**:

`Brier = mean((p_i - y_i)^2)`

Where:
- `p_i` is the predicted probability of YES;
- `y_i` is the realized outcome.

Why Brier is the right primary metric for v1:
- simple;
- probability-native;
- punishes overconfidence;
- easy to compare across model versions.

Lower is better.

## 6.2 Secondary metric: Log Loss
NoTrade should also track **Log Loss**.
This is useful because it punishes false certainty more aggressively than Brier.

Lower is better.

## 6.3 Reliability / calibration table
For each model family, NoTrade should maintain a reliability table by probability bucket.

Recommended v1 approach:
- fixed bins, e.g. width 0.10;
- for each bin record:
  - count;
  - average predicted probability;
  - realized YES frequency;
  - gap between the two.

Core question:
- when NoTrade says ~60%, does that bucket actually resolve YES around 60% of the time?

## 6.4 Expected Calibration Error (optional when sample allows)
If the validation sample is large enough, NoTrade may track an expected calibration error measure.
In very small samples, this should be treated cautiously and never worshipped as a magic summary statistic.

## 6.5 Sharpness
Calibration alone is not enough.
A model that always predicts around 50% can be perfectly dull.

NoTrade should also monitor whether the probability distribution has useful spread, while keeping calibration primary.

> Sharpness without calibration is a peacock with a broken compass.

---

# 7. Baselines and acceptance tests

## 7.1 Baselines are mandatory
A probability model has not earned respect until it beats simple baselines.
At minimum, compare against:
- **family base-rate baseline**;
- **market-implied probability baseline** using `probs.market_prob_yes`;
- a trivial heuristic baseline if one exists for the family.

## 7.2 Minimum acceptance logic for v1
A family model is provisionally acceptable only if:
- it is evaluated chronologically;
- it beats or at least meaningfully challenges naive baselines on Brier Score;
- Log Loss does not reveal pathological overconfidence;
- calibration tables are directionally sane;
- outputs are stable enough to support disciplined PASS behavior.

## 7.3 Rejection conditions
A model should be rejected or downgraded if:
- it performs well only on random splits;
- it beats baselines only by noise-level margins with no calibration benefit;
- its upper-probability buckets are badly overconfident;
- its performance collapses under out-of-sample windows;
- it depends on fragile inputs that often fail integrity gates.

---

# 8. Calibration layer

## 8.1 Raw score vs decision probability
The model’s first score should not automatically become the decision probability.
In NoTrade, calibration is the layer that converts a raw model output into the probability actually written to `probs.model_prob_yes`.

## 8.2 Preferred v1 methods
Because early sample size will likely be limited, NoTrade should start with conservative calibration methods.

Recommended order:
1. **simple shrinkage toward family base rate** when sample size is thin;
2. **Platt scaling** when enough validation data exists;
3. more flexible methods only after out-of-sample evidence justifies them.

## 8.3 Methods to avoid too early
Avoid aggressive calibration methods in sparse data regimes if they create pretty curves with no durable meaning.
Examples:
- highly flexible isotonic calibration on tiny samples;
- cross-family pooling without proof that the families behave similarly;
- repeated recalibration on very small rolling windows.

## 8.4 Calibration window discipline
Calibration should be fit only on past data and evaluated forward.
Never fit calibration on the same future outcomes that are later used to brag about performance.

## 8.5 What `probs.model_prob_yes` means in v1
To keep the repo internally clean:

- `logic_output.raw_prob_yes` = raw model score converted to probability scale;
- `probs.model_prob_yes` = calibrated probability used for edge computation and action logic.

That distinction should remain stable across future chapters.

---

# 9. Calibration health and freshness

## 9.1 Why freshness exists
Calibration is not eternal.
A model can be well-calibrated in one regime and sloppy in the next.

Therefore NoTrade should not treat calibration as “done once, trusted forever.”

## 9.2 `calibration_status`
Recommended operational meanings:

### `FRESH`
Recent evaluation is acceptable and sample coverage is adequate.

### `AGING`
Calibration still looks usable, but sample depth or regime stability is weakening.

### `STALE`
Calibration is no longer sufficiently supported by recent evidence.
Use caution and prefer PASS unless the rest of the case is unusually strong.

### `INVALID`
The probability layer is not trustworthy enough for decision use.
PASS should be the default.

## 9.3 Repo-aligned action rule
Because no dedicated Chapter 6 PASS code exists yet in `DATA_LAYER/PASS_CODES.md`, v1 should not invent one.
Instead:
- upstream data-driven causes should use their existing pass codes;
- if model uncertainty or calibration weakness destroys effective decision quality, use the closest existing policy code and explain the model reason in `action.reasoning`.

In practice:
- if uncertainty kills edge → `EDGE_TOO_SMALL`;
- if model risk dominates reward → `RISK_REWARD_UNFAVORABLE`;
- if the window is now too short → `TIMEFRAME_TOO_SHORT`;
- if stale inputs caused the problem → use the corresponding data-layer code.

This preserves PASS-code SSOT while still letting Chapter 6 veto bad decisions.

---

# 10. Uncertainty and confidence band

## 10.1 Point estimate is not enough
A single probability number hides fragility.
NoTrade should therefore produce a confidence band and an uncertainty score alongside the point estimate.

## 10.2 What should feed uncertainty
Recommended contributors:
- feature completeness;
- data-integrity state from `data_integrity.integrity_ok` and related staleness fields;
- local sample density for this family;
- calibration health;
- disagreement between raw and calibrated output;
- regime unfamiliarity;
- instability across recent re-evaluations.

## 10.3 Recommended use in v1
For MVP, uncertainty should primarily do three things:
- widen the confidence band;
- raise the standard for acting;
- make PASS more likely when the case is fragile.

It should **not** silently rewrite the point estimate in a way that makes the audit trail muddy.

## 10.4 Confidence-band interpretation
Example:
- `probs.model_prob_yes = 0.62`
- `logic_output.confidence_band_low = 0.55`
- `logic_output.confidence_band_high = 0.68`
- `logic_output.uncertainty_score = HIGH`

Interpretation:
- the model leans YES;
- the evidence is not clean enough for aggressive conviction;
- the decision layer should behave conservatively.

---

# 11. Overconfidence controls

## 11.1 Overconfidence definition
In NoTrade, overconfidence means the system expresses more certainty than the evidence deserves.

This can happen because of:
- tiny sample size;
- regime shifts;
- feature instability;
- noisy but seductive short-term signals;
- hidden leakage;
- poor calibration maintenance.

## 11.2 Evidence-based control ladder
NoTrade should respond proportionally.

### Mild concern
- keep the estimate;
- mark elevated uncertainty;
- allow normal monitoring.

### Moderate concern
- widen the confidence band;
- require cleaner edge;
- make PASS more likely.

### High concern
- treat the setup as fragile;
- prefer PASS unless the supporting evidence is unusually coherent.

### Critical concern
- probability not fit for action;
- PASS by default.

## 11.3 What should trigger concern
Examples:
- core features valid on paper but historically weak in this regime;
- raw probability extreme while calibration history for extreme bins is poor;
- repeated re-evaluations swing too violently without matching spot reality;
- the model thesis depends on one noisy input while stronger evidence blocks disagree.

## 11.4 What should not happen
NoTrade should not pretend confidence exists just because the model produced a large number.
A loud score is not the same thing as a justified score.

---

# 12. Economic evaluation

## 12.1 Why economic evaluation belongs here
Probability quality matters because it flows into `edge_net`, and `edge_net` drives action.
Therefore Chapter 6 cannot stop at statistics.

## 12.2 Economic checks to track
For each family and evaluation window, track:
- number of candidate signals;
- number of ENTER vs PASS outcomes;
- average `probs.edge_net` before and after calibration;
- hit rate by probability bucket;
- realized PnL / EV proxies in paper trading;
- behavior under uncertainty tiers;
- behavior near expiry.

## 12.3 Calibration must improve decisions, not just charts
A calibration layer is useful only if it improves practical decision quality, such as:
- fewer false-strong ENTERs;
- fewer low-quality trades near the threshold;
- better alignment between estimated edge and realized outcomes;
- cleaner PASS behavior in noisy conditions.

---

# 13. Repo integration notes

## 13.1 Alignment with current ledger schema
This chapter is aligned with the existing ledger fields:
- `probs.market_prob_yes`
- `probs.model_prob_yes`
- `probs.edge_net`
- `policy.pass`
- `policy.pass_code`
- `action.action_type`
- `action.reasoning`
- `decision_group_id`

No v1 schema break is required.

## 13.2 Where to store new model metadata without breaking v1
Use `logic_output` / provenance-style storage for:
- raw model score;
- calibration diagnostics;
- confidence band;
- uncertainty score;
- family/model identifiers.

This preserves replayability and lets later chapters expand the schema only if needed.

## 13.3 PASS-code discipline
Chapter 6 does **not** create new stable PASS code IDs in v1.
It consumes the existing SSOT and uses `action.reasoning` to explain model-level vetoes when needed.

This avoids PASS-code drift and keeps the repo internally clean.

---

# 14. Recommended v1 implementation path

## 14.1 Model form
For MVP, the preferred starting model is simple and auditable.
Recommended order:
1. logistic regression or similarly interpretable baseline;
2. conservative calibration layer;
3. richer models only after evidence warrants them.

## 14.2 v1 operating behavior
A clean MVP should support:
- family-specific modeling;
- repeated decision-time prediction;
- calibrated point estimate;
- uncertainty + confidence band;
- model-health awareness;
- PASS-first discipline when trust is weak.

## 14.3 v1 success condition
v1 is successful if it can power the paper simulator with probabilities that are:
- chronologically valid;
- reasonably calibrated;
- audit-friendly;
- stable enough to support disciplined ENTER / PASS behavior.

It does **not** need to be fancy. It needs to be honest.

---

# 15. Minimum chapter-complete standard
Chapter 6 should be considered MVP-complete only if NoTrade has:
- a formal prediction target;
- family-specific models;
- repeated decision-time evaluation support;
- chronological validation;
- Brier Score tracking;
- Log Loss tracking;
- calibration tables by family;
- at least one conservative calibration method;
- uncertainty output;
- calibration-status output;
- overconfidence controls;
- repo-aligned mapping to current ledger and PASS-code conventions.

If these conditions are not met, the system has scores, but not yet a trustworthy probability layer.

---

# 16. Final design rule
> NoTrade should not chase certainty. It should chase honest probabilities.  
> A modest estimate that behaves truthfully is more valuable than a dramatic estimate that flatters the operator and poisons the ledger.
