from __future__ import annotations

from datetime import date, timedelta

from stock_manager.pricing.models import MarketQuote

from .base_provider import NoDataError, PriceProvider, ProviderError, parse_number


class FinMindProvider(PriceProvider):
    source = "FinMind"
    exchange = ""
    endpoint = "https://api.finmindtrade.com/api/v4/data"

    def __init__(self, token: str = "", timeout: float = 12.0):
        super().__init__(timeout)
        self.token = token.strip()

    def fetch_latest(self, symbol: str, as_of: date | None = None) -> MarketQuote:
        as_of = as_of or date.today()
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        payload = self._get_json(
            self.endpoint,
            {
                "dataset": "TaiwanStockPrice",
                "data_id": symbol,
                "start_date": (as_of - timedelta(days=40)).isoformat(),
                "end_date": as_of.isoformat(),
            },
            headers=headers,
        )
        if str(payload.get("status", "200")) != "200" or not payload.get("data"):
            raise NoDataError(str(payload.get("msg") or "FinMind 查無成交資料"))
        matching = [row for row in payload["data"] if str(row.get("stock_id") or "") == symbol]
        if not matching:
            raise ProviderError("FinMind 回傳股票代號與請求不一致")
        row = sorted(matching, key=lambda item: str(item.get("date") or ""))[-1]
        close = parse_number(row.get("close"))
        if close is None:
            raise NoDataError("FinMind 最新交易日沒有有效收盤價")
        try:
            trade_date = date.fromisoformat(str(row["date"])[:10])
        except (KeyError, ValueError) as exc:
            raise ProviderError("FinMind 回傳日期無法解析") from exc
        return MarketQuote(
            symbol=symbol,
            name="",
            exchange="",
            trade_date=trade_date,
            open=parse_number(row.get("open")),
            high=parse_number(row.get("max")),
            low=parse_number(row.get("min")),
            close=close,
            volume_shares=parse_number(row.get("Trading_Volume"), integer=True),
            turnover_twd=parse_number(row.get("Trading_money"), integer=True),
            transaction_count=parse_number(row.get("Trading_turnover"), integer=True),
            price_change=parse_number(row.get("spread")),
            source=self.source,
        )
