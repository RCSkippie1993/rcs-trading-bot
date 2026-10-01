# RCS Trading Bot

A small, risk-controlled trading bot scaffold.

## Current mode
**Phase 2B: historical multi-symbol robustness testing + paper execution only.**

The bot reads historical OHLCV market bars from Yahoo Finance through `yfinance`. It does **not** connect to a live broker or place real-money orders.

## Phase 2 single-symbol defaults
- Symbol: `SOL.JO` (Sasol, JSE)
- Period: `6mo`
- Interval: `1h`
- JSE `.JO` prices are normalized from Yahoo's ZAc quotes to ZAR.

Run a single-symbol test with:

```bash
python backtest.py
```

Override the symbol/timeframe with environment variables:

```bash
RCS_SYMBOL=MTN.JO RCS_PERIOD=1y RCS_INTERVAL=1d python backtest.py
```

## Phase 2B multi-symbol basket
The default robustness basket applies the **same strategy, risk limits and execution costs** to:

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

Override the basket without changing code:

```bash
RCS_SYMBOLS="SOL.JO,MTN.JO,FSR.JO,SPY,QQQ" python portfolio_backtest.py
```

The cross-market comparison is primarily percentage-based. Absolute account P&L is not directly comparable between JSE and US instruments because they trade in different currencies.

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
- Stops and targets are evaluated against each bar's **high and low**, not merely its close.
- If a candle touches both stop and target, the backtest uses the conservative assumption that the stop was hit first.

## Execution assumptions
The historical backtest includes modeled execution costs:
- Default fee: **10 basis points per side**
- Default slippage: **5 basis points per side**

Override them with:

```bash
RCS_FEE_BPS=15 RCS_SLIPPAGE_BPS=8 python portfolio_backtest.py
```

## Phase 2 single-symbol report
The single-symbol report includes:
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

Files:
- `reports/latest_summary.txt`
- `reports/latest_trades.csv`
- `reports/latest_equity.csv`

## Phase 2B robustness report
The multi-symbol runner produces:
- strategy return by instrument
- buy-and-hold return by instrument
- excess return versus benchmark
- trade count and win rate
- profit factor
- maximum drawdown
- expectancy
- modeled fees
- percentage of instruments with positive returns
- percentage of instruments beating buy-and-hold
- percentage with positive expectancy
- median strategy return
- median excess return
- median maximum drawdown

Files:
- `reports/portfolio_comparison.csv`
- `reports/portfolio_summary.txt`

If one symbol has a data-source error, the remaining symbols still run and the failure is recorded in the summary.

## Install and run

```bash
pip install -r requirements.txt
python -m unittest discover -s tests -v
python backtest.py
python portfolio_backtest.py
```

## Automated checks
GitHub Actions first runs the deterministic test suite, then the single-symbol backtest, then the Phase 2B basket. All reports are uploaded as a workflow artifact.

## Data note
`yfinance` uses Yahoo Finance's publicly available market-data interfaces and is intended for research/personal use. Market quotes may be delayed, adjusted and incomplete, and they are not an execution feed.

## Important limitations
A positive historical backtest does not establish that the strategy will be profitable live. Cross-symbol success also does not eliminate overfitting. Results remain sensitive to market regime, data quality, execution costs, gaps, liquidity, currency, survivorship bias and parameter selection.

## Next phase
1. Run multiple timeframes, including daily bars over longer historical periods.
2. Add train/test and walk-forward validation.
3. Add parameter sensitivity testing rather than selecting only the historical winner.
4. Add a broker sandbox/paper-trading adapter for continuous forward testing.
5. Only after successful forward testing, consider an explicitly enabled live-trading mode.

## Secrets
Never commit API keys. A future broker integration must use environment variables or the deployment platform's secret store.
