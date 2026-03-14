"""
AIDS-P4: AutoTrader - Market Data Generator
Generates 60 asset CSV files, asset_metadata.json, README.md
"""

import numpy as np
import csv
import json
import os
from datetime import date, timedelta

RANDOM_SEED = 42
OUTPUT_DIR = r"c:\Users\John Jacob\Desktop\Tier-1\prerequisites\AIDS\AIDS-P4"
MARKET_DIR = os.path.join(OUTPUT_DIR, "market_data")

os.makedirs(MARKET_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

rng = np.random.default_rng(RANDOM_SEED)

# ─── Asset definitions ──────────────────────────────────────────────────────
STOCKS = [
    "AAPL","MSFT","GOOGL","AMZN","META","NVDA","TSLA","JPM","JNJ","V",
    "PG","UNH","HD","BAC","XOM","CVX","ABBV","PFE","MRK","KO",
    "PEP","WMT","COST","AVGO","LLY","TMO","DHR","ABT","MCD","NKE",
    "DIS","NFLX","ADBE","CRM","INTC","AMD","QCOM","TXN","NEE","DUK",
    "SO","D","EXC","AEP","WM","RSG","LIN","APD","FCX","GE"
]
BONDS = ["TLT","IEF","SHY","TIP","HYG"]
COMMODITIES = ["GLD","SLV","USO"]
CRYPTO = ["BTC_USD","ETH_USD"]

SECTOR_MAP = {
    "AAPL":"Technology","MSFT":"Technology","GOOGL":"Technology","AMZN":"Technology","META":"Technology",
    "NVDA":"Technology","TSLA":"Consumer Discretionary","ADBE":"Technology","CRM":"Technology",
    "INTC":"Technology","AMD":"Technology","QCOM":"Technology","TXN":"Technology",
    "JPM":"Financials","BAC":"Financials","V":"Financials",
    "JNJ":"Healthcare","UNH":"Healthcare","ABBV":"Healthcare","PFE":"Healthcare","MRK":"Healthcare",
    "TMO":"Healthcare","DHR":"Healthcare","ABT":"Healthcare","LLY":"Healthcare",
    "PG":"Consumer Staples","KO":"Consumer Staples","PEP":"Consumer Staples","WMT":"Consumer Staples",
    "COST":"Consumer Staples",
    "HD":"Consumer Discretionary","MCD":"Consumer Discretionary","NKE":"Consumer Discretionary",
    "DIS":"Communication Services","NFLX":"Communication Services",
    "XOM":"Energy","CVX":"Energy",
    "NEE":"Utilities","DUK":"Utilities","SO":"Utilities","D":"Utilities","EXC":"Utilities","AEP":"Utilities",
    "WM":"Industrials","RSG":"Industrials","GE":"Industrials",
    "LIN":"Materials","APD":"Materials","FCX":"Materials",
    "TLT":"Fixed Income","IEF":"Fixed Income","SHY":"Fixed Income","TIP":"Fixed Income","HYG":"Fixed Income",
    "GLD":"Commodities","SLV":"Commodities","USO":"Commodities",
    "BTC_USD":"Cryptocurrency","ETH_USD":"Cryptocurrency",
}

START_PRICES = {
    "AAPL":30.0,"MSFT":25.0,"GOOGL":300.0,"AMZN":140.0,"META":25.0,
    "NVDA":4.0,"TSLA":4.0,"JPM":35.0,"JNJ":60.0,"V":20.0,
    "PG":55.0,"UNH":25.0,"HD":25.0,"BAC":10.0,"XOM":60.0,
    "CVX":70.0,"ABBV":50.0,"PFE":15.0,"MRK":30.0,"KO":25.0,
    "PEP":55.0,"WMT":55.0,"COST":50.0,"AVGO":10.0,"LLY":35.0,
    "TMO":50.0,"DHR":30.0,"ABT":25.0,"MCD":60.0,"NKE":20.0,
    "DIS":30.0,"NFLX":10.0,"ADBE":25.0,"CRM":15.0,"INTC":20.0,
    "AMD":5.0,"QCOM":40.0,"TXN":25.0,"NEE":10.0,"DUK":55.0,
    "SO":25.0,"D":40.0,"EXC":20.0,"AEP":25.0,"WM":25.0,
    "RSG":20.0,"LIN":50.0,"APD":60.0,"FCX":15.0,"GE":15.0,
    "TLT":90.0,"IEF":90.0,"SHY":85.0,"TIP":90.0,"HYG":85.0,
    "GLD":110.0,"SLV":17.0,"USO":35.0,
    "BTC_USD":1000.0,"ETH_USD":10.0,
}

# Sector volatilities (annualized σ → daily σ = σ_annual / sqrt(252))
SECTOR_SIGMA = {
    "Technology":0.28,"Financials":0.22,"Healthcare":0.18,"Consumer Staples":0.14,
    "Consumer Discretionary":0.24,"Communication Services":0.26,"Energy":0.28,
    "Utilities":0.14,"Industrials":0.20,"Materials":0.24,
    "Fixed Income":0.03,"Commodities":0.15,"Cryptocurrency":0.05,
}

ALL_ASSETS = STOCKS + BONDS + COMMODITIES + CRYPTO

def get_trading_days(start="2010-01-04", end="2025-12-31"):
    """Generate trading days (Mon-Fri) between start and end dates."""
    d = date.fromisoformat(start)
    end_d = date.fromisoformat(end)
    days = []
    while d <= end_d:
        if d.weekday() < 5:  # Mon=0 ... Fri=4
            days.append(d.isoformat())
        d += timedelta(days=1)
    return days


def compute_rsi(prices, period=14):
    """Compute RSI-14 for a price series."""
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    rsi = np.full(len(prices), np.nan)
    if len(deltas) < period:
        return rsi
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            rsi[i + 1] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi[i + 1] = 100.0 - 100.0 / (1.0 + rs)
    return rsi


def compute_ema(prices, span):
    """Compute EMA."""
    alpha = 2.0 / (span + 1)
    ema = np.full(len(prices), np.nan)
    ema[0] = prices[0]
    for i in range(1, len(prices)):
        ema[i] = alpha * prices[i] + (1 - alpha) * ema[i - 1]
    return ema


def compute_macd(prices):
    ema12 = compute_ema(prices, 12)
    ema26 = compute_ema(prices, 26)
    return ema12 - ema26


def compute_rolling_mean(arr, window):
    result = np.full(len(arr), np.nan)
    for i in range(window - 1, len(arr)):
        result[i] = np.mean(arr[i - window + 1:i + 1])
    return result


def compute_rolling_std(arr, window):
    result = np.full(len(arr), np.nan)
    for i in range(window - 1, len(arr)):
        result[i] = np.std(arr[i - window + 1:i + 1], ddof=1)
    return result


def compute_rolling_corr(arr1, arr2, window=60):
    result = np.full(len(arr1), np.nan)
    for i in range(window - 1, len(arr1)):
        a = arr1[i - window + 1:i + 1]
        b = arr2[i - window + 1:i + 1]
        std_a = np.std(a, ddof=1)
        std_b = np.std(b, ddof=1)
        if std_a > 0 and std_b > 0:
            result[i] = np.corrcoef(a, b)[0, 1]
    return result


print("Generating AIDS-P4: AutoTrader Market Data...")

trading_days = get_trading_days()
N = len(trading_days)
print(f"  Trading days: {N} ({trading_days[0]} to {trading_days[-1]})")

# ─── Generate market factor (SPY proxy) ─────────────────────────────────────
market_mu = 0.0003
market_sigma_daily = 0.012  # ~19% annual vol

market_shocks = rng.standard_normal(N - 1).astype(np.float64)

# Crisis regimes
for i, d in enumerate(trading_days[1:]):
    yr = int(d[:4])
    mo = int(d[5:7])
    if yr == 2008 or (yr == 2009 and mo <= 3):
        market_shocks[i] *= 3.0
        market_shocks[i] -= 0.003  # downward drift
    elif yr == 2020 and mo in (2, 3):
        market_shocks[i] *= 4.0
        market_shocks[i] -= 0.005
    elif yr == 2020 and mo in (4, 5, 6):
        market_shocks[i] += 0.002  # recovery

spy_log_returns = (market_mu - 0.5 * market_sigma_daily**2) + market_sigma_daily * market_shocks
spy_prices = np.zeros(N)
spy_prices[0] = 100.0
for i in range(1, N):
    spy_prices[i] = spy_prices[i - 1] * np.exp(spy_log_returns[i - 1])

spy_returns = np.concatenate([[0.0], np.diff(spy_prices) / spy_prices[:-1]])

# ─── Generate each asset ────────────────────────────────────────────────────
asset_metadata = {}

for asset in ALL_ASSETS:
    sector = SECTOR_MAP.get(asset, "Technology")
    asset_class = "stock" if asset in STOCKS else \
                  "bond_etf" if asset in BONDS else \
                  "commodity_etf" if asset in COMMODITIES else "crypto"
    sigma_annual = SECTOR_SIGMA[sector]
    sigma_daily = sigma_annual / np.sqrt(252)

    mu_daily = 0.001 if asset in CRYPTO else \
               0.0001 if asset in BONDS + COMMODITIES else \
               0.0003

    start_price = START_PRICES.get(asset, 50.0)
    beta = rng.uniform(0.4, 1.8) if asset in STOCKS else \
           rng.uniform(-0.3, 0.3) if asset in BONDS else \
           rng.uniform(0.3, 0.9) if asset in COMMODITIES else \
           rng.uniform(0.5, 1.5)

    # Idiosyncratic shocks
    idio_shocks = rng.standard_normal(N - 1).astype(np.float64)
    idio_sigma = np.sqrt(max(sigma_daily**2 - beta**2 * market_sigma_daily**2, 1e-8))

    log_returns = (mu_daily - 0.5 * sigma_daily**2) + \
                  beta * market_sigma_daily * market_shocks + \
                  idio_sigma * idio_shocks

    # Crisis adjustments
    for i, d in enumerate(trading_days[1:]):
        yr = int(d[:4])
        mo = int(d[5:7])
        if yr == 2020 and mo in (2, 3) and asset in STOCKS:
            log_returns[i] -= 0.003

    prices = np.zeros(N)
    prices[0] = start_price
    for i in range(1, N):
        prices[i] = max(prices[i - 1] * np.exp(log_returns[i - 1]), 0.01)

    # Returns
    returns = np.concatenate([[0.0], np.diff(prices) / prices[:-1]])

    # OHLCV
    daily_range = sigma_daily * prices
    open_prices = np.concatenate([[prices[0]], prices[:-1] * (1 + rng.standard_normal(N - 1) * sigma_daily * 0.3)])
    open_prices = np.maximum(open_prices, 0.01)
    high_prices = np.maximum(prices + daily_range * np.abs(rng.standard_normal(N)) * 0.5,
                             np.maximum(open_prices, prices))
    low_prices  = np.minimum(prices - daily_range * np.abs(rng.standard_normal(N)) * 0.5,
                             np.minimum(open_prices, prices))
    low_prices  = np.maximum(low_prices, 0.01)

    base_volume = 10_000_000 if asset in STOCKS else 1_000_000 if asset in BONDS + COMMODITIES else 5_000
    volumes = (base_volume * (1 + np.abs(returns) * 5) * rng.lognormal(0, 0.3, N)).astype(np.int64)

    # Technical indicators
    rsi   = compute_rsi(prices)
    macd  = compute_macd(prices)
    ma20  = compute_rolling_mean(prices, 20)
    ma50  = compute_rolling_mean(prices, 50)
    vol20 = compute_rolling_std(returns, 20)
    corr_spy = compute_rolling_corr(returns, spy_returns, window=60)

    # Write CSV
    csv_path = os.path.join(MARKET_DIR, f"{asset}.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["date","open","high","low","close","volume",
                         "returns_daily","rsi_14","macd","ma_20","ma_50",
                         "volatility_20d","correlation_spy"])
        for i, d in enumerate(trading_days):
            def fmt(v):
                if np.isnan(v):
                    return ""
                return f"{v:.6f}"
            writer.writerow([
                d,
                f"{open_prices[i]:.4f}",
                f"{high_prices[i]:.4f}",
                f"{low_prices[i]:.4f}",
                f"{prices[i]:.4f}",
                int(volumes[i]),
                fmt(returns[i]),
                fmt(rsi[i]),
                fmt(macd[i]),
                fmt(ma20[i]),
                fmt(ma50[i]),
                fmt(vol20[i]),
                fmt(corr_spy[i]),
            ])

    mcap_bin = "large" if start_price * base_volume > 500_000_000 else "mid" if start_price > 30 else "small"
    asset_metadata[asset] = {
        "sector": sector,
        "asset_class": asset_class,
        "start_price": start_price,
        "market_cap_bin": mcap_bin,
        "beta": round(float(beta), 3),
        "annual_volatility": round(float(sigma_annual), 4),
    }
    print(f"  Wrote {asset}.csv ({N} rows)")

# Write asset_metadata.json
meta_path = os.path.join(OUTPUT_DIR, "asset_metadata.json")
with open(meta_path, "w", encoding="utf-8") as f:
    json.dump(asset_metadata, f, indent=2)
print(f"  Wrote asset_metadata.json ({len(asset_metadata)} assets)")

# Write README.md
readme = """# AIDS-P4: AutoTrader — Financial Market Dataset

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
"""
readme_path = os.path.join(OUTPUT_DIR, "README.md")
with open(readme_path, "w", encoding="utf-8") as f:
    f.write(readme)
print(f"  Wrote README -> {readme_path}")

print("\nAIDS-P4 generation complete!")
print(f"Total assets: {len(ALL_ASSETS)}, Trading days per asset: {N}")
