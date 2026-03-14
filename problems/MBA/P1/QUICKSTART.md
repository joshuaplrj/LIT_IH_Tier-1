# MarketPivot — Quick Start

## Objective
You are the CEO of MediCore Health ($2B healthcare IT company) facing existential disruption from AI-native competitors and tech giants. Develop a credible 3-year strategic transformation plan that preserves company value while navigating the transition to an AI-first healthcare technology model.

## Inputs
- **Company financials**: Revenue $2B (declining 5% YoY), EBITDA 18%, $500M cash, $800M debt maturing in 3 years, R&D $160M/year
- **Revenue breakdown**: EHR software 60% ($1.2B), medical billing 25% ($500M), telehealth 15% ($300M)
- **Competitive threats**: AI-native EHR startups (1/10th cost), Google Health, Microsoft/Nuance, Amazon Clinic
- **Customer health signals**: Churn up from 5% to 15%, NPS dropped from +45 to +12
- **Regulatory context**: CMS interoperability mandates (API opening commoditizes data moat)
- **Strategic options**: Build (in-house AI), Buy (AI startup acquisition), Partner (tech alliance), Pivot (platform company)

## Expected Output
A structured JSON submission file with the following top-level sections:
```
submission.json
├── strategic_analysis      (options scoring, SWOT, competitive landscape)
├── recommended_strategy    (chosen option with rationale and trade-offs)
├── gtm_transformation      (licensing-to-SaaS transition, pricing, retention plan)
├── financial_plan          (3-year P&L, capital allocation, break-even analysis)
├── org_transformation      (talent plan, cultural change roadmap)
└── risk_analysis           (key risks, mitigation plans, contingency scenarios)
```
Each section must include quantitative metrics and narrative justification.

## Recommended First Steps
1. Use `starter.py` to generate baseline financial scenarios — run `python starter.py --output analysis.json` to see the pre-populated model skeleton with MediCore's current numbers
2. Score each strategic option (Build / Buy / Partner / Pivot) using the weighted criteria matrix in `starter.py`; fill in your scores and rationale
3. Build the 3-year P&L for your chosen strategy — model at least two scenarios (base case and downside) using the scenario skeleton provided

## Scoring Breakdown
| Metric | Weight |
|---|---|
| Strategic Clarity (clear recommendation + trade-off analysis) | 30% |
| Competitive Analysis (Porter's 5 Forces or equivalent depth) | 25% |
| Financial Model (3-year P&L, capital allocation, break-even) | 25% |
| Feasibility (org readiness, timeline realism, risk mitigation) | 20% |

## Common Pitfalls
- Recommending "all four options simultaneously" without prioritization — judges want a clear, defensible choice
- Building a financial model that ignores the $800M debt maturity — this is a critical constraint, not a footnote
- Confusing strategy with tactics — the 3-year roadmap must show stage-gated milestones, not just a wish list
- Underestimating churn acceleration — a 15% annual churn rate means ~40% of the customer base turns over in 3 years; the model must reflect this
- Ignoring the regulatory angle — CMS interoperability mandates are both a threat (data moat erosion) and an opportunity (partner ecosystem)
