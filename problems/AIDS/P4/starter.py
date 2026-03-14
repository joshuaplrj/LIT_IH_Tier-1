"""
AIDS-P4: AutoTrader — Reinforcement Learning for Portfolio Management
Starter skeleton. Run as-is to verify the RL loop executes end-to-end
on randomly generated dummy market data.

Usage:
    python starter.py --data_dir data --output_dir submission
"""

import argparse
import csv
import json
import os
import random
import warnings
from pathlib import Path

import numpy as np

warnings.filterwarnings("ignore")

# Optional RL / finance imports ---------------------------------------------
try:
    import gym
    from gym import spaces
    GYM_AVAILABLE = True
except ImportError:
    GYM_AVAILABLE = False
    print("[WARN] gym not found — using simplified environment stub.")

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("[WARN] pandas not found — using numpy-only data pipeline.")

try:
    from stable_baselines3 import PPO
    from stable_baselines3.common.env_checker import check_env
    SB3_AVAILABLE = True
except ImportError:
    SB3_AVAILABLE = False
    print("[WARN] stable-baselines3 not found — using random policy.")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
N_ASSETS = 60           # 50 stocks + 5 bonds + 3 commodities + 2 crypto
N_FEATURES = 8          # per-asset feature count
LOOKBACK = 20           # trading days of history in state
TRAIN_START = "2010-01-01"
TRAIN_END = "2023-12-31"
TEST_START = "2024-01-01"
TEST_END = "2025-12-31"
TRANSACTION_COST = 0.001   # 0.1% per trade (fractional per unit weight change)
MAX_WEIGHT = 0.20          # no single asset > 20%
MIN_CASH = 0.05            # minimum 5% cash reserve
INITIAL_CAPITAL = 1_000_000.0
N_TRAIN_STEPS = 50_000     # increase to 500_000 for serious training


# ---------------------------------------------------------------------------
# Data loading and feature engineering
# ---------------------------------------------------------------------------

def generate_dummy_prices(n_assets: int = N_ASSETS,
                          n_days: int = 3500) -> np.ndarray:
    """Generate synthetic daily log-returns, shape (n_days, n_assets)."""
    mu = np.random.uniform(0.0001, 0.0005, n_assets)
    sigma = np.random.uniform(0.01, 0.03, n_assets)
    returns = np.random.normal(mu, sigma, size=(n_days, n_assets)).astype(np.float32)
    return returns


def load_prices(data_dir: str) -> tuple:
    """
    Load prices.csv and return (returns_array, dates, tickers).
    Returns shape: returns (n_days, n_assets).
    Falls back to dummy data if file absent.
    """
    path = Path(data_dir) / "prices.csv"
    if not path.exists() or not PANDAS_AVAILABLE:
        print("[INFO] Using dummy price data.")
        n_days = 3500
        returns = generate_dummy_prices(N_ASSETS, n_days)
        import datetime
        start = datetime.date(2010, 1, 1)
        dates = [(start + datetime.timedelta(days=i)).isoformat()
                 for i in range(n_days)]
        tickers = [f"ASSET_{i:02d}" for i in range(N_ASSETS)]
        return returns, dates, tickers

    df = pd.read_csv(path, parse_dates=["date"])
    df = df.sort_values(["date", "ticker"])
    tickers = df["ticker"].unique().tolist()
    pivoted = df.pivot(index="date", columns="ticker", values="close")
    pivoted = pivoted.sort_index().ffill().dropna()
    log_returns = np.log(pivoted / pivoted.shift(1)).dropna()
    dates = log_returns.index.strftime("%Y-%m-%d").tolist()
    returns = log_returns.values.astype(np.float32)
    return returns, dates, tickers


def load_sentiment(data_dir: str, n_days: int, n_assets: int) -> np.ndarray:
    """Load or synthesise daily sentiment scores, shape (n_days, n_assets)."""
    path = Path(data_dir) / "sentiment.csv"
    if not path.exists() or not PANDAS_AVAILABLE:
        return np.random.uniform(-1, 1, (n_days, n_assets)).astype(np.float32)
    df = pd.read_csv(path, parse_dates=["date"])
    # TODO: pivot and align with returns DataFrame
    return np.random.uniform(-1, 1, (n_days, n_assets)).astype(np.float32)


def build_features(returns: np.ndarray,
                   sentiment: np.ndarray) -> np.ndarray:
    """
    Construct feature matrix of shape (n_days, n_assets, N_FEATURES).
    Features per asset: [ret_1d, ret_5d, ret_20d, vol_20d,
                         rsi_14, momentum_20, sentiment, rolling_z]
    """
    n_days, n_assets = returns.shape
    features = np.zeros((n_days, n_assets, N_FEATURES), dtype=np.float32)

    for t in range(20, n_days):
        window = returns[max(0, t - 20):t + 1]
        features[t, :, 0] = returns[t]                        # 1-day return
        features[t, :, 1] = returns[max(0, t - 5):t].sum(0)  # 5-day return
        features[t, :, 2] = window.sum(0)                     # 20-day return
        features[t, :, 3] = window.std(0)                     # 20-day vol
        # RSI-14 (simplified)
        up = np.maximum(returns[max(0, t - 14):t], 0).mean(0)
        dn = np.maximum(-returns[max(0, t - 14):t], 0).mean(0)
        rs = up / (dn + 1e-9)
        features[t, :, 4] = 1 - 1 / (1 + rs)                 # RSI normalised
        features[t, :, 5] = returns[max(0, t - 20):t].mean(0) # momentum
        features[t, :, 6] = sentiment[t]                      # sentiment
        # Rolling z-score of 1-day return
        mu = returns[max(0, t - 20):t].mean(0)
        std = returns[max(0, t - 20):t].std(0) + 1e-9
        features[t, :, 7] = (returns[t] - mu) / std

    return features


# ---------------------------------------------------------------------------
# Portfolio environment
# ---------------------------------------------------------------------------

if GYM_AVAILABLE:
    class PortfolioEnv(gym.Env):
        """
        Custom OpenAI Gym environment for portfolio management.
        State:  (N_ASSETS, N_FEATURES, LOOKBACK) feature cube
        Action: portfolio weight vector (N_ASSETS,) — normalised to sum <= 0.95
        """
        metadata = {"render_modes": []}

        def __init__(self, features: np.ndarray, returns: np.ndarray,
                     tickers: list, dates: list,
                     initial_capital: float = INITIAL_CAPITAL):
            super().__init__()
            self.features = features   # (n_days, n_assets, n_feat)
            self.returns = returns     # (n_days, n_assets)
            self.tickers = tickers
            self.dates = dates
            self.n_days, self.n_assets, _ = features.shape
            self.initial_capital = initial_capital

            self.observation_space = spaces.Box(
                low=-10.0, high=10.0,
                shape=(self.n_assets, N_FEATURES, LOOKBACK),
                dtype=np.float32,
            )
            self.action_space = spaces.Box(
                low=0.0, high=1.0,
                shape=(self.n_assets,),
                dtype=np.float32,
            )
            self.reset()

        def reset(self, seed=None, options=None):
            self.t = LOOKBACK
            self.portfolio_value = self.initial_capital
            self.peak_value = self.initial_capital
            self.weights = np.ones(self.n_assets, dtype=np.float32) / self.n_assets
            self.trade_log = []
            obs = self._get_obs()
            return obs, {}

        def _get_obs(self):
            """Return feature cube for last LOOKBACK days."""
            # Shape: (n_assets, n_features, lookback)
            window = self.features[self.t - LOOKBACK:self.t]  # (lookback, n_a, n_f)
            obs = window.transpose(1, 2, 0)                   # (n_a, n_f, lookback)
            return obs.astype(np.float32)

        def _normalise_weights(self, raw_weights: np.ndarray) -> np.ndarray:
            """Clip to max weight, ensure minimum cash reserve."""
            w = np.clip(raw_weights, 0, MAX_WEIGHT)
            total = w.sum()
            if total > (1 - MIN_CASH):
                w = w * (1 - MIN_CASH) / (total + 1e-9)
            return w

        def step(self, action: np.ndarray):
            new_weights = self._normalise_weights(action)
            # Transaction cost
            weight_change = np.abs(new_weights - self.weights).sum()
            tc = TRANSACTION_COST * weight_change * self.portfolio_value

            # Portfolio return
            day_returns = self.returns[self.t]
            port_return = float(np.dot(new_weights, day_returns))
            new_value = self.portfolio_value * (1 + port_return) - tc

            # Drawdown
            self.peak_value = max(self.peak_value, new_value)
            drawdown = (self.peak_value - new_value) / (self.peak_value + 1e-9)

            # Reward: risk-adjusted return minus drawdown penalty
            reward = port_return - tc / (self.portfolio_value + 1e-9)
            if drawdown > 0.10:
                reward -= 0.1 * drawdown

            # Log trade
            self.trade_log.append({
                "date": self.dates[self.t] if self.t < len(self.dates) else str(self.t),
                "portfolio_value": round(new_value, 2),
                "drawdown": round(drawdown, 4),
            })

            self.weights = new_weights
            self.portfolio_value = max(new_value, 1.0)  # floor at $1
            self.t += 1

            done = self.t >= self.n_days - 1
            obs = self._get_obs() if not done else np.zeros(
                self.observation_space.shape, dtype=np.float32)
            return obs, float(reward), done, False, {}

        def render(self):
            print(f"  t={self.t} | value=${self.portfolio_value:,.0f}")

else:
    # Minimal stub when gym is not available
    class PortfolioEnv:
        def __init__(self, features, returns, tickers, dates,
                     initial_capital=INITIAL_CAPITAL):
            self.n_days = len(dates)
            self.n_assets = returns.shape[1]
            self.returns = returns
            self.dates = dates
            self.tickers = tickers
            self.t = LOOKBACK
            self.portfolio_value = initial_capital
            self.peak_value = initial_capital
            self.weights = np.ones(self.n_assets) / self.n_assets
            self.trade_log = []

        def reset(self):
            self.t = LOOKBACK
            self.portfolio_value = INITIAL_CAPITAL
            self.peak_value = INITIAL_CAPITAL
            self.weights = np.ones(self.n_assets) / self.n_assets
            self.trade_log = []

        def step(self, action):
            w = np.clip(action, 0, MAX_WEIGHT)
            w = w / (w.sum() + 1e-9) * (1 - MIN_CASH)
            day_return = float(np.dot(w, self.returns[self.t]))
            self.portfolio_value *= (1 + day_return)
            self.peak_value = max(self.peak_value, self.portfolio_value)
            dd = (self.peak_value - self.portfolio_value) / (self.peak_value + 1e-9)
            self.trade_log.append({
                "date": self.dates[self.t] if self.t < len(self.dates) else str(self.t),
                "portfolio_value": round(self.portfolio_value, 2),
                "drawdown": round(dd, 4),
            })
            self.t += 1
            return None, day_return, self.t >= self.n_days - 1, {}


# ---------------------------------------------------------------------------
# Training and backtesting
# ---------------------------------------------------------------------------

def train_agent(env, n_steps: int = N_TRAIN_STEPS):
    """Train PPO agent. Falls back to random policy if SB3 absent."""
    if SB3_AVAILABLE and GYM_AVAILABLE:
        print(f"[INFO] Training PPO for {n_steps} steps...")
        model = PPO("MlpPolicy", env,
                    n_steps=2048, batch_size=64,
                    n_epochs=10, learning_rate=3e-4,
                    verbose=0)
        model.learn(total_timesteps=n_steps)
        return model
    else:
        print("[INFO] SB3 not available — using random policy agent.")
        return None


def run_backtest(model, env, tickers: list) -> list:
    """
    Run trained policy on environment. Returns list of trade records.
    Each record: {date, ticker, action, weight, portfolio_value}
    """
    if GYM_AVAILABLE:
        obs, _ = env.reset()
    else:
        env.reset()
        obs = None

    trades = []
    done = False
    while not done:
        if model is not None and SB3_AVAILABLE:
            action, _ = model.predict(obs, deterministic=True)
        else:
            action = np.random.dirichlet(np.ones(env.n_assets)).astype(np.float32)

        if GYM_AVAILABLE:
            obs, reward, done, _, info = env.step(action)
        else:
            obs, reward, done, info = env.step(action)

        if env.trade_log:
            last = env.trade_log[-1]
            for i, ticker in enumerate(tickers):
                trades.append({
                    "date": last["date"],
                    "ticker": ticker,
                    "action": "hold",   # TODO: derive from weight changes
                    "weight": round(float(action[i]), 4),
                    "portfolio_value": last["portfolio_value"],
                })
    return trades


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def compute_portfolio_metrics(trades: list) -> dict:
    """Compute Sharpe ratio, max drawdown, total return, Calmar ratio."""
    if not trades:
        return {"sharpe_ratio": 0.0, "max_drawdown": 1.0,
                "total_return": 0.0, "calmar_ratio": 0.0, "avg_turnover": 0.0}

    # Extract portfolio values by date (one row per date, any ticker)
    dates_seen = {}
    for t in trades:
        dates_seen[t["date"]] = t["portfolio_value"]
    sorted_dates = sorted(dates_seen)
    values = np.array([dates_seen[d] for d in sorted_dates], dtype=np.float64)

    daily_returns = np.diff(values) / (values[:-1] + 1e-9)
    total_return = float((values[-1] - values[0]) / (values[0] + 1e-9))
    sharpe = float(daily_returns.mean() / (daily_returns.std() + 1e-9) * np.sqrt(252))

    # Max drawdown
    peak = values[0]
    max_dd = 0.0
    for v in values:
        peak = max(peak, v)
        dd = (peak - v) / (peak + 1e-9)
        max_dd = max(max_dd, dd)

    n_years = max(len(sorted_dates) / 252, 1e-6)
    annualised_return = (1 + total_return) ** (1 / n_years) - 1
    calmar = float(annualised_return / (max_dd + 1e-9))

    # Average daily turnover (mean absolute weight change)
    # TODO: compute properly from weight time series
    avg_turnover = float(np.random.uniform(0.02, 0.10))

    return {
        "sharpe_ratio": round(sharpe, 4),
        "max_drawdown": round(float(max_dd), 4),
        "total_return": round(total_return, 4),
        "calmar_ratio": round(calmar, 4),
        "avg_turnover": round(avg_turnover, 4),
    }


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def save_trades(trades: list, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, "trades.csv")
    if not trades:
        return
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["date", "ticker", "action", "weight", "portfolio_value"])
        writer.writeheader()
        writer.writerows(trades)
    print(f"[OUT] Trades saved to {path}")


def save_metrics(metrics: dict, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, "metrics.json")
    with open(path, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"[OUT] Metrics saved to {path}")


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="AIDS-P4 AutoTrader pipeline")
    parser.add_argument("--data_dir", type=str, default="data",
                        help="Directory containing prices.csv, sentiment.csv, etc.")
    parser.add_argument("--output_dir", type=str, default="submission")
    parser.add_argument("--n_steps", type=int, default=N_TRAIN_STEPS,
                        help="RL training steps")
    parser.add_argument("--device", type=str, default="cpu")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    print("=" * 60)
    print("AIDS-P4: AutoTrader — RL Portfolio Management")
    print("=" * 60)

    # --- Load data ---
    print("\n[1/5] Loading market data...")
    returns, dates, tickers = load_prices(args.data_dir)
    n_days = len(dates)
    print(f"  {n_days} trading days | {len(tickers)} assets")

    sentiment = load_sentiment(args.data_dir, n_days, len(tickers))

    # --- Build features ---
    print("\n[2/5] Engineering features...")
    features = build_features(returns, sentiment)

    # --- Split train / test ---
    train_mask = np.array([d <= TRAIN_END for d in dates])
    test_mask = np.array([d >= TEST_START for d in dates])
    train_features = features[train_mask]
    train_returns = returns[train_mask]
    train_dates = [d for d, m in zip(dates, train_mask) if m]
    test_features = features[test_mask]
    test_returns = returns[test_mask]
    test_dates = [d for d, m in zip(dates, test_mask) if m]
    print(f"  Train: {len(train_dates)} days | Test: {len(test_dates)} days")

    # --- Build training environment ---
    print("\n[3/5] Building RL environment and training agent...")
    train_env = PortfolioEnv(train_features, train_returns, tickers, train_dates)
    model = train_agent(train_env, n_steps=args.n_steps)

    # --- Backtest on test period ---
    print("\n[4/5] Running backtest on 2024–2025 test period...")
    test_env = PortfolioEnv(test_features, test_returns, tickers, test_dates)
    trades = run_backtest(model, test_env, tickers)
    save_trades(trades, args.output_dir)

    # --- Compute and save metrics ---
    print("\n[5/5] Computing portfolio metrics...")
    metrics = compute_portfolio_metrics(trades)
    save_metrics(metrics, args.output_dir)
    print(f"\n  Sharpe Ratio:  {metrics['sharpe_ratio']:.3f}  (target > 2.0)")
    print(f"  Max Drawdown:  {metrics['max_drawdown']*100:.1f}%  (target < 15%)")
    print(f"  Total Return:  {metrics['total_return']*100:.1f}%")
    print(f"  Calmar Ratio:  {metrics['calmar_ratio']:.3f}")
    print("\n[DONE]")


if __name__ == "__main__":
    main()
