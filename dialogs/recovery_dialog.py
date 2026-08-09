from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel,
    QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from stock_manager.database import PortfolioRepository
from stock_manager.domain import OptimizationMode, RecoveryMode, zh
from stock_manager.services import RecoveryService
from stock_manager.ui import COLORS
from stock_manager.utils.formatting import currency


class RecoveryDialog(QDialog):
    def __init__(self, repository: PortfolioRepository, initial_lot_id: str | None = None, parent=None):
        super().__init__(parent); self.setWindowTitle("回本賣出模擬器"); self.resize(900, 560)
        self.service = RecoveryService(repository)
        root = QVBoxLayout(self); form = QFormLayout(); root.addLayout(form)
        self.lot = QComboBox()
        for row in repository.master_rows():
            if row["remaining_shares"] > 0:
                self.lot.addItem(f"{row['id']}｜{row['symbol']} {row['security_name']}｜剩 {row['remaining_shares']:,} 股", row)
        if initial_lot_id:
            for i in range(self.lot.count()):
                if self.lot.itemData(i)["id"] == initial_lot_id: self.lot.setCurrentIndex(i); break
        self.price = QDoubleSpinBox(); self.price.setRange(0.01, 100_000_000); self.price.setDecimals(2)
        self.target_mode = QComboBox()
        for item in RecoveryMode: self.target_mode.addItem(zh(item), item)
        self.optimization = QComboBox()
        for item in OptimizationMode: self.optimization.addItem(zh(item), item)
        self.tolerance = QDoubleSpinBox(); self.tolerance.setRange(0, 100_000_000); self.tolerance.setDecimals(2); self.tolerance.setPrefix("NT$ ")
        self.custom_target = QDoubleSpinBox(); self.custom_target.setRange(0, 1_000_000_000); self.custom_target.setDecimals(2); self.custom_target.setPrefix("NT$ ")
        self.summary = QLabel(); self.summary.setWordWrap(True)
        for label, widget in (("買進批次", self.lot), ("模擬賣出價格", self.price), ("回收目標", self.target_mode),
                              ("最佳化方式", self.optimization), ("回本容許差額", self.tolerance), ("自訂回收目標", self.custom_target), ("批次資訊", self.summary)):
            form.addRow(label, widget)
        button = QPushButton("重新計算"); button.setProperty("role","primary"); button.clicked.connect(self.calculate); root.addWidget(button)
        self.table = QTableWidget(0, 9); self.table.setHorizontalHeaderLabels(["方案", "賣出股數", "成交總額", "手續費", "交易稅", "預估淨回收", "回本差額", "剩餘股數", "策略判定"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers); self.table.setAlternatingRowColors(True); root.addWidget(self.table)
        note = QLabel("模擬不會寫入交易或修改持股；實際成交後仍須使用「新增賣出」。帳務回收率不會因容許差額而偽裝成 100%。")
        note.setProperty("role","secondary"); root.addWidget(note)
        close = QPushButton("關閉"); close.clicked.connect(self.accept); line = QHBoxLayout(); line.addStretch(); line.addWidget(close); root.addLayout(line)
        self.lot.currentIndexChanged.connect(self._load_lot); self._load_lot()

    def _load_lot(self):
        row = self.lot.currentData()
        if not row: return
        self.price.setValue(float(row["current_price"] or row["buy_price"]))
        self.tolerance.setValue(float(row["recovery_tolerance_amount"]))
        self.summary.setText(f"原始投入 {currency(row['original_capital'])}｜已回收 {currency(row['net_cash_recovered'])}｜完整成本 {currency(row['full_cost'])}｜目前 {row['remaining_shares']:,} 股")
        self.calculate()

    def calculate(self):
        row = self.lot.currentData()
        if not row: return
        try:
            _, target, options = self.service.simulate(row["id"], self.price.value(), self.target_mode.currentData(), self.optimization.currentData(), self.tolerance.value(), self.custom_target.value())
            self.table.setRowCount(len(options))
            for r, option in enumerate(options):
                status = "容許差額內可完成" if option.eligible_with_tolerance else "尚未達容許範圍"
                if option.fully_recovered: status = "完整達到回收目標"
                values = ["建議" if option.recommended else "相鄰方案", f"{option.shares:,}", currency(option.gross_amount), currency(option.commission), currency(option.tax), currency(option.net_cash), currency(option.difference), f"{option.remaining_shares:,}", status]
                for c, value in enumerate(values):
                    item = QTableWidgetItem(value)
                    if option.recommended:
                        item.setBackground(QColor(COLORS["success_soft"])); item.setForeground(QColor(COLORS["success"]))
                    self.table.setItem(r, c, item)
            self.table.resizeColumnsToContents()
            self.summary.setText(self.summary.text().split("｜回收目標")[0] + f"｜回收目標 {currency(target)}")
        except Exception as exc:
            QMessageBox.warning(self, "無法模擬", str(exc))
