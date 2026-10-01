from dataclasses import dataclass
from typing import Iterator

import yfinance as yf


@dataclass(frozen=True)
class MarketBar:
    timestamp: object
    open: float
    high: float
    low: float
    close: float
    volume: float


class YahooFinanceData:
    """Read-only market-data adapter backed by Yahoo Finance via yfinance."""

    def __init__(self, symbol: str, period: str, interval: str):
        self.symbol = symbol
        self.period = period
        self.interval = interval

    @property
    def price_scale(self) -> float:
        # Yahoo quotes JSE (.JO) equities in South African cents (ZAc).
        # The paper account is denominated in rand, so normalize to ZAR.
        return 0.01 if self.symbol.upper().endswith(".JO") else 1.0

    def bars(self) -> Iterator[MarketBar]:
        ticker = yf.Ticker(self.symbol)
        frame = ticker.history(
            period=self.period,
            interval=self.interval,
            auto_adjust=True,
            actions=False,
            repair=True,
            raise_errors=True,
        )

        if frame.empty:
            raise RuntimeError(
                f"No market data returned for {self.symbol} "
                f"({self.period}, {self.interval})."
            )

        scale = self.price_scale
        for timestamp, row in frame.iterrows():
            yield MarketBar(
                timestamp=timestamp,
                open=float(row["Open"]) * scale,
                high=float(row["High"]) * scale,
                low=float(row["Low"]) * scale,
                close=float(row["Close"]) * scale,
                volume=float(row.get("Volume", 0.0)),
            )
