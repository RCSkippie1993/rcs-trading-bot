# RCS Trading Bot

A small, risk-controlled trading bot scaffold.

## Current mode
**Paper trading only.** It does not connect to a live broker or place real-money orders.

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

The included demo market feed is deterministic synthetic data so the bot can be tested without credentials.

## Run
```bash
python main.py
```

## Next steps
1. Add historical-market-data adapter.
2. Backtest and report win rate, drawdown, profit factor and total return.
3. Add a broker paper-trading adapter.
4. Only after successful testing, add an explicitly enabled live-trading mode.

## Secrets
Never commit API keys. A future broker integration must use environment variables or the deployment platform's secret store.
