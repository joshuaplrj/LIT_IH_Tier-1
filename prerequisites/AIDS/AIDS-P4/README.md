# AIDS-P4: AutoTrader — Financial Market Dataset

## Overview
Historical price and technical indicator data for 60 financial assets (2010-2025).

## Asset Universe
- **50 Stocks**: Large-cap S&P 500 constituents across 10 sectors
- **5 Bond ETFs**: TLT, IEF, SHY, TIP, HYG
- **3 Commodity ETFs**: GLD, SLV, USO
- **2 Crypto**: BTC_USD, ETH_USD

## File Structure
```
AIDS-P4/
├── market_data/
│   ├── AAPL.csv
│   ├── MSFT.csv
│   ...
│   └── ETH_USD.csv
├── asset_metadata.json
└── README.md
```

## CSV Columns
| Column | Description |
|---|---|
| date | Trading date (YYYY-MM-DD) |
| open | Opening price |
| high | Daily high |
| low | Daily low |
| close | Closing price |
| volume | Trading volume |
| returns_daily | (close - prev_close) / prev_close |
| rsi_14 | 14-period Relative Strength Index |
| macd | 12-day EMA - 26-day EMA |
| ma_20 | 20-day simple moving average |
| ma_50 | 50-day simple moving average |
| volatility_20d | 20-day rolling standard deviation of returns |
| correlation_spy | 60-day rolling correlation with SPY (market) |

## Data Characteristics
- ~3,900 trading days per asset (2010-01-04 to 2025-12-31)
- GBM-based price simulation with realistic parameters
- Correlated via shared market factor
- Includes 2008-2009 crisis and 2020 COVID crash regimes
- All assets share common market beta structure

## Task Objective
Build an automated trading strategy that maximizes risk-adjusted returns (Sharpe ratio).
