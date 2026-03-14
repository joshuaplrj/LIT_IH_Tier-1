# AutoTrader — Hints

> Each tier costs score points. Only request when genuinely stuck.

## Tier 1 — Conceptual Direction (-5% score penalty)
Portfolio management is a sequential decision problem under uncertainty: at each time step the agent observes market conditions and decides how to allocate capital. Reinforcement learning frames this naturally as a Markov Decision Process — the state is the current market snapshot, the action is the new portfolio weight vector, and the reward penalises both poor returns and excessive risk. The key insight is that the reward function must encode all the objectives you care about (return, drawdown, turnover cost) simultaneously, because the agent will otherwise learn to optimise only what you directly reward while ignoring everything else. The out-of-sample test period requires generalisation, not just memorisation of bull market patterns.

## Tier 2 — Technique Guidance (-10% score penalty)
Use **PPO (Proximal Policy Optimization)** with a continuous Gaussian policy over the portfolio weight simplex. PPO is stable under the non-stationary financial data distribution and handles the high-dimensional action space (60 assets) better than DQN variants. Represent the state as a **stacked feature matrix** of shape `(n_assets, n_features, lookback)` fed through a lightweight CNN or LSTM to capture cross-asset correlations and temporal momentum. Use a **Sharpe-ratio-based reward**: `r_t = (portfolio_return_t - transaction_cost_t) / (rolling_std + 1e-9)` computed over a 20-day rolling window, scaled by a drawdown penalty multiplier that increases when drawdown exceeds 10%.

## Tier 3 — Implementation Guidance (-15% score penalty)
Follow these steps in order:

1. **PortfolioEnv (gym.Env)** — `observation_space`: Box of shape `(n_assets, n_features, lookback=20)`. `action_space`: Box `[0, 1]^n_assets`, then normalise to sum to 1 via softmax inside `step()`. Maintain `self.weights`, `self.portfolio_value`, `self.peak_value` as state variables.

2. **State features** — Per asset: `[log_return_1d, log_return_5d, log_return_20d, volume_ratio, rsi_14, macd_signal, sentiment, pe_ratio_normalised]`. Stack macro features as an extra row. Normalise each feature with rolling z-score (window=252 trading days).

3. **Reward function** — `daily_return = (new_value - old_value) / old_value`. `transaction_cost = 0.001 * sum(|new_weights - old_weights|) * portfolio_value`. `drawdown = (peak_value - new_value) / peak_value`. `reward = daily_return - transaction_cost/portfolio_value - 0.1 * max(0, drawdown - 0.10)`.

4. **PPO training** — Use `stable-baselines3`: `model = PPO("MlpPolicy", env, n_steps=2048, batch_size=64, n_epochs=10, learning_rate=3e-4)`. Train for 500 K steps. Validate on 2022–2023 data with periodic rollouts.

5. **Position constraints** — After softmax normalisation, clip each weight to [0, 0.20] and ensure cash ≥ 0.05: `w = clip(w, 0, 0.20); cash = 1 - sum(w); if cash < 0.05: w *= (0.95 / sum(w))`.

6. **Backtest** — Re-run the trained policy step-by-step on 2024–2025 data without re-training. Log all trades, compute Sharpe, max drawdown, Calmar ratio, and turnover.
