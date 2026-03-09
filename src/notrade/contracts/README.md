# NoTrade Runtime Contracts

This folder contains the executable Stage 1 contracts that turn the architecture docs into machine-readable runtime objects.

## Model roles
- `MarketDefinition`: static identity + resolution rule for one market.
- `MarketSnapshot`: live decision-time quote state for that market.
- `MarketContext`: composed object consumed by the decision engine.
- `DataIntegritySnapshot`: whether the decision-time data is trustworthy enough to act.
- `ProbabilitySnapshot`: calibrated probability-layer output.
- `OpenPosition`: normalized representation of one active YES/NO thesis.
- `PortfolioState`: portfolio snapshot + cooldown guard state.
- `DecisionOutput`: policy verdict (`PASS`, `ENTER`, `HOLD`, `EXIT`) plus minimal execution intent.
- `FillEvent`: realized or simulated fill event for accounting / ledger reconstruction.

## Flow
1. Build `MarketDefinition` from market metadata.
2. Build `MarketSnapshot` from live quotes.
3. Combine them into `MarketContext`.
4. Gate data quality with `DataIntegritySnapshot`.
5. Generate calibrated probabilities with `ProbabilitySnapshot`.
6. Feed `MarketContext + DataIntegritySnapshot + ProbabilitySnapshot + PortfolioState` into the Stage 2 decision engine.
7. Emit `DecisionOutput`.
8. Convert any realized execution into `FillEvent` records and rebuild `OpenPosition` / `PortfolioState` over time.

## Semantic notes
- `market_prob_yes` / `market_prob_no` are executable entry prices, not midpoint complements.
- `EXIT` means full flatten of `target_position_id`.
- Cooldown is a portfolio guard, not a thesis state.
