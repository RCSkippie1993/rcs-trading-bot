from bot.broker import PaperBroker
from bot.config import Settings
from bot.data import YahooFinanceData
from bot.risk import RiskManager
from bot.strategy import MovingAverageCrossStrategy


def main():
    settings = Settings()
    market = YahooFinanceData(
        symbol=settings.symbol,
        period=settings.period,
        interval=settings.interval,
    )
    broker = PaperBroker(settings.starting_cash)
    risk = RiskManager(settings)
    strategy = MovingAverageCrossStrategy(
        settings.fast_window, settings.slow_window
    )

    print("RCS Trading Bot — REAL DATA / PAPER EXECUTION")
    print(
        f"Market: {settings.symbol} | "
        f"Period: {settings.period} | Interval: {settings.interval}"
    )
    print(f"Starting cash: R{broker.cash:,.2f}")

    last_price = None
    bars_seen = 0

    for step, bar in enumerate(market.bars(), start=1):
        bars_seen = step
        price = bar.close
        last_price = price
        signal = strategy.on_price(price)
        equity = broker.equity(price)

        if broker.position:
            entry = broker.position.entry_price
            stop_price = entry * (1 - settings.stop_loss_pct)
            target_price = entry * (1 + settings.take_profit_pct)

            if bar.low <= stop_price:
                result = broker.sell_all(stop_price)
                print(
                    f"{bar.timestamp} STOP  @ R{stop_price:.2f} "
                    f"| P&L R{result['pnl']:.2f}"
                )
                continue

            if bar.high >= target_price:
                result = broker.sell_all(target_price)
                print(
                    f"{bar.timestamp} TARGET @ R{target_price:.2f} "
                    f"| P&L R{result['pnl']:.2f}"
                )
                continue

        if signal == "BUY" and broker.position is None:
            if not risk.can_open_trade(equity):
                print(f"{bar.timestamp} BUY blocked by risk controls")
                continue

            qty = risk.position_size(equity, price)
            if qty > 0 and broker.buy(price, qty):
                risk.record_trade()
                print(f"{bar.timestamp} BUY   {qty} @ R{price:.2f}")

        elif signal == "SELL" and broker.position is not None:
            result = broker.sell_all(price)
            print(
                f"{bar.timestamp} SELL  @ R{price:.2f} "
                f"| P&L R{result['pnl']:.2f}"
            )

    if broker.position and last_price is not None:
        result = broker.sell_all(last_price)
        print(f"END EXIT @ R{last_price:.2f} | P&L R{result['pnl']:.2f}")

    print(f"Bars processed: {bars_seen}")
    print(f"Final equity: R{broker.cash:,.2f}")
    print(f"Realized P&L: R{broker.realized_pnl:,.2f}")
    print(f"Trades opened: {risk.trades}")


if __name__ == "__main__":
    main()
