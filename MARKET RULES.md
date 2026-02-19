# Chapter 2 — Market Rules (the truth in Polymarket)
**Document:** `MARKET_RULES.md`  
**Project:** NoTrade  
**Purpose:** define, with zero ambiguity, what “YES/NO” means for each market so NoTrade calculates probabilities and EV against the *correct* definition of reality (not assumptions).

---

## 0) Why Chapter 2 exists (and why it’s non-negotiable)
Polymarket markets are not “bets on price” in a generic sense. Each market is a **contract** with **resolution rules**.

NoTrade must not “guess the market”. It must evaluate:

1. **What exactly does the contract claim will happen?**
2. **What is the official resolution source?**
3. **What time window and timezone apply?**
4. **Which price metric is used?** (Close/High/Low/Index/Snapshot)
5. **How do we convert the rules into deterministic YES/NO logic?**
6. **What edge cases exist and how do we handle them consistently?**

If you skip this chapter:
- you may treat a market as “touch” when it’s actually “close at a snapshot”;
- you may use Romania time instead of ET/UTC and be wrong during DST shifts;
- you may compare with the wrong boundary logic (>, >=, strict vs inclusive);
- you may pull prices from a different source than the one used to resolve the market.

**Conclusion:** Market Rules = the definition of truth.  
Chapter 3 (APIs) only brings data; Chapter 2 defines what that data *means*.

---

## 1) Terms (short but important glossary)

### 1.1 “Hit”
In our internal language: **“hit” = our bet wins according to the market’s rules**.  
Note: Polymarket may use “hit price” in the title, but the market may actually be:
- **TOUCH** (it reaches a level at any time)
- **SNAPSHOT/CLOSE** (value at a specific moment)
- **RANGE** (value within an interval)
- **DIRECTION** (comparison between two times)

NoTrade must use the **real** rule type from the rules, not the word in the title.

### 1.2 “Resolution Source”
The official source that determines YES/NO.  
Example: “Binance BTC/USDT 1-minute candle Close price.”

### 1.3 “Price Metric”
The exact thing compared from the source:
- **Close** (candle close)
- **Open**
- **High / Low**
- **Last traded**
- **Index value**
- **Snapshot** (value at a specific timestamp)

### 1.4 Timezone & DST (critical)
Markets may be defined in:
- **ET (Eastern Time)**
- **UTC**
- other timezones

**Romania time (Europe/Bucharest) is not a safe base** when the market is defined in ET.  
ET–Romania can be **6 or 7 hours** depending on DST timing.  
Rule: write the spec in the market’s timezone; convert later in code.

---

## 2) Core concept: “Market Spec”
For every market we analyze, we complete a standard “Market Spec” sheet.  
This lets NoTrade:
- understand the market (meaning),
- know what data to request (APIs),
- compute probabilities and EV on a correct definition.

### 2.1 Official template: Market Spec
> Copy the template below for each market.  
> If a field is not applicable, set it to `N/A` and explain why.

---

# Market Spec (Template)

## A) Identity & classification
**Market ID / Slug:**  
**Market Title:**  
**Market URL:** (optional, for reference)  

**Market Type:**
- [ ] TOUCH (reaches a threshold at any time)  
- [ ] SNAPSHOT/CLOSE (value at a specific time)  
- [ ] RANGE (value within an interval)  
- [ ] DIRECTION (compare two timestamps)  
- [ ] EVENT (non-price event: elections, news, etc.)  

**One-liner:** (one sentence: “This market is YES if …”)

---

## B) Resolution rule (no interpretation)
**Resolution Condition (faithful copy/paraphrase):**  
(1–4 clear sentences, no ambiguity)

**Resolution Source (official):**  
(e.g., Binance BTC/USDT, 1m candles, Close price)

**Instrument / Pair:** (e.g., BTC/USDT)  
**Venue / Provider:** (e.g., Binance)  
**Quote Currency:** (e.g., USDT)  
**Base Asset:** (e.g., BTC)

---

## C) Time: window, timezone, expiry
**Date specified in title:** (format: YYYY-MM-DD)  
**Timezone (official):** (ET / UTC / etc.)  
**Start:** (timestamp + timezone)  
**End / Snapshot time:** (timestamp + timezone)  

**Expiry details:**  
- If it says “by date X”, clarify whether a specific time is included.

**DST warning:**  
- Note whether the timezone uses DST and how that affects conversions.

---

## D) Price: metric, granularity, exact definition
**Price Metric Used:**
- [ ] Close  
- [ ] Open  
- [ ] High  
- [ ] Low  
- [ ] Last trade  
- [ ] Index snapshot  
- [ ] Other: _______

**Exact Definition:**
- Which candles? (1m/5m/1h)  
- Candle start/end definition (e.g., 12:00:00–12:00:59.999 ET)  
- “Close” = the last price of that candle.

**Granularity required:**
- 1m / 5m / 1h / tick

---

## E) Binary condition (YES/NO logic)
**YES if:** (explicit logic, deterministic)  
**NO if:** (explicit logic, deterministic)

**Boundary rules:**
- [ ] strict: `>` / `<`  
- [ ] inclusive: `>=` / `<=`  
Explain your choice based on the actual rules.

**Rounding rules:**
- Precision used?
- Do we round or compare raw values?
Default recommendation: **compare raw values from the official source without rounding.**

---

## F) Edge Cases & Pitfalls
**Ambiguous wording:**  
**Exchange disagreements:** (N/A if the source is single)  
**Wicks/spikes:** do they matter? (depends on High/Low vs Close)  
**Missing data / downtime:** what do we do if the candle is missing?  
**Precision / floating errors:** prefer `Decimal` over floats.

---

## G) Data Needed (for Chapter 3)
**Market metadata needed:**
- rules text  
- expiry  
- resolution source fields (if available)  
- strike/interval (if range)

**Price feed needed:**
- candles endpoint  
- interval = 1m  
- exact timestamp needed

---

## H) Validation Plan (how we verify the spec is correct)
- 2–3 “manual check” scenarios  
- cross-check with UI (Binance candles)
- historical test where possible

---

## I) Implementation Notes (for later)
- map market to internal `rule_type`
- e.g., `RULE_TYPE = SNAPSHOT_CLOSE_ABOVE`
- e.g., `TIMEZONE = ET`
- e.g., `SOURCE = BINANCE_SPOT`

---

## 3) Standardization: internal Rule Types
To avoid reinventing logic for every market, we define internal rule types.

### 3.1 Common crypto “daily” types

#### (1) `SNAPSHOT_CLOSE_ABOVE`
YES if `Close(t_snapshot) > X`.

#### (2) `SNAPSHOT_CLOSE_BELOW`
YES if `Close(t_snapshot) < X`.

#### (3) `SNAPSHOT_CLOSE_IN_RANGE`
YES if `low < Close(t_snapshot) < high` (or inclusive if rules say so).

#### (4) `TOUCH_HIGH_ABOVE`
YES if `High(any candle in window) >= X`.

#### (5) `TOUCH_LOW_BELOW`
YES if `Low(any candle in window) <= X`.

> Note: “touch” uses High/Low over a window. Snapshot uses Close (or a defined metric) at a specific time.

---

## 4) Your rule: BTC “Daily hit/close” (Binance 1m candle, 12:00 ET)
Below is a complete “gold standard” Market Spec for the exact rule you described.

# Market Spec (Example) — BTC Daily Snapshot (Binance 1m Close @ 12:00 ET)

## A) Identity & classification
**Market ID / Slug:** `BTC_DAILY_SNAPSHOT_BINANCE_1M_CLOSE_1200ET`  
**Market Title:** (example) “BTC daily: Above 58,000 at 12:00 ET?”  
**Market Type:**
- [x] SNAPSHOT/CLOSE

**One-liner:**  
This market resolves YES if the **Close** price of the Binance BTC/USDT **1-minute** candle starting at **12:00 ET** on the date in the title is **higher** than the threshold stated in the title.

---

## B) Resolution rule (faithful)
**Resolution Condition (faithful):**  
“This market will resolve to 'Yes' if the Binance 1 minute candle for BTC/USDT 12:00 in the ET timezone (noon) on the date specified in the title has a final 'Close' price higher than the price specified in the title. Otherwise, this market will resolve to 'No'.”

**Resolution Source (official):**  
Binance, BTC/USDT, 1m candles, Close price (per rules).

**Instrument / Pair:** BTC/USDT  
**Venue / Provider:** Binance  
**Quote Currency:** USDT  
**Base Asset:** BTC

---

## C) Time: window, timezone, expiry
**Date specified in title:** `YYYY-MM-DD`  
**Timezone (official):** `ET` (Eastern Time)  
**Snapshot candle time:** `12:00 ET` on the title date.

**Exact candle definition:**  
The 1-minute candle with start `12:00:00 ET` and end `12:00:59.999... ET`.  
**Close price** = the last price at the end of this minute.

**DST warning:**  
ET uses DST; conversion to Romania time can shift.  
We do not hardcode “Romania 19:00”. We define everything in ET and convert later.

---

## D) Price: metric, granularity, definition
**Price Metric Used:**
- [x] Close

**Granularity required:**
- 1m candles

**Exact Definition:**  
`close = ClosePrice( BinanceCandle(BTC/USDT, interval=1m, start=12:00 ET, date=YYYY-MM-DD) )`

---

## E) Binary condition (YES/NO logic)

### Variant: “Above X” (threshold market)
**YES if:** `close > threshold`  
**NO if:** `close <= threshold`

**Boundary rules:**  
Rules say “higher than”, which implies strict `>` (not `>=`).  
Therefore equality is NO.

**Rounding rules:**  
Compare the raw `close` as returned by the official Binance candle source. Do not round for logic.

---

## F) Edge Cases & Pitfalls
1. **“hit” vs “close” confusion:**  
This market is not TOUCH. A brief spike in another minute does not matter. Only Close @ 12:00 ET matters.

2. **Timezone bugs:**  
Do not treat “Romania 19:00” as a fixed rule. Always use 12:00 ET and convert.

3. **Precision:**  
Use `Decimal` (or equivalent) for comparisons, avoid float rounding errors.

4. **Missing candle:**  
If the candle is missing from the source, enforce a policy:
- retry / fallback / or mark as `UNKNOWN` and force NoTrade to output PASS.

---

## G) Data Needed (for Chapter 3)
- Market rules text (to confirm the rule)
- Threshold extracted from title/metadata
- Binance 1m candle close @ 12:00 ET for BTC/USDT

---

## H) Validation Plan
- Manual check for 3 dates: open Binance UI, find the 12:00 ET candle, confirm what the result would be.
- Check wording differences: “higher than” vs “at or above”.

---

## I) Implementation Notes
- `rule_type = SNAPSHOT_CLOSE_ABOVE`
- `source = BINANCE`
- `pair = BTCUSDT`
- `interval = 1m`
- `timezone = ET`
- `snapshot_time = 12:00`

---

## 5) Range market example (“BTC daily 56–58k YES”)
Range markets must not be assumed. The rules must specify whether boundaries are strict or inclusive.
Below is the standard spec for a **snapshot range** market.

# Market Spec (Example) — BTC Daily Snapshot Range (Close in interval @ 12:00 ET)

## A) Identity & classification
**Market ID / Slug:** `BTC_DAILY_SNAPSHOT_RANGE_BINANCE_1M_CLOSE_1200ET`  
**Market Type:**
- [x] RANGE
- [x] SNAPSHOT/CLOSE (range evaluated at snapshot)

**One-liner:**  
YES if the 1m Close @ 12:00 ET is inside `[low, high]` based on the market’s boundary rules.

---

## B) Resolution rule (to be copied from the market)
**Resolution Condition:**  
(Copy the exact wording from the market rules.)

**Resolution Source:**  
Binance BTC/USDT 1m candle Close @ 12:00 ET

---

## E) Binary condition (logic)
There are two possible interpretations; you must select the correct one from the rules:

### (1) Strict (open interval)
`YES = (low < close) AND (close < high)`

### (2) Inclusive (closed interval)
`YES = (low <= close) AND (close <= high)`

**Boundary rules:**  
- “between X and Y” can be ambiguous in natural language; the rules may clarify.
- “at least / at or above / at or below” typically indicates inclusive boundaries.

**Important note:**  
Even if equality is rare, the system must be deterministic and aligned with the rules. NoTrade does not “guess” boundaries.

---

## 6) NoTrade policy: when to output PASS due to rule uncertainty
NoTrade must be conservative when the market is ambiguous or data is not verifiable.

NoTrade outputs **PASS** if:
1. the rules do not clearly specify boundary logic and there is no safe interpretation;
2. the resolution source is vague (“multiple exchanges” without a defined method);
3. timezone or snapshot time is unclear;
4. price data cannot be obtained reliably at the required granularity;
5. there are contradictions between the title and the rules.

**Principle:** it’s better to miss a trade than to bet on a wrong contract interpretation.

---

## 7) “Market Spec quality” standard (what “good” looks like)
A Market Spec is “accepted” only if:
- it can be implemented as deterministic logic (no interpretation required);
- timezone is explicit;
- source is explicit (provider + pair + metric + granularity);
- snapshot time or time window is explicit;
- boundary rules are explicit (strict/inclusive);
- it has a minimal validation plan.

---

## 8) Quick checklist for every new market
When you see a new market, answer these before doing anything else:

1. Is it TOUCH or SNAPSHOT?  
2. What price metric is used? (Close vs High/Low)  
3. What exact time and timezone?  
4. What is the official source (venue, pair)?  
5. What is the deterministic YES/NO logic?  
6. Are boundaries strict or inclusive?  
7. What API data do we need to validate it?

---

## 9) Contract-first mindset (the golden rule)
NoTrade treats a market as a contract, not as a vibe.

**Golden rule:**  
> If the rules don’t say it, NoTrade doesn’t assume it.

---

## 10) Chapter 2 outcome
- We have a **standard Market Spec template** for any market.
- We have **internal rule types** (TOUCH vs SNAPSHOT, etc.).
- We have a complete spec for daily BTC markets: Binance 1m Close @ 12:00 ET.
- We have a clear **PASS policy** for ambiguity and unverifiable data.

Chapter 3 will implement the Data Layer:
- fetch market metadata and rules,
- extract strike/range,
- fetch the correct candle,
- feed these into the rule engine.

---

**End of Chapter 2.**
