# RCS Trading Bot

A risk-controlled research and paper-trading system.

## Current mode
**Phase 3: scheduled multi-symbol forward paper trading + Phase 2 historical validation.**

The repository supports historical backtesting, multi-symbol robustness tests, walk-forward validation, parameter-stability analysis, and stateful forward paper execution. It still does **not** connect to a live broker or place real-money orders.

## Safety defaults
- Starting paper balance: 10,000 account-currency units per symbol
- Risk per trade: 0.5% of equity
- Maximum daily loss: 2% of session-start equity
- Maximum position allocation: 10% of equity
- Maximum 3 entries per session
- No leverage
- Long-only
- Modeled fee: 10 bps per side
- Modeled slippage: 5 bps per side

## Phase 3 forward paper trading
The forward engine lives in `bot/forward.py` and is run through `forward_paper.py`.

It provides:
- persistent account/position state
- duplicate-bar protection
- completed-bar filtering
- replay of missed completed bars after a delayed run
- signal-at-close / execution-at-next-bar-open modeling
- simulated buy/sell fills
- entry and exit fees in realized P&L
- conservative gap-down stop handling
- stop-loss and take-profit handling
- daily loss cutoff
- session trade limits
- persisted halt state
- environment-variable kill switch
- performance ledger for the readiness dashboard

The runner is disabled by default. A single manual paper cycle can be run with:

```bash
RCS_FORWARD_ENABLED=1 \
RCS_SYMBOL=SOL.JO \
RCS_FORWARD_PERIOD=10d \
RCS_FORWARD_INTERVAL=15m \
python forward_paper.py
```

## Scheduled zero-cost Phase 3 runtime
`.github/workflows/forward-paper-scheduled.yml` is the current automated paper runtime.

It runs five minutes after each 15-minute boundary during the weekday JSE trading window and processes:
- `SOL.JO`
- `NPN.JO`
- `MTN.JO`
- `FSR.JO`
- `SBK.JO`

Each symbol has an independent paper account/state file. The workflow:
1. restores the previous state from the dedicated `paper-state` branch;
2. fetches recent Yahoo market data;
3. ignores any still-forming candle;
4. replays every completed bar not previously processed;
5. executes queued signals at the next bar open;
6. updates each paper account;
7. builds the readiness dashboard;
8. writes the updated state back to `paper-state`;
9. uploads the run reports as a GitHub Actions artifact.

The `paper-state` branch contains **paper simulation state only**. No API keys, passwords, broker credentials or real account data should ever be stored there.

GitHub scheduled workflows can run late, especially during platform load. The replay logic is designed to process missed completed candles when that happens. This runtime is suitable for research/forward-paper observation, not live order execution.

## Kill switch
The engine also supports:

```bash
RCS_KILL_SWITCH=1
```

For the scheduled GitHub runtime, creating the file below on the `paper-state` branch activates the same halt behavior on the next run:

```text
state/KILL_SWITCH
```

The bot then persists a halted state. Restarting after a halt should be a deliberate review action.

## Phase 3 readiness dashboard
Run:

```bash
python readiness_dashboard.py
```

Default research gates:
- at least 30 closed paper trades per adequately sampled symbol
- positive return after modeled costs
- profit factor >= 1.20
- maximum drawdown <= 10%
- at least 60% of adequately sampled symbols with positive returns

Possible statuses:
- `INSUFFICIENT DATA`
- `NOT READY`
- `READY FOR MANUAL REVIEW`

`READY FOR MANUAL REVIEW` is not permission to trade live and is not a profit guarantee.

Reports:
- `reports/forward_readiness.txt`
- `reports/forward_readiness.json`
- per-symbol latest snapshots under `reports/forward_<symbol>.json` in scheduled runs

## Manual GitHub smoke test
`.github/workflows/forward-paper-smoke.yml` remains available as a manual one-cycle smoke test. It does not serve as the durable scheduled runtime.

## Market data
The project currently uses `yfinance>=1.7.0,<2` for research and forward paper data. Yahoo market data can be delayed, adjusted, incomplete, or unsuitable for execution decisions. It is not a broker execution feed.

JSE `.JO` prices are normalized from Yahoo's ZAc quotes to ZAR by the data adapter.

## Phase 2 historical validation
### Single symbol
```bash
python backtest.py
```

### Multi-symbol robustness — Phase 2B
```bash
python portfolio_backtest.py
```

Default basket:
- JSE: `SOL.JO`, `NPN.JO`, `MTN.JO`, `FSR.JO`, `SBK.JO`
- US ETFs: `SPY`, `QQQ`, `IWM`, `DIA`

### Walk-forward validation — Phase 2C
```bash
python walk_forward.py
```

Default walk-forward setup:
- history: 2 years
- daily bars
- 252-bar training window
- 63-bar unseen test window
- candidates: `(3,10)`, `(5,12)`, `(8,20)`, `(10,30)`

### Parameter stability — Phase 2D
```bash
python parameter_stability.py
```

The stability analysis tests a neighborhood of SMA combinations across the basket rather than selecting a single historical winner.

## Tests
```bash
pip install -r requirements.txt
python -m unittest discover -s tests -v
```

Tests cover the historical engine, walk-forward logic, parameter grid, persistent state, duplicate-bar handling, halt behavior, next-open forward execution and readiness gates.

## Reports
### Phase 2
- `reports/latest_summary.txt`
- `reports/latest_trades.csv`
- `reports/latest_equity.csv`

### Phase 2B
- `reports/portfolio_comparison.csv`
- `reports/portfolio_summary.txt`

### Phase 2C
- `reports/walk_forward_summary.csv`
- `reports/walk_forward_summary.txt`
- per-symbol fold files

### Phase 2D
- `reports/parameter_stability.csv`
- `reports/parameter_stability_detail.csv`
- `reports/parameter_stability_summary.txt`

### Phase 3
- `reports/forward_latest.json`
- `reports/forward_readiness.txt`
- `reports/forward_readiness.json`
- persistent paper state on the `paper-state` branch

## Important limitations
Historical, walk-forward, stability and forward-paper results do not establish that the strategy will be profitable with real capital. Paper fills can differ materially from actual spreads, gaps, queue position, liquidity, market impact, outages, taxes, FX conversion and broker-specific execution.

The GitHub scheduler is intentionally a **paper-research runtime only**. Before any real-money consideration, the next infrastructure step should be a broker-supported paper account and a persistent service with proper secrets, monitoring, reconciliation and broker-side controls.

## Secrets
Never commit API keys or account credentials. Future broker connections must use the deployment platform's secret store or protected environment variables.
