from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum


class PriceUpdateStatus(StrEnum):
    SUCCESS = "SUCCESS"
    FALLBACK = "FALLBACK"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


@dataclass(frozen=True)
class MarketQuote:
    symbol: str
    name: str
    exchange: str
    trade_date: date
    close: Decimal
    open: Decimal | None = None
    high: Decimal | None = None
    low: Decimal | None = None
    volume_shares: int | None = None
    turnover_twd: int | None = None
    transaction_count: int | None = None
    price_change: Decimal | None = None
    source: str = ""
    quote_type: str = "CLOSE"
    fetched_at: datetime = field(default_factory=lambda: datetime.now().astimezone())
    warning_message: str = ""


@dataclass(frozen=True)
class SecurityUpdateResult:
    security_id: int
    symbol: str
    name: str
    status: PriceUpdateStatus
    source: str = ""
    trade_date: date | None = None
    retry_count: int = 0
    message: str = ""


@dataclass(frozen=True)
class PriceUpdateSummary:
    run_id: int
    trigger_type: str
    started_at: datetime
    completed_at: datetime
    results: tuple[SecurityUpdateResult, ...]

    @property
    def planned_count(self) -> int:
        return len(self.results)

    @property
    def success_count(self) -> int:
        return sum(r.status == PriceUpdateStatus.SUCCESS for r in self.results)

    @property
    def fallback_count(self) -> int:
        return sum(r.status == PriceUpdateStatus.FALLBACK for r in self.results)

    @property
    def failed_count(self) -> int:
        return sum(r.status == PriceUpdateStatus.FAILED for r in self.results)

    @property
    def skipped_count(self) -> int:
        return sum(r.status == PriceUpdateStatus.SKIPPED for r in self.results)

    @property
    def status(self) -> str:
        if self.failed_count and (self.success_count or self.fallback_count):
            return "PARTIAL"
        if self.failed_count:
            return "FAILED"
        return "SUCCESS"

