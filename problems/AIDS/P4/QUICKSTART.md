# AutoTrader — Quick Start

## Objective
Train a reinforcement learning agent to dynamically manage a portfolio of 60 assets (50 stocks, 5 bond ETFs, 3 commodity ETFs, 2 crypto). The agent must achieve a Sharpe ratio > 2.0 and maximum drawdown < 15% on the 2024–2025 out-of-sample test period.

## Inputs
- `data/prices.csv` — Daily OHLCV for all 60 assets, 2010–2025, columns: `date, ticker, open, high, low, close, volume`
- `data/fundamentals.csv` — Quarterly fundamental data: `date, ticker, pe_ratio, market_cap, debt_equity`
- `data/sentiment.csv` — Daily news sentiment scores: `date, ticker, sentiment_score (-1 to 1)`
- `data/macro.csv` — Daily macroeconomic indicators: `date, gdp_growth, cpi, fed_rate, vix`
- `data/benchmark.csv` — Daily S&P 500 returns for comparison: `date, sp500_return`

## Expected Output
- `submission/trades.csv` — Columns: `date, ticker, action (buy/sell/hold), weight (0–1), portfolio_value`
- `submission/metrics.json` — Keys: `sharpe_ratio`, `max_drawdown`, `total_return`, `calmar_ratio`, `avg_turnover`

## Recommended First Steps
1. Run `python starter.py --data_dir data --output_dir submission` to verify the RL loop runs on dummy data.
2. Build the `PortfolioEnv` gym environment and sanity-check that a random-action agent produces a valid trade history.
3. Train PPO for 10,000 steps with a simple reward (daily return) before adding Sharpe and drawdown terms.

## Scoring Breakdown
| Metric                          | Weight |
|---------------------------------|--------|
| Sharpe ratio (target > 2.0)     | 40%    |
| Max drawdown control (< 15%)    | 25%    |
| Transaction cost awareness      | 20%    |
| Strategy documentation          | 15%    |

## Common Pitfalls
- Including 2024–2025 data in training (look-ahead bias) will produce unrealistically high Sharpe; strictly enforce the 2010–2023 training cutoff.
- Using raw price levels (instead of returns or log-returns) as state features causes the agent to exploit non-stationary scale differences rather than learning market dynamics.
- Ignoring transaction costs (0.1% per trade) during training results in an agent that churns the portfolio constantly; include the cost term in the reward from the first epoch.
