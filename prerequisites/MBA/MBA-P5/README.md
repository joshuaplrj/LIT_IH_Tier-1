# MBA-P5: DealArchitect — M&A Financial Modelling Dataset

## Problem Statement
CloudStack (enterprise software, $5B revenue) is considering acquiring DataFlow Analytics
(fast-growing startup, $200M ARR). As the lead M&A analyst, build a full valuation model
and recommend a fair acquisition price range.

## Dataset Overview

| File | Rows | Description |
|------|------|-------------|
| cloudstack_financials.csv | 8 | CloudStack historical financials FY2017–FY2024 |
| dataflow_financials.csv | 5 | DataFlow Analytics financials FY2020–FY2024 |
| comparable_companies.csv | 10 | Public/private comps with trading multiples |
| precedent_transactions.csv | 5 | Recent data analytics M&A deals |
| dcf_template.csv | 12 | Pre-built DCF model with projections |

## Valuation Framework
Use three methodologies and triangulate:

### 1. Comparable Company Analysis (Comps)
- Apply EV/Revenue and EV/EBITDA multiples from comparable_companies.csv
- Adjust for DataFlow's higher growth rate (premium warranted)

### 2. Precedent Transaction Analysis (Precedents)
- Use EV/Revenue multiples from precedent_transactions.csv
- Note: M&A premiums typically 20-40% above trading comps

### 3. Discounted Cash Flow (DCF)
- Use dcf_template.csv as starting point
- Key assumptions: WACC=12%, Terminal Growth=3%, projection 10 years
- Sensitivity analysis: WACC ±2%, Terminal Growth ±1%

## Key Questions
1. What is the implied valuation range for DataFlow?
2. What synergies would CloudStack need to justify a premium?
3. Is DataFlow's 140% NDR sustainable? How does it affect LTV?
4. What integration risks exist (culture, technology, customer overlap)?
5. How does the deal affect CloudStack's leverage (Debt/EBITDA)?

## Suggested Deliverables
- Football field chart showing valuation range across methodologies
- Synergy model: revenue synergies + cost synergies over 3 years
- Pro-forma combined P&L for FY2025-FY2027
- Deal recommendation memo (buy / pass / conditional)
