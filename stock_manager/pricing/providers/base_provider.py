from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import date
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from stock_manager.pricing.models import MarketQuote


class ProviderError(RuntimeError):
    """報價來源連線、格式或驗證錯誤。"""


class NoDataError(ProviderError):
    """來源正常回應，但指定股票沒有可用成交資料。"""


class PriceProvider(ABC):
    source = ""
    exchange = ""

    def __init__(self, timeout: float = 12.0):
        self.timeout = timeout

    @abstractmethod
    def fetch_latest(self, symbol: str, as_of: date | None = None) -> MarketQuote:
        raise NotImplementedError

    def _get_json(
        self,
        url: str,
        params: dict[str, object],
        *,
        headers: dict[str, str] | None = None,
    ) -> Any:
        target = f"{url}?{urlencode(params)}"
        request_headers = {
            "Accept": "application/json",
            "User-Agent": "LeveragedStockAccumulationManager/1.1",
        }
        request_headers.update(headers or {})
        try:
            with urlopen(Request(target, headers=request_headers), timeout=self.timeout) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                return json.loads(response.read().decode(charset))
        except HTTPError as exc:
            raise ProviderError(f"HTTP {exc.code}") from exc
        except URLError as exc:
            raise ProviderError(f"網路連線失敗：{exc.reason}") from exc
        except TimeoutError as exc:
            raise ProviderError("連線逾時") from exc
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProviderError("來源回傳的資料格式無法解析") from exc


def parse_number(value: object, *, integer: bool = False):
    text = str(value or "").strip().replace(",", "").replace("+", "")
    if text in {"", "--", "---", "-", "除權", "除息", "除權息"}:
        return None
    try:
        if integer:
            return int(float(text))
        from decimal import Decimal

        return Decimal(text)
    except (ValueError, ArithmeticError) as exc:
        raise ProviderError(f"無法解析數值：{value}") from exc


def roc_date(value: object) -> date:
    try:
        year, month, day = (int(part) for part in str(value).strip().split("/"))
        return date(year + 1911, month, day)
    except (TypeError, ValueError) as exc:
        raise ProviderError(f"無法解析民國日期：{value}") from exc

