from __future__ import annotations

from datetime import date, datetime

from PySide6.QtCore import QObject, QThread, QTimer, Signal

from stock_manager.database import PortfolioRepository

from .price_update_service import PriceUpdateService


class PriceUpdateWorker(QThread):
    completed = Signal(object)
    failed = Signal(str)
    progress = Signal(int, int, str)

    def __init__(self, repository: PortfolioRepository, kwargs: dict, parent=None):
        super().__init__(parent)
        self.repository = repository
        self.kwargs = kwargs

    def run(self):
        try:
            summary = PriceUpdateService(self.repository).update(
                **self.kwargs,
                progress_callback=lambda done, total, result: self.progress.emit(done, total, result.symbol),
            )
            self.completed.emit(summary)
        except Exception as exc:
            self.failed.emit(str(exc))


class PriceScheduler(QObject):
    update_started = Signal(str)
    update_finished = Signal(object)
    update_failed = Signal(str)
    update_progress = Signal(int, int, str)

    def __init__(self, repository: PortfolioRepository, parent=None):
        super().__init__(parent)
        self.repository = repository
        self.worker: PriceUpdateWorker | None = None
        self._executed_slots: set[str] = set()
        self.timer = QTimer(self)
        self.timer.setInterval(30_000)
        self.timer.timeout.connect(self._check_schedule)

    @property
    def is_running(self) -> bool:
        return bool(self.worker and self.worker.isRunning())

    def start(self) -> None:
        self.timer.start()
        settings = self.repository.settings()
        if settings.get("price_auto_update_on_startup", "1") == "1":
            QTimer.singleShot(800, lambda: self.trigger("STARTUP", force=False))

    def trigger(self, trigger_type: str, *, security_ids: list[int] | None = None, force: bool = False) -> bool:
        if self.is_running:
            return False
        kwargs = {"trigger_type": trigger_type, "security_ids": security_ids, "force": force}
        self.worker = PriceUpdateWorker(self.repository, kwargs, self)
        self.worker.completed.connect(self._completed)
        self.worker.failed.connect(self._failed)
        self.worker.progress.connect(self.update_progress.emit)
        self.worker.finished.connect(self._cleanup)
        self.update_started.emit(trigger_type)
        self.worker.start()
        return True

    def _check_schedule(self) -> None:
        settings = self.repository.settings()
        if settings.get("price_schedule_enabled", "1") != "1" or self.is_running:
            return
        now = datetime.now().astimezone()
        if now.weekday() >= 5:
            return
        valid_times = {item.strip() for item in settings.get("price_schedule_times", "14:30,15:00,17:00").split(",")}
        slot = f"{date.today().isoformat()} {now:%H:%M}"
        if f"{now:%H:%M}" in valid_times and slot not in self._executed_slots:
            self._executed_slots.add(slot)
            self.trigger("SCHEDULED", force=False)
        # 避免長時間開啟程式後集合無限成長。
        today = date.today().isoformat()
        self._executed_slots = {item for item in self._executed_slots if item.startswith(today)}

    def _completed(self, summary) -> None:
        self.update_finished.emit(summary)

    def _failed(self, message: str) -> None:
        self.update_failed.emit(message)

    def _cleanup(self) -> None:
        if self.worker:
            self.worker.deleteLater()
        self.worker = None
