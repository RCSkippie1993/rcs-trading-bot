# RCS Trading Bot

A small, risk-controlled trading bot scaffold.

## Current mode
**Phase 2: historical market-data backtesting + paper execution only.**

The bot reads historical OHLCV market bars from Yahoo Finance through `yfinance`. It does **not** connect to a live broker or place real-money orders.

Default market settings:
- Symbol: `SOL.JO` (Sasol, JSE)
- Period: `6mo`
- Interval: `1h`
- JSE `.JO` prices are normalized from Yahoo's ZAc quotes to ZAR.

Override the defaults with environment variables:

```bash
RCS_SYMBOL=MTN.JO RCS_PERIOD=1y RCS_INTERVAL=1d python backtest.py
```

## Safety defaults
- Starting paper balance: R10,000
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
- Stops and targets are evaluated against each bar's **high and low**, not merely its close.
- If a candle touches both stop and target, the backtest uses the conservative assumption that the stop was hit first.

## Phase 2 realism
The historical backtest now includes modeled execution costs:
- Default fee: **10 basis points per side**
- Default slippage: **5 basis points per side**

Override them with:

```bash
RCS_FEE_BPS=15 RCS_SLIPPAGE_BPS=8 python backtest.py
```

The report includes:
- ending equity and net P&L
- total return
- buy-and-hold benchmark return
- excess return versus benchmark
- closed trades
- wins, losses and win rate
- profit factor
- maximum drawdown
- average trade P&L
- expectancy per trade
- modeled transaction fees

Files are written to:
- `reports/latest_summary.txt`
- `reports/latest_trades.csv`
- `reports/latest_equity.csv`

## Install and run

```bash
pip install -r requirements.txt
python -m unittest discover -s tests -v
python backtest.py
```

## Automated checks
GitHub Actions runs the deterministic test suite before each scheduled real-data backtest. The backtest report is uploaded as a workflow artifact.

## Data note
`yfinance` uses Yahoo Finance's publicly available market-data interfaces and is intended for research/personal use. Market quotes may be delayed, adjusted and incomplete, and they are not an execution feed.

## Important limitations
A positive historical backtest does not establish that the strategy will be profitable live. Results remain sensitive to market regime, data quality, execution costs, gaps, liquidity and parameter selection. The strategy must be tested across multiple instruments and out-of-sample periods before any live-trading integration is considered.

## Next phase
1. Run multi-symbol backtests across liquid JSE and/or US instruments.
2. Add parameter sweeps without selecting parameters solely on the best historical return.
3. Add train/test or walk-forward validation.
4. Add a broker sandbox/paper-trading adapter for continuous forward testing.
5. Only after successful forward testing, add an explicitly enabled live-trading mode.

## Secrets
Never commit API keys. A future broker integration must use environment variables or the deployment platform's secret store.
