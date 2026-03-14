# MBA-P3: SupplyZen — Supply Chain Risk Intelligence Dataset

## Problem Statement
You are the Chief Supply Chain Officer at a global consumer electronics manufacturer.
Analyse the supply chain data to identify critical risks, recommend mitigation strategies,
and build a supply chain resilience score for each supplier.

## Dataset Overview

| File | Rows | Description |
|------|------|-------------|
| supply_chain.csv | 2,000 | Component-level supply chain data |
| supplier_risk_matrix.csv | 500 | Risk scores for each supplier |
| disruption_events.csv | 50 | Historical disruption events 2020-2024 |
| inventory_levels.csv | 2,000 | Current inventory per component |

## supply_chain.csv Columns
- component_id: Unique component identifier (COMP-XXXX)
- component_type: semiconductor / display / battery_cell / connector / pcb / housing / camera_module / sensor / cable / ic_chip
- tier_level: 1 (direct supplier), 2, 3
- is_single_source: 1 = only one supplier globally, 0 = multiple sources
- critical_component: 1 = production halts if unavailable

## Key Challenges
1. Identify single-source components with high geopolitical risk
2. Quantify financial exposure from top-10 disruption scenarios
3. Build a multi-tier supplier risk heatmap
4. Recommend dual-sourcing priorities given cost constraints

## Suggested Approach
- Graph analysis of multi-tier dependencies
- Monte Carlo simulation for disruption impact
- Risk scoring: financial × geopolitical × dependency
- Optimisation: cost vs. resilience trade-off model
