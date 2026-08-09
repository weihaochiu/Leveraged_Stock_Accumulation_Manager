from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal

from .models import MarketQuote


class PriceValidationError(ValueError):
    pass


def validate_quote(
    quote: MarketQuote,
    *,
    requested_symbol: str,
    expected_exchange: str | None = None,
    previous_close: object | None = None,
    anomaly_threshold_pct: object = 20,
) -> MarketQuote:
    if quote.symbol != requested_symbol:
        raise PriceValidationError("回傳股票代號與請求不一致")
    if expected_exchange and quote.exchange and quote.exchange != expected_exchange:
        raise PriceValidationError("回傳市場與股票設定不一致")
    if quote.close <= 0:
        raise PriceValidationError("收盤價必須大於 0")
    if quote.trade_date > date.today():
        raise PriceValidationError("交易日期不得晚於今天")

    warning_parts = [quote.warning_message] if quote.warning_message else []
    previous = Decimal(str(previous_close)) if previous_close not in (None, "", 0) else Decimal("0")
    threshold = Decimal(str(anomaly_threshold_pct or 20))
    if previous > 0:
        difference = abs((quote.close - previous) / previous * 100)
        if difference >= threshold:
            warning_parts.append(
                f"與前次價格差異 {difference:.2f}%，請確認是否有除權息、分割、減資或恢復交易。"
            )
    return replace(quote, warning_message=" ".join(warning_parts))

