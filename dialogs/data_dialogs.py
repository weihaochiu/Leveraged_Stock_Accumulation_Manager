from __future__ import annotations

from datetime import date
from pathlib import Path

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFileDialog,
    QFormLayout, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QMessageBox,
    QPushButton, QSpinBox, QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget,
)

from stock_manager.database import PortfolioRepository
from stock_manager.domain import FundingType, dec, money, zh
from stock_manager.import_export import BackupService, ExcelService
from stock_manager.ui import COLORS


class SettingsDialog(QDialog):
    def __init__(self, repository: PortfolioRepository, parent=None):
        super().__init__(parent); self.setWindowTitle("設定"); self.setMinimumWidth(620); self.repository = repository; s = repository.settings()
        root = QVBoxLayout(self); tabs = QTabWidget(); root.addWidget(tabs)
        trade = QWidget(); tf = QFormLayout(trade)
        self.commission_rate = self._spin(0, 1, 6, float(s["commission_rate"])); self.discount = self._spin(0, 1, 3, float(s["commission_discount"]))
        self.minimum = self._spin(0, 10000, 2, float(s["minimum_commission"])); self.tax = self._spin(0, 1, 6, float(s["sell_tax_rate"]))
        for label, widget in (("手續費率（小數）", self.commission_rate), ("手續費折扣（小數）", self.discount), ("最低手續費", self.minimum), ("賣出交易稅率（小數）", self.tax)): tf.addRow(label, widget)
        tabs.addTab(trade, "交易設定")
        strategy = QWidget(); sf = QFormLayout(strategy)
        self.target = self._spin(-99, 1000, 2, float(s["default_target_return_pct"])); self.near = self._spin(0, 100, 2, float(s["near_target_alert_pct"]))
        self.budget = self._spin(0, 1e9, 2, float(s["default_buy_budget"])); self.tolerance = self._spin(0, 1e9, 2, float(s["recovery_tolerance_amount"]))
        for label, widget in (("新股票預設目標報酬 %", self.target), ("接近目標提示範圍 %", self.near), ("預設策略單位預算", self.budget), ("預設回本容許差額", self.tolerance)): sf.addRow(label, widget)
        tabs.addTab(strategy, "策略設定")
        stock = QWidget(); stf = QFormLayout(stock); self.stock_strategy = QComboBox()
        for row in repository.list_securities(): self.stock_strategy.addItem(f"{row['symbol']} {row['name']}", row)
        self.stock_target = self._spin(-99,1000,2,10); self.stock_near = self._spin(0,100,2,2); self.stock_budget = self._spin(0,1e9,2,10000); self.stock_tolerance = self._spin(0,1e9,2,100)
        self.stock_funding = QComboBox()
        for item in FundingType: self.stock_funding.addItem(zh(item),item.value)
        for label,widget in (("股票",self.stock_strategy),("預設目標報酬 %",self.stock_target),("接近目標提示 %",self.stock_near),("策略單位預算",self.stock_budget),("回本容許差額",self.stock_tolerance),("預設資金來源",self.stock_funding)): stf.addRow(label,widget)
        self.stock_strategy.currentIndexChanged.connect(self._load_stock_strategy); tabs.addTab(stock,"個股策略"); self._load_stock_strategy()
        data = QWidget(); df = QFormLayout(data); self.backup_start = QCheckBox("程式啟動時自動完整備份"); self.backup_start.setChecked(s["backup_on_startup"] == "1")
        self.frequency = QComboBox(); self.frequency.addItem("每日第一次啟動", "DAILY_FIRST"); self.frequency.addItem("每次啟動", "EVERY_START")
        idx = self.frequency.findData(s["backup_frequency"]); self.frequency.setCurrentIndex(max(0, idx)); df.addRow(self.backup_start); df.addRow("啟動備份頻率", self.frequency)
        broker_button = QPushButton("新增券商帳戶"); broker_button.clicked.connect(self._add_broker); df.addRow("券商設定", broker_button); tabs.addTab(data, "資料與券商")
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel); buttons.button(QDialogButtonBox.Save).setText("儲存"); buttons.button(QDialogButtonBox.Cancel).setText("取消")
        buttons.button(QDialogButtonBox.Save).setProperty("role","primary")
        buttons.accepted.connect(self.save); buttons.rejected.connect(self.reject); root.addWidget(buttons)

    @staticmethod
    def _spin(minimum, maximum, decimals, value):
        w = QDoubleSpinBox(); w.setRange(minimum, maximum); w.setDecimals(decimals); w.setValue(value); return w

    def _add_broker(self):
        name, ok = QInputDialog.getText(self, "新增券商帳戶", "券商／帳戶顯示名稱")
        if ok and name.strip():
            self.repository.add_broker(name.strip()); QMessageBox.information(self, "完成", "券商帳戶已建立；重新開啟輸入視窗即可選用。")

    def _load_stock_strategy(self):
        row=self.stock_strategy.currentData()
        if not row: return
        self.stock_target.setValue(row["default_target_return_pct"]); self.stock_near.setValue(row["near_target_alert_pct"]); self.stock_budget.setValue(row["default_buy_budget"]); self.stock_tolerance.setValue(row["recovery_tolerance_amount"])
        index=self.stock_funding.findData(row["default_funding_preference"]); self.stock_funding.setCurrentIndex(max(0,index))

    def save(self):
        values = {"commission_rate": self.commission_rate.value(), "commission_discount": self.discount.value(), "minimum_commission": self.minimum.value(),
                  "sell_tax_rate": self.tax.value(), "default_target_return_pct": self.target.value(), "near_target_alert_pct": self.near.value(),
                  "default_buy_budget": self.budget.value(), "recovery_tolerance_amount": self.tolerance.value(), "backup_on_startup": int(self.backup_start.isChecked()),
                  "backup_frequency": self.frequency.currentData()}
        for key, value in values.items(): self.repository.set_setting(key, value)
        row=self.stock_strategy.currentData()
        if row:
            self.repository.update_security_strategy(row["id"],{"default_target_return_pct":self.stock_target.value(),"near_target_alert_pct":self.stock_near.value(),"default_buy_budget":self.stock_budget.value(),"recovery_tolerance_amount":self.stock_tolerance.value(),"default_funding_preference":self.stock_funding.currentData()})
        self.accept()


class ExcelImportDialog(QDialog):
    FIELDS = [
        ("股票代號", "symbol", True), ("股票名稱", "name", True), ("買入日期", "buy_date", True),
        ("買入價格", "buy_price", True), ("原始股數", "original_shares", True), ("買入手續費", "buy_fee", False),
        ("券商下單編號", "broker_order_id", False), ("備註", "note", False),
    ]

    def __init__(self, repository: PortfolioRepository, parent=None):
        super().__init__(parent); self.setWindowTitle("從 Excel 匯入買入批次"); self.resize(950, 700); self.repository = repository; self.excel = ExcelService(repository); self.headers=[]; self.rows=[]
        root = QVBoxLayout(self); top = QHBoxLayout(); self.path = QLineEdit(); browse = QPushButton("選擇 Excel"); browse.clicked.connect(self.choose); top.addWidget(self.path); top.addWidget(browse); root.addLayout(top)
        options = QHBoxLayout(); self.broker = QComboBox(); self.broker.addItem("未指定", None)
        for row in repository.list_brokers(): self.broker.addItem(row["name"], row["id"])
        self.funding = QComboBox()
        for item in FundingType: self.funding.addItem(zh(item), item.value)
        self.loan = QComboBox(); self.loan.addItem("不使用貸款", None)
        for row in repository.list_loans(): self.loan.addItem(f"{row['id']} {row['name']}", row["id"])
        options.addWidget(QLabel("本次券商")); options.addWidget(self.broker); options.addWidget(QLabel("資金來源")); options.addWidget(self.funding); options.addWidget(QLabel("貸款帳戶")); options.addWidget(self.loan); root.addLayout(options)
        self.mapping = QFormLayout(); self.combos = {}
        mapping_widget = QWidget(); mapping_widget.setLayout(self.mapping); root.addWidget(mapping_widget)
        self.table = QTableWidget(); root.addWidget(self.table)
        note = QLabel("匯入前僅預覽，不修改原 Excel。正式寫入時逐列驗證；任何錯誤列都會列出，不會靜默跳過。")
        note.setProperty("role","secondary"); root.addWidget(note)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); buttons.button(QDialogButtonBox.Ok).setText("確認匯入"); buttons.button(QDialogButtonBox.Cancel).setText("取消")
        buttons.button(QDialogButtonBox.Ok).setProperty("role","primary")
        buttons.accepted.connect(self.commit); buttons.rejected.connect(self.reject); root.addWidget(buttons)

    def choose(self):
        path, _ = QFileDialog.getOpenFileName(self, "選擇 Excel", "", "Excel 檔案 (*.xlsx *.xlsm)")
        if not path: return
        self.path.setText(path)
        try:
            self.headers, self.rows = self.excel.preview(path, limit=5000); self._build_mapping(); self._preview()
        except Exception as exc: QMessageBox.warning(self, "無法讀取", str(exc))

    def _build_mapping(self):
        while self.mapping.rowCount(): self.mapping.removeRow(0)
        self.combos = {}
        for label, key, required in self.FIELDS:
            combo = QComboBox(); combo.addItem("不匯入", None)
            for index, header in enumerate(self.headers): combo.addItem(header, index)
            candidates = [label, key]
            for i, header in enumerate(self.headers):
                if str(header).strip() in candidates: combo.setCurrentIndex(i + 1); break
            self.mapping.addRow(label + (" *" if required else ""), combo); self.combos[key] = combo

    def _preview(self):
        self.table.setColumnCount(len(self.headers)); self.table.setHorizontalHeaderLabels(self.headers); self.table.setRowCount(min(100, len(self.rows)))
        for r, row in enumerate(self.rows[:100]):
            for c, value in enumerate(row): self.table.setItem(r, c, QTableWidgetItem(str(value or "")))
        self.table.resizeColumnsToContents()

    def commit(self):
        required = [key for _, key, req in self.FIELDS if req]
        if not self.rows: QMessageBox.warning(self, "尚無資料", "請先選擇 Excel 檔案"); return
        if any(self.combos[k].currentData() is None for k in required): QMessageBox.warning(self, "欄位不足", "請完成所有 * 必填欄位的對應"); return
        successes, errors = 0, []
        for number, row in enumerate(self.rows, start=2):
            try:
                value = lambda key, default="": row[self.combos[key].currentData()] if self.combos[key].currentData() is not None else default
                raw_date = value("buy_date")
                if hasattr(raw_date, "date"): buy_date = raw_date.date().isoformat()
                else: buy_date = str(raw_date).replace("/", "-")[:10]
                security_id = self.repository.ensure_security(str(value("symbol")), str(value("name")))
                sec = next(s for s in self.repository.list_securities() if s["id"] == security_id)
                price, shares, fee = dec(value("buy_price")), int(value("original_shares")), dec(value("buy_fee", 0))
                total = money(price * shares + fee); funding = self.funding.currentData(); loan_amount = total if funding in ("LOAN", "MIXED") else 0
                cash_amount = total - loan_amount
                self.repository.add_buy_lot({"security_id": security_id, "broker_account_id": self.broker.currentData(), "buy_date": buy_date, "buy_price": price,
                    "original_shares": shares, "stock_amount": price * shares, "buy_fee": fee, "funding_type": funding, "loan_id": self.loan.currentData(),
                    "loan_funded": loan_amount, "cash_funded": cash_amount, "target_return_pct": sec["default_target_return_pct"], "recovery_mode": sec["default_recovery_mode"],
                    "recovery_tolerance_amount": sec["recovery_tolerance_amount"], "recovery_tolerance_pct": sec["recovery_tolerance_pct"],
                    "broker_order_id": str(value("broker_order_id", "") or ""), "note": str(value("note", "") or "")})
                successes += 1
            except Exception as exc: errors.append(f"第 {number} 列：{exc}")
        message = f"成功匯入 {successes} 筆。"
        if errors: message += f"\n失敗 {len(errors)} 筆：\n" + "\n".join(errors[:20])
        QMessageBox.information(self, "匯入結果", message)
        if successes: self.accept()


class BackupSettingsDialog(QDialog):
    def __init__(self, service: BackupService, parent=None):
        super().__init__(parent); self.setWindowTitle("備份設定"); self.resize(850, 460); self.service = service
        root = QVBoxLayout(self); self.table = QTableWidget(0, 7); self.table.setHorizontalHeaderLabels(["啟用", "名稱", "類型", "備份位置", "保留天數", "最後成功", "最後錯誤"]); root.addWidget(self.table)
        line = QHBoxLayout(); add = QPushButton("新增位置"); add.clicked.connect(self.add); refresh = QPushButton("重新整理"); refresh.clicked.connect(self.refresh); line.addWidget(add); line.addWidget(refresh); line.addStretch(); close = QPushButton("關閉"); close.clicked.connect(self.accept); line.addWidget(close); root.addLayout(line); self.refresh()
    def refresh(self):
        rows = self.service.targets(); self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            values = ["是" if row["enabled"] else "否", row["name"], "Google Drive 同步資料夾" if row["target_type"] == "GOOGLE_DRIVE_SYNC_FOLDER" else "本機資料夾", row["path"], row["retention_days"], row["last_success_at"] or "—", row["last_error"] or "—"]
            for c, value in enumerate(values): self.table.setItem(r, c, QTableWidgetItem(str(value)))
        self.table.resizeColumnsToContents()
    def add(self):
        path = QFileDialog.getExistingDirectory(self, "選擇備份資料夾")
        if not path: return
        name, ok = QInputDialog.getText(self, "新增備份位置", "顯示名稱", text=Path(path).name)
        if ok and name.strip(): self.service.add_target(name.strip(), path); self.refresh()


class BackupHistoryDialog(QDialog):
    def __init__(self, service: BackupService, parent=None):
        super().__init__(parent); self.setWindowTitle("備份歷史"); self.resize(900, 500); root = QVBoxLayout(self)
        rows = service.history(); table = QTableWidget(len(rows), 6); table.setHorizontalHeaderLabels(["日期時間", "觸發方式", "資料庫", "Excel", "狀態", "錯誤"])
        labels={"STARTUP":"程式啟動","MANUAL":"手動","BEFORE_EXCEL_IMPORT":"Excel 匯入前","SUCCESS":"成功","FAILED":"失敗","PARTIAL":"部分成功","PENDING":"處理中"}
        for r, row in enumerate(rows):
            vals = [row["started_at"], labels.get(row["trigger_type"],row["trigger_type"]), labels.get(row["db_status"],row["db_status"]), labels.get(row["excel_status"],row["excel_status"]), labels.get(row["status"],row["status"]), row["error_message"] or ""]
            for c, value in enumerate(vals):
                item=QTableWidgetItem(str(value))
                if c in (2,3,4):
                    raw=(row["db_status"],row["excel_status"],row["status"])[c-2]
                    if raw=="SUCCESS": background,foreground=COLORS["success_soft"],COLORS["success"]
                    elif raw in ("PARTIAL","PENDING"): background,foreground=COLORS["warning_soft"],COLORS["warning"]
                    elif raw=="FAILED": background,foreground=COLORS["danger_soft"],COLORS["danger"]
                    else: background=foreground=None
                    if background:
                        item.setBackground(QColor(background)); item.setForeground(QColor(foreground))
                table.setItem(r,c,item)
        table.resizeColumnsToContents(); root.addWidget(table); close=QPushButton("關閉"); close.clicked.connect(self.accept); root.addWidget(close)


class AuditDialog(QDialog):
    def __init__(self, repository: PortfolioRepository, parent=None):
        super().__init__(parent); self.setWindowTitle("稽核紀錄"); self.resize(1100, 600); root=QVBoxLayout(self); rows=repository.audit_rows()
        table=QTableWidget(len(rows), 7); table.setHorizontalHeaderLabels(["時間", "動作", "資料類型", "資料編號", "修改前", "修改後", "備註"])
        for r,row in enumerate(rows):
            for c,key in enumerate(("occurred_at","action","entity_type","entity_id","old_value","new_value","note")): table.setItem(r,c,QTableWidgetItem(str(row.get(key) or "")))
        table.resizeColumnsToContents(); root.addWidget(table); close=QPushButton("關閉"); close.clicked.connect(self.accept); root.addWidget(close)
