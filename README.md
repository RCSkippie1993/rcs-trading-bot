# RCS Trading Bot

A small, risk-controlled trading bot scaffold.

## Current mode
**Real market data + paper execution only.** The bot now reads market bars from Yahoo Finance through `yfinance`, but it does not connect to a live broker or place real-money orders.

Default market settings:
- Symbol: `SOL.JO` (Sasol, JSE)
- Period: `1mo`
- Interval: `1h`
- JSE `.JO` prices are normalized from Yahoo's ZAc quotes to ZAR.

Override the defaults with environment variables:

```bash
RCS_SYMBOL=MTN.JO RCS_PERIOD=5d RCS_INTERVAL=15m python main.py
```

## Safety defaults
- Starting paper balance: R10,000
- Risk per trade: 0.5% of equity
- Maximum daily loss: 2% of starting daily equity
- Maximum position allocation: 10% of equity
- Maximum 3 trades per session
- No leverage
- Long-only in v1

## Strategy
A simple moving-average crossover:
- Buy when the fast SMA crosses above the slow SMA.
- Exit when the fast SMA crosses below the slow SMA, stop-loss is hit, or take-profit is hit.
- Stops and targets are evaluated against each bar's high/low.

## Install and run

```bash
pip install -r requirements.txt
python main.py
```

## Next steps
1. Add a proper backtest report: win rate, drawdown, profit factor, fees/slippage and total return.
2. Test several liquid instruments and timeframes without curve-fitting.
3. Add a broker paper-trading adapter for continuous execution.
4. Only after successful testing, add an explicitly enabled live-trading mode.

## Data note
`yfinance` uses Yahoo Finance's publicly available market-data interfaces and is intended for research/personal use. Market quotes may be delayed and are not an execution feed.

## Secrets
Never commit API keys. A future broker integration must use environment variables or the deployment platform's secret store.
