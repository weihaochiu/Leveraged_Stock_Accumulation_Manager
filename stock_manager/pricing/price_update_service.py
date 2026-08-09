from __future__ import annotations

import logging
import time
from dataclasses import replace
from datetime import date, datetime
from typing import Callable, Iterable

from stock_manager.database import PortfolioRepository

from .models import MarketQuote, PriceUpdateStatus, PriceUpdateSummary, SecurityUpdateResult
from .price_validator import PriceValidationError, validate_quote
from .providers import FinMindProvider, NoDataError, PriceProvider, ProviderError, TPExProvider, TWSEProvider


LOGGER = logging.getLogger(__name__)


class PriceUpdateService:
    """只更新目前持股，逐檔隔離失敗並記錄實際來源。"""

    def __init__(
        self,
        repository: PortfolioRepository,
        *,
        providers: dict[str, PriceProvider] | None = None,
        fallback_provider: PriceProvider | None = None,
        retry_delays: Iterable[float] | None = None,
        sleeper: Callable[[float], None] = time.sleep,
    ):
        self.repository = repository
        settings = repository.settings()
        timeout = _float_setting(settings, "price_request_timeout_seconds", 12.0)
        self.providers = providers or {
            "TWSE": TWSEProvider(timeout),
            "TPEx": TPExProvider(timeout),
        }
        if fallback_provider is not None:
            self.fallback_provider = fallback_provider
        elif settings.get("price_finmind_fallback_enabled") == "1":
            self.fallback_provider = FinMindProvider(settings.get("price_finmind_token", ""), timeout)
        else:
            self.fallback_provider = None
        self.retry_delays = tuple(retry_delays if retry_delays is not None else _retry_delays(settings))
        self.sleeper = sleeper
        self.anomaly_threshold = _float_setting(settings, "price_anomaly_threshold_pct", 20.0)

    def update(
        self,
        *,
        trigger_type: str,
        security_ids: list[int] | None = None,
        force: bool = False,
        as_of: date | None = None,
        progress_callback: Callable[[int, int, SecurityUpdateResult], None] | None = None,
    ) -> PriceUpdateSummary:
        as_of = as_of or date.today()
        started_at = datetime.now().astimezone()
        securities = self.repository.list_held_securities(security_ids)
        run_id = self.repository.create_price_update_run(trigger_type, len(securities), started_at)
        results: list[SecurityUpdateResult] = []
        for security in securities:
            try:
                result = self._update_one(security, as_of=as_of, force=force, trigger_type=trigger_type)
            except Exception as exc:  # 個股失敗不得中止整個批次
                LOGGER.exception("更新 %s 時發生未預期錯誤", security["symbol"])
                result = SecurityUpdateResult(
                    security_id=security["id"], symbol=security["symbol"], name=security["name"],
                    status=PriceUpdateStatus.FAILED, message=f"未預期錯誤：{exc}",
                )
            self.repository.add_price_update_result(run_id, result)
            results.append(result)
            if progress_callback:
                progress_callback(len(results), len(securities), result)

        completed_at = datetime.now().astimezone()
        summary = PriceUpdateSummary(run_id, trigger_type, started_at, completed_at, tuple(results))
        self.repository.finish_price_update_run(
            run_id,
            completed_at,
            {
                "success": summary.success_count,
                "fallback": summary.fallback_count,
                "failed": summary.failed_count,
                "skipped": summary.skipped_count,
            },
            summary.status,
        )
        return summary

    def _update_one(self, security: dict, *, as_of: date, force: bool, trigger_type: str) -> SecurityUpdateResult:
        latest = self.repository.latest_price(security["id"])
        if not force and self._should_skip(latest, as_of, trigger_type):
            return SecurityUpdateResult(
                security["id"], security["symbol"], security["name"], PriceUpdateStatus.SKIPPED,
                source=str((latest or {}).get("source") or ""),
                trade_date=date.fromisoformat(latest["price_date"]) if latest else None,
                message="已有今天價格或今天已確認最新可取得資料",
            )

        market = _normalize_market(security.get("market"))
        provider_names = [market] if market else ["TWSE", "TPEx"]
        errors: list[str] = []
        total_retries = 0
        quote: MarketQuote | None = None
        for provider_name in provider_names:
            provider = self.providers.get(provider_name)
            if not provider:
                continue
            try:
                quote, retries = self._fetch_with_retry(provider, security["symbol"], as_of)
                total_retries += retries
                quote = validate_quote(
                    quote,
                    requested_symbol=security["symbol"],
                    expected_exchange=provider_name,
                    previous_close=(latest or {}).get("price"),
                    anomaly_threshold_pct=self.anomaly_threshold,
                )
                self.repository.record_provider_health(provider.source, True)
                break
            except (NoDataError, ProviderError, PriceValidationError) as exc:
                total_retries += int(getattr(exc, "retry_count", 0))
                errors.append(f"{provider.source}：{exc}")
                self.repository.record_provider_health(provider.source, False, str(exc))

        if quote is not None:
            self.repository.save_market_quote(security["id"], quote)
            if not market and quote.exchange:
                self.repository.update_security_market(security["id"], quote.exchange)
            message = quote.warning_message or "更新成功"
            return SecurityUpdateResult(
                security["id"], security["symbol"], security["name"], PriceUpdateStatus.SUCCESS,
                quote.source, quote.trade_date, total_retries, message,
            )

        if self.fallback_provider is not None:
            provider = self.fallback_provider
            try:
                fallback, retries = self._fetch_with_retry(provider, security["symbol"], as_of)
                total_retries += retries
                fallback = replace(fallback, exchange=market or "")
                fallback = validate_quote(
                    fallback,
                    requested_symbol=security["symbol"],
                    expected_exchange=market or None,
                    previous_close=(latest or {}).get("price"),
                    anomaly_threshold_pct=self.anomaly_threshold,
                )
                self.repository.save_market_quote(security["id"], fallback)
                self.repository.record_provider_health(provider.source, True)
                return SecurityUpdateResult(
                    security["id"], security["symbol"], security["name"], PriceUpdateStatus.FALLBACK,
                    fallback.source, fallback.trade_date, total_retries,
                    fallback.warning_message or "官方來源失敗，已使用備援來源",
                )
            except (NoDataError, ProviderError, PriceValidationError) as exc:
                total_retries += int(getattr(exc, "retry_count", 0))
                errors.append(f"{provider.source}：{exc}")
                self.repository.record_provider_health(provider.source, False, str(exc))

        cache_note = "；沿用最近成功價格" if latest else "；目前沒有可沿用價格"
        return SecurityUpdateResult(
            security["id"], security["symbol"], security["name"], PriceUpdateStatus.FAILED,
            retry_count=total_retries,
            message="｜".join(errors) + cache_note,
        )

    def _fetch_with_retry(self, provider: PriceProvider, symbol: str, as_of: date) -> tuple[MarketQuote, int]:
        attempts = len(self.retry_delays) + 1
        last_error: Exception | None = None
        for attempt in range(attempts):
            try:
                return provider.fetch_latest(symbol, as_of), attempt
            except NoDataError:
                # 查無資料通常代表市場不符、停牌或尚未發布，重送相同請求沒有幫助。
                raise
            except ProviderError as exc:
                last_error = exc
                if attempt < len(self.retry_delays):
                    self.sleeper(self.retry_delays[attempt])
        failure = ProviderError(str(last_error or "來源更新失敗"))
        failure.retry_count = len(self.retry_delays)
        raise failure

    @staticmethod
    def _should_skip(latest: dict | None, as_of: date, trigger_type: str) -> bool:
        if not latest:
            return False
        if str(latest.get("price_date") or "") == as_of.isoformat():
            return True
        fetched = str(latest.get("fetched_at") or latest.get("updated_at") or "")
        return trigger_type == "STARTUP" and fetched[:10] == as_of.isoformat()


def _normalize_market(value: object) -> str | None:
    text = str(value or "").strip().upper()
    if text in {"TWSE", "上市"}:
        return "TWSE"
    if text in {"TPEX", "TPEx".upper(), "上櫃", "OTC"}:
        return "TPEx"
    return None


def _float_setting(settings: dict[str, str], key: str, default: float) -> float:
    try:
        return float(settings.get(key, default))
    except (TypeError, ValueError):
        return default


def _retry_delays(settings: dict[str, str]) -> tuple[float, ...]:
    try:
        values = tuple(float(item.strip()) for item in settings.get("price_retry_delays_seconds", "2,5").split(",") if item.strip())
        return values[:3]
    except ValueError:
        return (2.0, 5.0)
