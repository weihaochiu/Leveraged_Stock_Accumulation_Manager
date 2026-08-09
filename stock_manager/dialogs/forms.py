from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDateEdit, QDialog, QDialogButtonBox, QDoubleSpinBox,
    QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPlainTextEdit, QSpinBox, QVBoxLayout,
)

from stock_manager.database import PortfolioRepository
from stock_manager.domain import FeePolicy, FundingType, RecoveryMode, dec, suggest_budget_shares, zh
from stock_manager.services import RecoveryService
from stock_manager.utils.formatting import currency, percent


def _money_spin(maximum: float = 1_000_000_000) -> QDoubleSpinBox:
    widget = QDoubleSpinBox(); widget.setRange(0, maximum); widget.setDecimals(2); widget.setGroupSeparatorShown(True)
    return widget


def _pct_spin() -> QDoubleSpinBox:
    widget = QDoubleSpinBox(); widget.setRange(-99.99, 1000); widget.setDecimals(2); widget.setSuffix(" %")
    return widget


def _date_edit() -> QDateEdit:
    widget = QDateEdit(QDate.currentDate()); widget.setCalendarPopup(True); widget.setDisplayFormat("yyyy/MM/dd")
    return widget


class BaseDialog(QDialog):
    def __init__(self, title: str, parent=None):
        super().__init__(parent); self.setWindowTitle(title); self.setMinimumWidth(560)
        self.root = QVBoxLayout(self)
        self.form = QFormLayout(); self.root.addLayout(self.form)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.buttons.button(QDialogButtonBox.Save).setText("儲存")
        self.buttons.button(QDialogButtonBox.Cancel).setText("取消")
        self.buttons.accepted.connect(self.submit); self.buttons.rejected.connect(self.reject)

    def finish(self):
        self.root.addWidget(self.buttons)

    def fail(self, exc: Exception):
        QMessageBox.warning(self, "資料驗證失敗", str(exc))

    def submit(self):
        raise NotImplementedError


class BuyDialog(BaseDialog):
    def __init__(self, repository: PortfolioRepository, parent=None, prefill: dict | None = None):
        super().__init__("新增買入批次", parent); self.repository = repository
        self.security = QComboBox(); self._load_securities(); self.security.currentIndexChanged.connect(self._security_changed)
        self.symbol = QLineEdit(); self.symbol.setPlaceholderText("例如：006208")
        self.name = QLineEdit(); self.name.setPlaceholderText("例如：富邦台50")
        sec_line = QHBoxLayout(); sec_line.addWidget(self.security, 2); sec_line.addWidget(QLabel("或新增：")); sec_line.addWidget(self.symbol); sec_line.addWidget(self.name)
        self.form.addRow("股票", sec_line)
        self.broker = QComboBox(); self.broker.addItem("未指定", None)
        for row in repository.list_brokers(): self.broker.addItem(f"{row['name']} {row['account_label']}", row["id"])
        self.buy_date = _date_edit(); self.price = _money_spin(); self.shares = QSpinBox(); self.shares.setRange(1, 100_000_000)
        self.stock_amount = _money_spin(); self.fee = _money_spin(); self.other_cost = _money_spin()
        self.budget = _money_spin(); self.budget.setValue(10000); self.suggested = QLabel("—")
        self.funding = QComboBox()
        for item in FundingType: self.funding.addItem(zh(item), item.value)
        self.loan = QComboBox(); self.loan.addItem("不使用貸款", None)
        for row in repository.list_loans(): self.loan.addItem(f"{row['id']}｜{row['name']}｜餘額 {currency(row['current_balance'])}", row["id"])
        self.loan_funded = _money_spin(); self.cash_funded = _money_spin()
        self.target = _pct_spin(); self.tolerance = _money_spin(); self.tolerance_pct = _pct_spin()
        self.recovery_mode = QComboBox()
        for item in RecoveryMode: self.recovery_mode.addItem(zh(item), item.value)
        self.order_id = QLineEdit(); self.execution_id = QLineEdit(); self.note = QPlainTextEdit(); self.note.setMaximumHeight(70)
        for label, widget in (
            ("券商帳戶", self.broker), ("買入日期", self.buy_date), ("買入價格", self.price), ("原始股數", self.shares),
            ("策略單位預算", self.budget), ("建議股數", self.suggested), ("股票成交金額", self.stock_amount),
            ("買入手續費", self.fee), ("其他買入成本", self.other_cost), ("資金來源", self.funding),
            ("貸款帳戶", self.loan), ("貸款投入", self.loan_funded), ("自有資金投入", self.cash_funded),
            ("此批次目標報酬", self.target), ("回本容許差額", self.tolerance), ("回本容許比例", self.tolerance_pct),
            ("預設回收模式", self.recovery_mode), ("券商下單編號", self.order_id), ("券商成交編號", self.execution_id), ("備註", self.note),
        ): self.form.addRow(label, widget)
        self.price.valueChanged.connect(self._recalculate); self.shares.valueChanged.connect(self._recalculate)
        self.fee.valueChanged.connect(self._balance_cash); self.other_cost.valueChanged.connect(self._balance_cash)
        self.budget.valueChanged.connect(self._recalculate); self.loan_funded.valueChanged.connect(self._balance_cash)
        self.finish(); self._security_changed()
        if prefill: self._apply_prefill(prefill)

    def _load_securities(self):
        self.security.clear(); self.security.addItem("請選擇；或在右側新增股票", None)
        for row in self.repository.list_securities(): self.security.addItem(f"{row['symbol']} {row['name']}", row)

    def _security_changed(self):
        row = self.security.currentData()
        if row:
            self.target.setValue(row["default_target_return_pct"]); self.budget.setValue(row["default_buy_budget"])
            self.tolerance.setValue(row["recovery_tolerance_amount"]); self.tolerance_pct.setValue(row["recovery_tolerance_pct"])
            idx = self.funding.findData(row["default_funding_preference"])
            if idx >= 0: self.funding.setCurrentIndex(idx)
            idx = self.recovery_mode.findData(row["default_recovery_mode"])
            if idx >= 0: self.recovery_mode.setCurrentIndex(idx)

    def _recalculate(self):
        suggested = suggest_budget_shares(self.budget.value(), self.price.value())
        self.suggested.setText(f"{suggested:,} 股（不超過預算）")
        self.stock_amount.setValue(self.price.value() * self.shares.value())
        self._balance_cash()

    def _balance_cash(self):
        total = self.stock_amount.value() + self.fee.value() + self.other_cost.value()
        self.cash_funded.setValue(max(0, total - self.loan_funded.value()))

    def _apply_prefill(self, data: dict):
        symbol = str(data.get("symbol") or "")
        for i in range(self.security.count()):
            row = self.security.itemData(i)
            if row and row["symbol"] == symbol: self.security.setCurrentIndex(i); break
        else: self.symbol.setText(symbol)
        if data.get("trade_date"): self.buy_date.setDate(QDate.fromString(str(data["trade_date"]), "yyyy-MM-dd"))
        if data.get("price"): self.price.setValue(float(data["price"]))
        if data.get("shares"): self.shares.setValue(int(data["shares"]))
        self.order_id.setText(str(data.get("broker_order_id") or ""))

    def submit(self):
        try:
            sec = self.security.currentData()
            security_id = sec["id"] if sec else self.repository.ensure_security(self.symbol.text(), self.name.text())
            total = self.stock_amount.value() + self.fee.value() + self.other_cost.value()
            self.repository.add_buy_lot({
                "security_id": security_id, "broker_account_id": self.broker.currentData(),
                "buy_date": self.buy_date.date().toString("yyyy-MM-dd"), "buy_price": self.price.value(),
                "original_shares": self.shares.value(), "stock_amount": self.stock_amount.value(), "buy_fee": self.fee.value(),
                "other_cost": self.other_cost.value(), "funding_type": self.funding.currentData(), "loan_id": self.loan.currentData(),
                "loan_funded": self.loan_funded.value(), "cash_funded": self.cash_funded.value(), "target_return_pct": self.target.value(),
                "recovery_mode": self.recovery_mode.currentData(), "recovery_tolerance_amount": self.tolerance.value(),
                "recovery_tolerance_pct": self.tolerance_pct.value(), "broker_order_id": self.order_id.text().strip(),
                "broker_execution_id": self.execution_id.text().strip(), "note": self.note.toPlainText(),
            })
            self.accept()
        except Exception as exc: self.fail(exc)


class SellDialog(BaseDialog):
    def __init__(self, repository: PortfolioRepository, initial_lot_id: str | None = None, parent=None, prefill: dict | None = None):
        super().__init__("新增賣出交易", parent); self.repository = repository; self.recovery = RecoveryService(repository)
        self.lot = QComboBox()
        for row in repository.master_rows():
            if row["remaining_shares"] > 0:
                self.lot.addItem(f"{row['id']}｜{row['symbol']} {row['security_name']}｜剩 {row['remaining_shares']:,} 股｜報酬 {percent(row['current_return_pct'])}", row)
        if initial_lot_id:
            for i in range(self.lot.count()):
                if self.lot.itemData(i)["id"] == initial_lot_id: self.lot.setCurrentIndex(i); break
        self.sell_date = _date_edit(); self.price = _money_spin(); self.shares = QSpinBox(); self.shares.setRange(1, 100_000_000)
        self.gross = _money_spin(); self.commission = _money_spin(); self.tax = _money_spin(); self.other_fee = _money_spin(); self.net = _money_spin()
        self.repay = QCheckBox("本次賣出現金有用於償還貸款"); self.repay_amount = _money_spin()
        self.order_id = QLineEdit(); self.execution_id = QLineEdit(); self.preview = QLabel(); self.preview.setWordWrap(True)
        self.note = QPlainTextEdit(); self.note.setMaximumHeight(60)
        for label, widget in (("指定買進批次", self.lot), ("賣出日期", self.sell_date), ("實際成交價格", self.price), ("賣出股數", self.shares),
            ("成交總額", self.gross), ("賣出手續費", self.commission), ("交易稅", self.tax), ("其他費用", self.other_fee),
            ("實際淨回收", self.net), ("貸款還款", self.repay), ("實際償還貸款", self.repay_amount),
            ("券商下單編號", self.order_id), ("券商成交編號", self.execution_id), ("交易後預覽", self.preview), ("備註", self.note)):
            self.form.addRow(label, widget)
        self.lot.currentIndexChanged.connect(self._lot_changed); self.price.valueChanged.connect(self._calculate); self.shares.valueChanged.connect(self._calculate)
        self.other_fee.valueChanged.connect(self._calculate); self.finish(); self._lot_changed()
        if prefill: self._apply_prefill(prefill)

    def _apply_prefill(self, data: dict):
        symbol = str(data.get("symbol") or "")
        candidates = []
        for i in range(self.lot.count()):
            row = self.lot.itemData(i)
            if row["symbol"] == symbol and row["remaining_shares"] >= int(data.get("shares") or 0): candidates.append((float(row["current_return_pct"]), i))
        if candidates: self.lot.setCurrentIndex(max(candidates)[1])
        if data.get("trade_date"): self.sell_date.setDate(QDate.fromString(str(data["trade_date"]), "yyyy-MM-dd"))
        if data.get("price"): self.price.setValue(float(data["price"]))
        if data.get("shares"): self.shares.setValue(int(data["shares"]))
        self.order_id.setText(str(data.get("broker_order_id") or ""))

    def _lot_changed(self):
        row = self.lot.currentData()
        if row:
            self.shares.setMaximum(row["remaining_shares"]); self.price.setValue(float(row["current_price"] or row["buy_price"]))
        self._calculate()

    def _calculate(self):
        row = self.lot.currentData()
        if not row: return
        gross, fee, tax, net = self.recovery.fee_policy().sell_net(self.shares.value(), dec(self.price.value()))
        net -= dec(self.other_fee.value())
        self.gross.setValue(float(gross)); self.commission.setValue(float(fee)); self.tax.setValue(float(tax)); self.net.setValue(float(net))
        remaining = row["remaining_shares"] - self.shares.value()
        ratio = (row["net_cash_recovered"] + net) / row["original_capital"] if row["original_capital"] else 0
        self.preview.setText(f"賣出後剩餘 {remaining:,} 股；預計本金回收率 {float(ratio)*100:.2f}%（可高於 100%）")

    def submit(self):
        try:
            row = self.lot.currentData()
            if not row: raise ValueError("目前沒有可賣出的買進批次")
            self.repository.add_sell({
                "lot_id": row["id"], "security_id": row["security_id"], "broker_account_id": row["broker_account_id"],
                "sell_date": self.sell_date.date().toString("yyyy-MM-dd"), "sell_price": self.price.value(), "shares": self.shares.value(),
                "gross_amount": self.gross.value(), "commission": self.commission.value(), "tax": self.tax.value(), "other_fee": self.other_fee.value(),
                "net_cash": self.net.value(), "repay_loan": self.repay.isChecked(), "loan_repayment_amount": self.repay_amount.value(),
                "broker_order_id": self.order_id.text().strip(), "broker_execution_id": self.execution_id.text().strip(), "note": self.note.toPlainText(),
            })
            self.accept()
        except Exception as exc: self.fail(exc)


class DividendDialog(BaseDialog):
    def __init__(self, repository: PortfolioRepository, parent=None):
        super().__init__("新增股利", parent); self.repository = repository
        self.security = QComboBox()
        for row in repository.list_securities(): self.security.addItem(f"{row['symbol']} {row['name']}", row["id"])
        self.lot = QComboBox(); self.lot.addItem("不指定批次", None)
        for row in repository.master_rows(): self.lot.addItem(f"{row['id']}｜{row['symbol']} {row['security_name']}", row["id"])
        self.payment_date = _date_edit(); self.ex_date = _date_edit(); self.base_shares = _money_spin(); self.per_share = _money_spin()
        self.gross = _money_spin(); self.tax = _money_spin(); self.insurance = _money_spin(); self.other = _money_spin(); self.net = _money_spin()
        self.include = QCheckBox("將本筆股利納入該批次回本現金流"); self.note = QPlainTextEdit(); self.note.setMaximumHeight(60)
        for label, widget in (("股票", self.security), ("對應買進批次", self.lot), ("除息／除權日", self.ex_date), ("入帳日", self.payment_date),
            ("基準股數", self.base_shares), ("每股股利", self.per_share), ("稅前股利", self.gross), ("稅額", self.tax),
            ("補充保費", self.insurance), ("其他費用", self.other), ("實收股利", self.net), ("回本設定", self.include), ("備註", self.note)):
            self.form.addRow(label, widget)
        for w in (self.base_shares, self.per_share, self.tax, self.insurance, self.other): w.valueChanged.connect(self._calculate)
        self.finish()

    def _calculate(self):
        gross = self.base_shares.value() * self.per_share.value(); self.gross.setValue(gross)
        self.net.setValue(max(0, gross - self.tax.value() - self.insurance.value() - self.other.value()))

    def submit(self):
        try:
            if self.security.currentData() is None: raise ValueError("請先建立股票資料")
            self.repository.add_dividend({"security_id": self.security.currentData(), "lot_id": self.lot.currentData(), "payment_date": self.payment_date.date().toString("yyyy-MM-dd"),
                "ex_date": self.ex_date.date().toString("yyyy-MM-dd"), "base_shares": self.base_shares.value(), "dividend_per_share": self.per_share.value(),
                "gross_amount": self.gross.value(), "tax": self.tax.value(), "insurance_fee": self.insurance.value(), "other_fee": self.other.value(),
                "net_amount": self.net.value(), "include_in_recovery": self.include.isChecked(), "note": self.note.toPlainText()})
            self.accept()
        except Exception as exc: self.fail(exc)


class LoanDialog(BaseDialog):
    def __init__(self, repository: PortfolioRepository, parent=None):
        super().__init__("新增貸款帳戶", parent); self.repository = repository
        self.name = QLineEdit(); self.institution = QLineEdit(); self.borrow_date = _date_edit(); self.principal = _money_spin(); self.rate = _pct_spin()
        self.maturity = _date_edit(); self.note = QPlainTextEdit(); self.note.setMaximumHeight(70)
        for label, widget in (("貸款名稱", self.name), ("金融機構", self.institution), ("借款日期", self.borrow_date), ("原始本金", self.principal),
            ("年利率", self.rate), ("到期日", self.maturity), ("備註", self.note)): self.form.addRow(label, widget)
        self.finish()
    def submit(self):
        try:
            self.repository.add_loan({"name": self.name.text().strip(), "institution": self.institution.text().strip(), "borrow_date": self.borrow_date.date().toString("yyyy-MM-dd"),
                "original_principal": self.principal.value(), "annual_interest_rate": self.rate.value(), "maturity_date": self.maturity.date().toString("yyyy-MM-dd"), "note": self.note.toPlainText()})
            self.accept()
        except Exception as exc: self.fail(exc)


class LoanTransactionDialog(BaseDialog):
    def __init__(self, repository: PortfolioRepository, parent=None):
        super().__init__("新增貸款交易", parent); self.repository = repository
        self.loan = QComboBox()
        for row in repository.list_loans(): self.loan.addItem(f"{row['id']}｜{row['name']}｜餘額 {currency(row['current_balance'])}", row["id"])
        self.date = _date_edit(); self.kind = QComboBox()
        for text, value in (("償還本金", "REPAYMENT"), ("支付利息", "INTEREST"), ("額外費用", "FEE"), ("新增借款", "BORROW")): self.kind.addItem(text, value)
        self.amount = _money_spin(); self.note = QLineEdit()
        for label, widget in (("貸款帳戶", self.loan), ("日期", self.date), ("類型", self.kind), ("金額", self.amount), ("備註", self.note)): self.form.addRow(label, widget)
        self.finish()
    def submit(self):
        try:
            if not self.loan.currentData(): raise ValueError("請先建立貸款帳戶")
            self.repository.add_loan_transaction({"loan_id": self.loan.currentData(), "transaction_date": self.date.date().toString("yyyy-MM-dd"), "transaction_type": self.kind.currentData(), "amount": self.amount.value(), "note": self.note.text()})
            self.accept()
        except Exception as exc: self.fail(exc)


class PriceDialog(BaseDialog):
    def __init__(self, repository: PortfolioRepository, parent=None):
        super().__init__("手動更新股票價格", parent); self.repository = repository
        self.security = QComboBox()
        for row in repository.list_securities(): self.security.addItem(f"{row['symbol']} {row['name']}", row["id"])
        self.price = _money_spin(); self.date = _date_edit()
        self.form.addRow("股票", self.security); self.form.addRow("收盤／目前價格", self.price); self.form.addRow("價格日期", self.date); self.finish()
    def submit(self):
        try:
            if self.security.currentData() is None: raise ValueError("尚無股票資料")
            self.repository.add_price(self.security.currentData(), self.price.value(), self.date.date().toString("yyyy-MM-dd"), "手動輸入")
            self.accept()
        except Exception as exc: self.fail(exc)


class CorporateActionDialog(BaseDialog):
    def __init__(self, repository: PortfolioRepository, parent=None):
        super().__init__("新增公司行動", parent); self.repository = repository
        self.lot = QComboBox(); self.lot.addItem("請選擇受影響的買進批次", None)
        for row in repository.master_rows(): self.lot.addItem(f"{row['id']}｜{row['symbol']} {row['security_name']}", row)
        self.kind = QComboBox()
        for text, value in (("股票股利／無償配股", "STOCK_DIVIDEND"), ("股票分割", "SPLIT"), ("反向分割", "REVERSE_SPLIT"), ("現金減資", "CAPITAL_REDUCTION"), ("現金增資認購", "PAID_ALLOCATION")): self.kind.addItem(text, value)
        self.date = _date_edit(); self.share_change = QDoubleSpinBox(); self.share_change.setRange(-1_000_000_000, 1_000_000_000); self.share_change.setDecimals(4)
        self.cash = _money_spin(); self.ratio = _pct_spin(); self.note = QPlainTextEdit(); self.note.setMaximumHeight(70)
        for label, widget in (("買進批次", self.lot), ("事件類型", self.kind), ("生效日期", self.date), ("股數增減", self.share_change), ("現金金額", self.cash), ("比例 %", self.ratio), ("備註", self.note)): self.form.addRow(label, widget)
        self.finish()
    def submit(self):
        try:
            lot = self.lot.currentData()
            if not lot: raise ValueError("請指定受影響的買進批次")
            self.repository.add_corporate_action({"security_id": lot["security_id"], "lot_id": lot["id"], "action_type": self.kind.currentData(), "effective_date": self.date.date().toString("yyyy-MM-dd"),
                "share_change": self.share_change.value(), "cash_amount": self.cash.value(), "ratio": self.ratio.value(), "note": self.note.toPlainText()})
            self.accept()
        except Exception as exc: self.fail(exc)


class ReconciliationDialog(BaseDialog):
    def __init__(self, repository: PortfolioRepository, parent=None):
        super().__init__("完成持股對帳", parent); self.repository = repository; self.rows = repository.master_rows()
        self.security = QComboBox()
        for row in repository.list_securities(): self.security.addItem(f"{row['symbol']} {row['name']}", row["id"])
        self.broker = QComboBox(); self.broker.addItem("全部券商", None)
        for row in repository.list_brokers(): self.broker.addItem(row["name"], row["id"])
        self.system = QLabel("0 股"); self.actual = _money_spin(1_000_000_000); self.status = QLabel("—"); self.note = QLineEdit()
        for label, widget in (("股票", self.security), ("券商帳戶", self.broker), ("系統計算持股", self.system), ("券商實際持股", self.actual), ("預計對帳結果", self.status), ("備註", self.note)): self.form.addRow(label, widget)
        self.security.currentIndexChanged.connect(self._calculate); self.broker.currentIndexChanged.connect(self._calculate); self.actual.valueChanged.connect(self._calculate); self.finish(); self._calculate()
    def _calculate(self):
        security_id, broker_id = self.security.currentData(), self.broker.currentData()
        shares = sum(r["remaining_shares"] for r in self.rows if r["security_id"] == security_id and (not broker_id or r["broker_account_id"] == broker_id))
        self.system.setText(f"{shares:,.0f} 股"); difference = self.actual.value() - shares
        self.status.setText("對帳一致" if difference == 0 else f"對帳不一致（差異 {difference:+,.0f} 股）")
        self._system_shares = shares
    def submit(self):
        try:
            if self.security.currentData() is None: raise ValueError("尚無股票資料")
            self.repository.add_reconciliation({"session_date": date.today().isoformat(), "security_id": self.security.currentData(), "broker_account_id": self.broker.currentData(),
                "system_shares": self._system_shares, "broker_shares": self.actual.value(), "note": self.note.text()})
            self.accept()
        except Exception as exc: self.fail(exc)
