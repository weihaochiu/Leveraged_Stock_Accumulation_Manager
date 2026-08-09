from __future__ import annotations

from datetime import date, timedelta

from stock_manager.pricing.models import MarketQuote

from .base_provider import NoDataError, PriceProvider, ProviderError, parse_number, roc_date


class TPExProvider(PriceProvider):
    source = "TPEx"
    exchange = "TPEx"
    endpoint = "https://www.tpex.org.tw/www/zh-tw/afterTrading/tradingStock"

    def fetch_latest(self, symbol: str, as_of: date | None = None) -> MarketQuote:
        as_of = as_of or date.today()
        payload = self._request_month(symbol, as_of)
        if str(payload.get("stat", "")).lower() != "ok" or not payload.get("tables") or not (payload["tables"][0].get("data") or []):
            previous_month = as_of.replace(day=1) - timedelta(days=1)
            payload = self._request_month(symbol, previous_month)
        if str(payload.get("stat", "")).lower() != "ok" or not payload.get("tables"):
            raise NoDataError(str(payload.get("stat") or "查無上櫃成交資料"))
        if str(payload.get("code") or "") != symbol:
            raise ProviderError("回傳股票代號與請求不一致")
        rows = payload["tables"][0].get("data") or []
        if not rows:
            raise NoDataError("指定月份沒有上櫃成交資料")
        row = sorted(rows, key=lambda item: roc_date(item[0]))[-1]
        close = parse_number(row[6])
        if close is None:
            raise NoDataError("最新交易日沒有有效收盤價")

        # TPEx 此端點明確以「張」與「仟元」回傳。一般股票每張換算 1,000 股；
        # 外幣 ETF（第六碼 K/C）交易單位可能不同，無法由此端點安全推定時保留空值。
        lots = parse_number(row[1], integer=True)
        volume_shares = None if len(symbol) >= 6 and symbol[5].upper() in {"K", "C"} else (lots * 1000 if lots is not None else None)
        turnover_thousands = parse_number(row[2], integer=True)
        warning = "外幣 ETF 交易單位無法由盤後端點安全換算，成交股數未寫入。" if volume_shares is None and lots is not None else ""
        return MarketQuote(
            symbol=symbol,
            name=str(payload.get("name") or "").strip(),
            exchange=self.exchange,
            trade_date=roc_date(row[0]),
            open=parse_number(row[3]),
            high=parse_number(row[4]),
            low=parse_number(row[5]),
            close=close,
            volume_shares=volume_shares,
            turnover_twd=turnover_thousands * 1000 if turnover_thousands is not None else None,
            price_change=parse_number(row[7]),
            transaction_count=parse_number(row[8], integer=True),
            source=self.source,
            warning_message=warning,
        )

    def _request_month(self, symbol: str, target: date):
        return self._get_json(
            self.endpoint,
            {"code": symbol, "date": f"{target:%Y/%m}/01", "response": "json"},
            headers={"Referer": "https://www.tpex.org.tw/zh-tw/mainboard/trading/info/stock-pricing.html"},
        )
