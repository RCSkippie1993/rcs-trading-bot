# RCS Trading Bot

A risk-controlled research and paper-trading system.

## Current mode
**Phase 3: continuous-forward-paper architecture + Phase 2 historical validation.**

The repository now supports historical backtesting, multi-symbol robustness tests, walk-forward validation, parameter-stability analysis, and stateful forward paper execution. It still does **not** place real-money broker orders.

## Safety defaults
- Starting paper balance: 10,000 account-currency units
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
- persistent JSON account/position state
- duplicate-bar protection
- simulated buy/sell fills
- fees and slippage
- stop-loss and take-profit handling
- daily loss cutoff
- session trade limits
- persisted halt state
- environment-variable kill switch
- latest-run JSON snapshot

The runner is disabled by default. To process one new market bar:

```bash
RCS_FORWARD_ENABLED=1 \
RCS_SYMBOL=SOL.JO \
RCS_FORWARD_PERIOD=5d \
RCS_FORWARD_INTERVAL=15m \
python forward_paper.py
```

State is stored by default at:

```text
state/forward_state.json
```

Latest snapshot:

```text
reports/forward_latest.json
```

Both `state/` and `reports/` are ignored by Git so account state is not accidentally committed.

### Kill switch
Set:

```bash
RCS_KILL_SWITCH=1
```

The engine will persist a halted state and stop opening or closing simulated positions. A halted state should be reviewed deliberately before being reset.

## GitHub Actions
`.github/workflows/forward-paper-smoke.yml` provides a **manual-only** Phase 3 smoke test. It processes one forward paper bar and uploads the resulting snapshot.

It is intentionally not scheduled as the continuous runtime because GitHub Actions does not provide a suitable persistent local state model for a trading loop. Continuous paper operation should run on a persistent worker/container with durable storage.

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

Tests cover the historical engine, walk-forward logic, parameter grid, persistent state, duplicate-bar handling, and halt behavior.

## Existing reports
Phase 2:
- `reports/latest_summary.txt`
- `reports/latest_trades.csv`
- `reports/latest_equity.csv`

Phase 2B:
- `reports/portfolio_comparison.csv`
- `reports/portfolio_summary.txt`

Phase 2C:
- `reports/walk_forward_summary.csv`
- `reports/walk_forward_summary.txt`
- per-symbol fold files

Phase 2D:
- `reports/parameter_stability.csv`
- `reports/parameter_stability_detail.csv`
- `reports/parameter_stability_summary.txt`

Phase 3:
- `reports/forward_latest.json`
- `state/forward_state.json`

## Important limitation
A historical, walk-forward, stability, or forward-paper result does not establish that a strategy will be profitable with real capital. Forward paper fills remain simulations and can differ materially from live execution, spreads, gaps, liquidity, market-impact, outages, taxes, FX conversion, and broker-specific behavior.

## Phase 3 next deployment step
Run `forward_paper.py` on a persistent worker with durable state storage and a controlled polling schedule. After a meaningful forward-paper observation period, a broker-specific **paper-account adapter** can replace the local simulated-fill layer while keeping live trading disabled.

## Secrets
Never commit API keys or account credentials. Future broker connections must use environment variables or the deployment platform's secret store.
