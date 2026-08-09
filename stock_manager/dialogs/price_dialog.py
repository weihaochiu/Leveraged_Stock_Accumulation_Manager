from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QTabWidget, QVBoxLayout, QWidget,
)

from stock_manager.database import PortfolioRepository
from stock_manager.utils.formatting import currency


class PriceStatusDialog(QDialog):
    def __init__(self, repository: PortfolioRepository, parent=None):
        super().__init__(parent)
        self.repository = repository
        self.setWindowTitle("目前持股股價狀態")
        self.resize(1180, 620)
        root = QVBoxLayout(self)
        note = QLabel("僅顯示目前仍有持股的股票。手動覆寫只優先於同一交易日，自動更新不會因此永久停用。")
        note.setWordWrap(True)
        root.addWidget(note)
        tabs = QTabWidget(); root.addWidget(tabs)
        current = QWidget(); current_layout = QVBoxLayout(current)
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "股票", "市場", "目前價格", "漲跌", "價格日期", "取得時間",
            "來源", "狀態", "持有股數", "訊息",
        ])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        current_layout.addWidget(self.table); tabs.addTab(current, "目前持股價格")
        history = QWidget(); history_layout = QVBoxLayout(history)
        self.history = QTableWidget(); self.history.setColumnCount(9)
        self.history.setHorizontalHeaderLabels(["批次", "開始時間", "觸發方式", "預計", "官方成功", "備援成功", "失敗", "略過", "狀態"])
        self.history.setEditTriggers(QTableWidget.NoEditTriggers); history_layout.addWidget(self.history); tabs.addTab(history, "更新批次紀錄")
        line = QHBoxLayout()
        refresh = QPushButton("重新整理")
        refresh.clicked.connect(self.refresh)
        close = QPushButton("關閉")
        close.clicked.connect(self.accept)
        line.addWidget(refresh)
        line.addStretch()
        line.addWidget(close)
        root.addLayout(line)
        self.refresh()

    def refresh(self):
        rows = self.repository.price_status_rows()
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            change = row.get("price_change")
            warning = row.get("warning_message") or row.get("last_error") or ""
            values = [
                f"{row['symbol']} {row['name']}",
                {"TWSE": "上市", "TPEx": "上櫃", "TW": "待辨識"}.get(row.get("market"), row.get("market") or "待辨識"),
                currency(row.get("price")) if row.get("price") else "—",
                f"{float(change):+,.2f}" if change is not None else "—",
                row.get("price_date") or "—",
                row.get("fetched_at") or row.get("updated_at") or "—",
                {"TWSE": "證交所", "TPEx": "櫃買中心", "FinMind": "FinMind 備援", "MANUAL": "手動"}.get(row.get("source"), row.get("source") or "—"),
                row.get("price_status") or "—",
                f"{int(float(row.get('held_shares') or 0)):,}",
                warning,
            ]
            for c, value in enumerate(values):
                self.table.setItem(r, c, QTableWidgetItem(str(value)))
        self.table.resizeColumnsToContents()
        self.table.setColumnWidth(9, min(420, max(180, self.table.columnWidth(9))))
        runs = self.repository.price_update_runs()
        self.history.setRowCount(len(runs))
        trigger_labels = {"STARTUP": "程式啟動", "SCHEDULED": "盤後排程", "MANUAL_ALL": "手動全部", "MANUAL_SINGLE": "手動單檔"}
        status_labels = {"SUCCESS": "完成", "PARTIAL": "部分成功", "FAILED": "失敗", "RUNNING": "進行中"}
        for r, run in enumerate(runs):
            values = [run["id"], run["started_at"], trigger_labels.get(run["trigger_type"], run["trigger_type"]), run["planned_count"],
                      run["success_count"], run["fallback_success_count"], run["failed_count"], run["skipped_count"], status_labels.get(run["status"], run["status"])]
            for c, value in enumerate(values): self.history.setItem(r, c, QTableWidgetItem(str(value)))
        self.history.resizeColumnsToContents()
