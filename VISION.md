# NoTrade

NoTrade is a probability-driven AI/ML “CFO” for crypto prediction markets.  
It is designed to estimate **probabilities** (not “certainty”) about whether a crypto price will reach a given level within a defined time window and to act only when it detects **real edge**.

> Keyword: “should be” 😄 (because reality will fight back, and we will adapt.)

---

## What is NoTrade?

**NoTrade** is an AI built to predict, as well as realistically possible, the probability of specific price outcomes in crypto over the next **X hours** (or by a certain date/time).

It behaves like a disciplined analyst:
- collects signals (via APIs)
- transforms them into features
- estimates **P(event)** (probability the event resolves YES)
- compares it with the market’s implied probability
- outputs a decision: **ENTER / PASS / EXIT / RE-EVALUATE**

It learns over time through a structured memory system (a ledger of decisions + outcomes), and improves via incremental retraining.

---

## What is it NOT?

NoTrade is **not** a magical tool that predicts the market with perfect accuracy.
- It will never be 100% accurate.
- It is **not** a fully automated execution bot (it does not click/place orders for you).
- It is **not** a validation machine. Its job is to challenge weak logic and avoid bad trades.

You execute trades manually. NoTrade provides the decision, reasoning, and thresholds.

**Constants + stable IDs:** see `NOTRADE_CONSTANTS.yaml` and `PASS_CODES.md`.

---

## The Most Important Rule

If there is **NO EDGE**, there will be **NO TRADE**.

NoTrade optimizes for **EV (Expected Value)**, not for “being right as often as possible”.
- It prefers fewer, higher-quality trades over constant action.
- It is allowed to output **0 trades per day** if conditions are not good.
- Position sizing is adaptive: higher confidence and cleaner conditions can justify larger size, but only within strict risk limits.

---

## Target Market

Primary focus: **daily hit-price by date** on major crypto assets:
- BTC / ETH / SOL / XRP

Why hit-price daily:
- defined resolution rules
- measurable probabilities
- good fit for a disciplined “edge vs. implied probability” framework

**Phase 1 will be paper trading** with a virtual bankroll (e.g., $500) to validate behavior, logic, and EV before using real capital.

---

## How NoTrade Thinks (High-Level)

NoTrade estimates probabilities using a blend of signals such as:
- technical indicators (RSI, MACD, trend, volatility, momentum)
- news flow and event shocks (optional early stage)
- social sentiment (optional early stage)
- whale flows / large transfers (optional later)
- microstructure (order book / liquidity) (optional later)

The system is built to start **minimal and reliable**, then grow in complexity only if it improves results.

---

## Architecture roadmap
The chapter-by-chapter plan lives in `CHAPTERS.md`.
