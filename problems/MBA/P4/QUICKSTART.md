# LaunchPad — Quick Start

## Objective
You are the VP of Marketing at QuantumLeap, an early-stage B2B deep-tech startup with a quantum-inspired optimisation engine, $50K ARR, and 18 months of runway. Design a credible go-to-market strategy to reach the ARR threshold required to raise a Series B from a standing start.

## Inputs
No external data files for this problem — all inputs are embedded in the problem statement and starter.py. Key parameters:

- **Company**: QuantumLeap, quantum-inspired VRP/facility/supply chain optimisation, API-first SaaS
- **Pricing**: Usage-based, $0.01 per optimisation call
- **Current state**: 5 paying customers, $50K ARR, 20 employees (10 eng / 3 sales / 2 marketing), $15M Series A
- **Funding runway**: 18 months to Series B raise
- **Target market**: VP Supply Chain / VP Operations at Fortune 500 companies
- **TAM**: $15B (optimisation software market)
- **Competitors**: Gurobi, CPLEX (classical), D-Wave/Rigetti (quantum), Google OR-Tools (open-source)
- **Sales cycle**: 6–18 months; ACV target: depends on usage volume
- **Marketing budget**: $500K for 18 months

## Expected Output
A structured JSON file (`submission.json`) with:
```
submission.json
├── market_sizing         (TAM, SAM, SOM with methodology and sources)
├── gtm_strategy          (positioning, ICP, channel mix, sales methodology)
├── channel_strategy      (direct sales vs. PLG vs. partners — allocation and rationale)
├── financial_projections (ARR model, CAC/LTV analysis, 18-month funnel)
└── action_plan_90_days   (week-by-week priorities for first 90 days)
```

## Recommended First Steps
1. Run `python starter.py --output analysis.json` to generate the baseline TAM/SAM/SOM calculator, CAC/LTV model, and sales funnel projection with placeholder values
2. Start with market sizing — work top-down (TAM → SAM → SOM) and bottom-up (target accounts × ACV): do both and reconcile; the bottom-up number is your 18-month target
3. Calculate the Series B threshold: deep-tech B2B SaaS companies typically need $5–15M ARR and 100%+ YoY growth — reverse-engineer your required deal volume, deal size, and win rate from this target

## Scoring Breakdown
| Metric | Weight |
|---|---|
| Market Sizing (TAM/SAM/SOM with documented methodology, both top-down and bottom-up) | 25% |
| GTM Strategy (positioning, ICP definition, sales methodology, playbook quality) | 30% |
| Channel Strategy (budget allocation by channel with ROI rationale) | 20% |
| Financial Projections (ARR model, CAC/LTV, funnel conversion rates, Series B target) | 25% |

## Common Pitfalls
- Using the full $15B TAM as your target — judges will penalise unrealistic market capture; SOM should reflect 18-month reachable revenue, not total market size
- Ignoring the 6–18 month sales cycle when modelling ARR — deals started in Month 1 may not close until Month 12; build a pipeline-based model, not a steady-state one
- Positioning as "quantum computing" (which requires specialised hardware) rather than "quantum-inspired" (runs on classical hardware) — this is a critical messaging distinction
- Forgetting the competitive moat question — why can't a Fortune 500 customer just use Google OR-Tools (free)?
- Allocating the entire $500K budget to digital marketing for a product with a 12-month enterprise sales cycle
