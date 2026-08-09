from __future__ import annotations

import re
from datetime import date, timedelta

from stock_manager.pricing.models import MarketQuote

from .base_provider import NoDataError, PriceProvider, ProviderError, parse_number, roc_date


class TWSEProvider(PriceProvider):
    source = "TWSE"
    exchange = "TWSE"
    endpoint = "https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY"

    def fetch_latest(self, symbol: str, as_of: date | None = None) -> MarketQuote:
        as_of = as_of or date.today()
        payload = self._request_month(symbol, as_of)
        if payload.get("stat") != "OK" or not payload.get("data"):
            previous_month = as_of.replace(day=1) - timedelta(days=1)
            payload = self._request_month(symbol, previous_month)
        if payload.get("stat") != "OK" or not payload.get("data"):
            raise NoDataError(str(payload.get("stat") or "查無上市成交資料"))
        title = str(payload.get("title") or "")
        if symbol not in title:
            raise ProviderError("回傳股票代號與請求不一致")
        rows = sorted(payload["data"], key=lambda row: roc_date(row[0]))
        row = rows[-1]
        close = parse_number(row[6])
        if close is None:
            raise NoDataError("最新交易日沒有有效收盤價")
        name_match = re.search(rf"\b{re.escape(symbol)}\s+(.+?)\s+各日成交資訊", title)
        return MarketQuote(
            symbol=symbol,
            name=name_match.group(1).strip() if name_match else "",
            exchange=self.exchange,
            trade_date=roc_date(row[0]),
            open=parse_number(row[3]),
            high=parse_number(row[4]),
            low=parse_number(row[5]),
            close=close,
            volume_shares=parse_number(row[1], integer=True),
            turnover_twd=parse_number(row[2], integer=True),
            price_change=parse_number(row[7]),
            transaction_count=parse_number(row[8], integer=True),
            source=self.source,
        )

    def _request_month(self, symbol: str, target: date):
        return self._get_json(
            self.endpoint,
            {"response": "json", "date": target.strftime("%Y%m%d"), "stockNo": symbol},
        )
