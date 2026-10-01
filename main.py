import math
from bot.config import Settings
from bot.strategy import MovingAverageCrossStrategy
from bot.risk import RiskManager
from bot.broker import PaperBroker

def synthetic_prices():
    # Deterministic demo feed: trend + oscillation, no network required.
    for i in range(80):
        yield round(100 + (i * 0.08) + (math.sin(i / 3) * 2.2), 2)

def main():
    settings = Settings()
    broker = PaperBroker(settings.starting_cash)
    risk = RiskManager(settings)
    strategy = MovingAverageCrossStrategy(
        settings.fast_window, settings.slow_window
    )

    print("RCS Trading Bot — PAPER MODE")
    print(f"Starting cash: R{broker.cash:,.2f}")

    last_price = None
    for step, price in enumerate(synthetic_prices(), start=1):
        last_price = price
        signal = strategy.on_price(price)
        equity = broker.equity(price)

        if broker.position:
            entry = broker.position.entry_price
            stop_price = entry * (1 - settings.stop_loss_pct)
            target_price = entry * (1 + settings.take_profit_pct)

            if price <= stop_price:
                result = broker.sell_all(price)
                print(f"{step:03} STOP  @ R{price:.2f} | P&L R{result['pnl']:.2f}")
                continue
            if price >= target_price:
                result = broker.sell_all(price)
                print(f"{step:03} TARGET @ R{price:.2f} | P&L R{result['pnl']:.2f}")
                continue

        if signal == "BUY" and broker.position is None:
            if not risk.can_open_trade(equity):
                print(f"{step:03} BUY blocked by risk controls")
                continue
            qty = risk.position_size(equity, price)
            if broker.buy(price, qty):
                risk.record_trade()
                print(f"{step:03} BUY   {qty} @ R{price:.2f}")
        elif signal == "SELL" and broker.position is not None:
            result = broker.sell_all(price)
            print(f"{step:03} SELL  @ R{price:.2f} | P&L R{result['pnl']:.2f}")

    if broker.position and last_price is not None:
        result = broker.sell_all(last_price)
        print(f"END EXIT @ R{last_price:.2f} | P&L R{result['pnl']:.2f}")

    final_equity = broker.cash
    print(f"Final equity: R{final_equity:,.2f}")
    print(f"Realized P&L: R{broker.realized_pnl:,.2f}")
    print(f"Trades opened: {risk.trades}")

if __name__ == "__main__":
    main()
