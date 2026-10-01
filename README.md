# RCS Trading Bot

A small, risk-controlled trading bot scaffold.

## Current mode
**Phase 2C: historical multi-symbol robustness + walk-forward validation + paper execution only.**

The bot reads historical OHLCV market bars from Yahoo Finance through `yfinance`. It does **not** connect to a live broker or place real-money orders.

## Phase 2 single-symbol defaults
- Symbol: `SOL.JO` (Sasol, JSE)
- Period: `6mo`
- Interval: `1h`
- JSE `.JO` prices are normalized from Yahoo's ZAc quotes to ZAR.

Run:

```bash
python backtest.py
```

Override the symbol/timeframe with environment variables:

```bash
RCS_SYMBOL=MTN.JO RCS_PERIOD=1y RCS_INTERVAL=1d python backtest.py
```

## Phase 2B multi-symbol basket
The default robustness basket applies the same strategy, risk limits and execution costs to:

### JSE
- `SOL.JO`
- `NPN.JO`
- `MTN.JO`
- `FSR.JO`
- `SBK.JO`

### US ETFs
- `SPY`
- `QQQ`
- `IWM`
- `DIA`

Run:

```bash
python portfolio_backtest.py
```

Override the basket:

```bash
RCS_SYMBOLS="SOL.JO,MTN.JO,FSR.JO,SPY,QQQ" python portfolio_backtest.py
```

The cross-market comparison is primarily percentage-based. Absolute account P&L is not directly comparable between JSE and US instruments because they trade in different currencies.

## Phase 2C walk-forward validation
Phase 2C tests whether the strategy survives unseen data rather than only fitting the full historical sample.

Default walk-forward setup:
- history: `2y`
- interval: `1d`
- training window: 252 bars
- unseen test window: 63 bars
- step: 63 bars
- SMA candidates: `(3,10)`, `(5,12)`, `(8,20)`, `(10,30)`

For every fold:
1. Only the training window is used for parameter selection.
2. Candidates are scored on training excess return with a drawdown penalty.
3. The selected SMA pair is frozen.
4. The immediately following test window is run out-of-sample.
5. The process rolls forward and repeats.

Run:

```bash
python walk_forward.py
```

Optional overrides:

```bash
RCS_WF_PERIOD=5y \
RCS_WF_INTERVAL=1d \
RCS_WF_TRAIN_BARS=504 \
RCS_WF_TEST_BARS=126 \
RCS_WF_STEP_BARS=126 \
python walk_forward.py
```

The Phase 2C report records:
- selected SMA parameters per fold
- training return and drawdown
- unseen test return
- unseen buy-and-hold return
- unseen excess return
- unseen drawdown
- test trade count, win rate, profit factor and expectancy
- compounded out-of-sample return per symbol
- compounded benchmark return per symbol
- percentage of positive test folds
- percentage of test folds beating the benchmark
- cross-symbol median out-of-sample results

Files:
- `reports/walk_forward_summary.csv`
- `reports/walk_forward_summary.txt`
- `reports/walk_forward_<symbol>.csv` for each successful symbol

## Safety defaults
- Starting paper balance: 10,000 account currency units
- Risk per trade: 0.5% of equity
- Maximum daily loss: 2% of starting daily equity
- Maximum position allocation: 10% of equity
- Maximum 3 entries per session
- No leverage
- Long-only

## Strategy
A simple moving-average crossover:
- Buy when the fast SMA crosses above the slow SMA.
- Exit when the fast SMA crosses below the slow SMA, stop-loss is hit, or take-profit is hit.
- Stops and targets are evaluated against each bar's high and low, not merely its close.
- If a candle touches both stop and target, the backtest uses the conservative assumption that the stop was hit first.

## Execution assumptions
The historical backtest includes modeled execution costs:
- Default fee: **10 basis points per side**
- Default slippage: **5 basis points per side**

Override them with:

```bash
RCS_FEE_BPS=15 RCS_SLIPPAGE_BPS=8 python walk_forward.py
```

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
- per-symbol walk-forward fold CSV files

If one symbol has a data-source error, the remaining symbols continue and the failure is recorded.

## Install and run

```bash
pip install -r requirements.txt
python -m unittest discover -s tests -v
python backtest.py
python portfolio_backtest.py
python walk_forward.py
```

## Automated checks
GitHub Actions runs:
1. deterministic unit tests
2. the Phase 2 single-symbol backtest
3. the Phase 2B multi-symbol robustness basket
4. the Phase 2C walk-forward validation

All generated reports are uploaded as a workflow artifact.

## Data note
`yfinance` uses Yahoo Finance's publicly available market-data interfaces and is intended for research/personal use. Market quotes may be delayed, adjusted and incomplete, and they are not an execution feed.

## Important limitations
A positive historical or walk-forward result does not establish that the strategy will be profitable live. Walk-forward testing reduces one important form of overfitting but does not remove market-regime risk, data-quality problems, liquidity constraints, survivorship bias, currency effects, execution uncertainty or model-selection bias.

## Next phase
1. Review the actual Phase 2C out-of-sample results across the basket.
2. Add parameter-sensitivity/stability analysis around the selected SMA values.
3. Add a broker sandbox/paper-trading adapter for continuous forward testing.
4. Run forward paper trading for a meaningful period before considering live capital.
5. Only after successful forward testing, consider an explicitly enabled live-trading mode.

## Secrets
Never commit API keys. A future broker integration must use environment variables or the deployment platform's secret store.
