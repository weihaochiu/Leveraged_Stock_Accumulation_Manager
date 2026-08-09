from __future__ import annotations

from PySide6.QtWidgets import QDialog, QGridLayout, QHBoxLayout, QLabel, QPushButton, QTabWidget, QVBoxLayout, QWidget
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from stock_manager.database import PortfolioRepository
from stock_manager.domain import ZH, StrategyStatus
from stock_manager.services import PortfolioService
from stock_manager.utils.formatting import currency


class Chart(QWidget):
    def __init__(self, title: str, labels: list[str], values: list[float], color: str = "#3B82F6", horizontal: bool = False, parent=None):
        super().__init__(parent); layout = QVBoxLayout(self); figure = Figure(figsize=(6, 4), tight_layout=True); canvas = FigureCanvasQTAgg(figure); layout.addWidget(canvas)
        ax = figure.add_subplot(111)
        if horizontal: ax.barh(labels, values, color=color)
        else: ax.bar(labels, values, color=color); ax.tick_params(axis="x", rotation=25)
        ax.set_title(title); ax.grid(axis="x" if horizontal else "y", alpha=.2); canvas.draw()


class AnalysisDialog(QDialog):
    def __init__(self, repository: PortfolioRepository, parent=None):
        super().__init__(parent); self.setWindowTitle("績效分析"); self.resize(1200, 800)
        self.repository = repository; self.service = PortfolioService(repository); root = QVBoxLayout(self)
        tabs = QTabWidget(); root.addWidget(tabs)
        overview = QWidget(); ov = QVBoxLayout(overview); cards = QGridLayout(); ov.addLayout(cards)
        dashboard = repository.dashboard()
        items = [("已回本持股市值", dashboard["free_share_value"], True), ("尚未回收本金", dashboard["capital_at_risk"], True),
                 ("目前貸款餘額", dashboard["loan_balance"], True), ("股票總市值", dashboard["market_value"], False),
                 ("累積回收現金", dashboard["net_cash_recovered"], False), ("超額回收現金", dashboard["cash_surplus"], False),
                 ("累積現金股利", dashboard["dividends"], False), ("累積貸款利息", dashboard["loan_interest"], False)]
        for i, (label, value, primary) in enumerate(items):
            card = QLabel(f"<div style='font-size:13px;color:#64748b'>{label}</div><div style='font-size:{'24' if primary else '20'}px;font-weight:700'>{currency(value)}</div>")
            card.setStyleSheet("QLabel{background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:14px}")
            cards.addWidget(card, i // 4, i % 4)
        status = self.service.recovery_status_counts(); labels = [ZH.get(StrategyStatus(k), k) for k in status]; values = list(status.values())
        ov.addWidget(Chart("買進批次回收狀態分布", labels, values, "#10B981")); tabs.addTab(overview, "策略總覽")
        capital = self.service.capital_at_risk_by_stock(); tabs.addTab(Chart("尚未回收本金（依股票）", list(capital), list(capital.values()), "#F59E0B", True), "本金回收")
        ages = self.service.unrecovered_age_buckets(); tabs.addTab(Chart("尚未回本批次年齡（尚未回收本金）", list(ages), [v["capital"] for v in ages.values()], "#EF4444"), "批次年齡")
        note = QLabel("市場環境分析需先匯入 Benchmark 歷史資料；本版保留資料與分析介面，不以目標報酬率單獨推論回本效率。")
        note.setWordWrap(True); note.setStyleSheet("padding:30px;font-size:15px")
        wrapper = QWidget(); wv = QVBoxLayout(wrapper); wv.addWidget(note); wv.addStretch(); tabs.addTab(wrapper, "市場環境")
        close = QPushButton("關閉"); close.clicked.connect(self.accept); line = QHBoxLayout(); line.addStretch(); line.addWidget(close); root.addLayout(line)
