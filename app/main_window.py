from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor
from PySide6.QtWidgets import (
    QComboBox, QDialog, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMainWindow,
    QInputDialog, QMenu, QMessageBox, QPushButton, QStatusBar, QTableWidget, QTableWidgetItem,
    QToolBar, QToolButton, QVBoxLayout, QWidget,
)

from stock_manager.config import APP_NAME, AppPaths
from stock_manager.database import PortfolioRepository
from stock_manager.dialogs.analysis_dialog import AnalysisDialog
from stock_manager.dialogs.data_dialogs import AuditDialog, BackupHistoryDialog, BackupSettingsDialog, ExcelImportDialog, SettingsDialog
from stock_manager.dialogs.forms import BuyDialog, CorporateActionDialog, DividendDialog, LoanDialog, LoanTransactionDialog, PriceDialog, ReconciliationDialog, SellDialog
from stock_manager.dialogs.recovery_dialog import RecoveryDialog
from stock_manager.dialogs.ocr_dialog import OCRWorkbenchDialog
from stock_manager.domain import FundingType, StrategyStatus, zh
from stock_manager.import_export import BackupService, ExcelService
from stock_manager.services import PortfolioService
from stock_manager.ui import return_foreground, set_widget_property, strategy_colors
from stock_manager.utils.formatting import currency, number, percent


COLUMNS = [
    ("id", "買進批次", "basic"), ("buy_date", "買入日期", "basic"), ("broker_name", "券商", "basic"),
    ("symbol", "股票代號", "basic"), ("security_name", "股票名稱", "basic"), ("funding_type", "資金來源", "basic"),
    ("loan_id", "貸款編號", "loan"), ("buy_price", "買入價格", "basic"), ("original_shares", "原始股數", "basic"),
    ("original_capital", "原始總投入", "basic"), ("current_price", "現價", "market"), ("current_return_pct", "目前報酬率", "market"),
    ("target_return_pct", "目標報酬率", "market"), ("target_price", "目標價格", "market"), ("distance_to_target_pct", "距離目標", "market"),
    ("strategy_status", "策略狀態", "market"), ("net_cash_recovered", "累積淨回收", "recovery"),
    ("capital_recovery_ratio", "本金回收率", "recovery"), ("full_cost_recovery_ratio", "完整成本回收率", "recovery"),
    ("remaining_capital_at_risk", "尚未回收本金", "recovery"), ("recovery_difference", "回本差額", "recovery"),
    ("remaining_shares", "目前股數", "position"), ("free_shares", "已回本持股", "position"),
    ("market_value", "目前市值", "position"), ("free_share_value", "已回本持股市值", "position"),
    ("loan_funded", "貸款投入", "loan"), ("loan_interest", "累積利息", "loan"),
    ("last_sell_date", "最近賣出日期", "history"), ("sold_shares", "累積賣出股數", "history"),
    ("holding_days", "持有天數", "history"), ("updated_at", "最後修改時間", "history"),
]

MONEY_FIELDS = {"buy_price", "original_capital", "current_price", "target_price", "net_cash_recovered", "remaining_capital_at_risk", "recovery_difference", "market_value", "free_share_value", "loan_funded", "loan_interest"}
PERCENT_FIELDS = {"current_return_pct", "target_return_pct", "distance_to_target_pct"}
RATIO_FIELDS = {"capital_recovery_ratio", "full_cost_recovery_ratio"}
NUMBER_FIELDS = {"original_shares", "remaining_shares", "free_shares", "sold_shares", "holding_days"}


class MasterTable(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(0, len(COLUMNS), parent); self.setHorizontalHeaderLabels([c[1] for c in COLUMNS])
        self.setAlternatingRowColors(True); self.setSelectionBehavior(QTableWidget.SelectRows); self.setSelectionMode(QTableWidget.SingleSelection)
        self.setEditTriggers(QTableWidget.NoEditTriggers); self.setSortingEnabled(True); self.verticalHeader().setVisible(False)

    def load(self, rows: list[dict]):
        self.setSortingEnabled(False); self.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, (key, _, _) in enumerate(COLUMNS):
                value = row.get(key)
                if key in MONEY_FIELDS: text = currency(value)
                elif key in PERCENT_FIELDS: text = percent(value)
                elif key in RATIO_FIELDS: text = percent(value, ratio=True)
                elif key in NUMBER_FIELDS: text = f"{int(value or 0):,}"
                elif hasattr(value, "value"): text = zh(value)
                else: text = str(value or "")
                item = QTableWidgetItem(text); item.setData(Qt.UserRole, row["id"])
                if key == "strategy_status":
                    colors = strategy_colors(value)
                    if colors:
                        background, foreground = colors
                        item.setBackground(QColor(background)); item.setForeground(QColor(foreground))
                if key == "current_return_pct": item.setForeground(QColor(return_foreground(value)))
                self.setItem(r, c, item)
        self.setSortingEnabled(True); self.resizeColumnsToContents()
        for c in range(self.columnCount()): self.setColumnWidth(c, min(190, max(90, self.columnWidth(c))))

    def selected_lot_id(self) -> str | None:
        row = self.currentRow()
        return self.item(row, 0).data(Qt.UserRole) if row >= 0 and self.item(row, 0) else None

    def apply_view(self, mode: str):
        groups = {"basic": {"basic", "market"}, "market": {"basic", "market"}, "recovery": {"basic", "recovery"}, "position": {"basic", "position"}, "loan": {"basic", "loan"}, "all": {"basic", "market", "recovery", "position", "loan", "history"}}
        visible = groups.get(mode, groups["all"])
        for index, (_, _, group) in enumerate(COLUMNS): self.setColumnHidden(index, group not in visible)


class LotDetailDialog(QDialog):
    def __init__(self, row: dict, repository: PortfolioRepository, parent=None):
        super().__init__(parent); self.setWindowTitle(f"買進批次明細｜{row['id']}"); self.resize(800, 560); root=QVBoxLayout(self)
        summary = QLabel(
            f"<h2>{row['id']}｜{row['symbol']} {row['security_name']}</h2>"
            f"<b>買入</b>　{row['buy_date']}　{row['original_shares']:,} 股 @ {currency(row['buy_price'])}　原始投入 {currency(row['original_capital'])}<br><br>"
            f"<b>策略</b>　目前報酬 {percent(row['current_return_pct'])}　目標 {percent(row['target_return_pct'])}　目標價 {currency(row['target_price'])}　{zh(row['strategy_status'])}<br><br>"
            f"<b>回收</b>　淨回收 {currency(row['net_cash_recovered'])}　本金回收率 {percent(row['capital_recovery_ratio'], True)}　完整成本回收率 {percent(row['full_cost_recovery_ratio'], True)}<br>"
            f"尚未回收本金 {currency(row['remaining_capital_at_risk'])}　超額回收現金 {currency(row['cash_surplus'])}<br><br>"
            f"<b>持股</b>　剩餘 {row['remaining_shares']:,} 股　市值 {currency(row['market_value'])}　已回本持股 {row['free_shares']:,} 股 / {currency(row['free_share_value'])}"
        ); summary.setWordWrap(True); root.addWidget(summary)
        sells = repository.list_sells(row["id"]); table=QTableWidget(len(sells),7); table.setHorizontalHeaderLabels(["賣出編號","日期","股數","價格","成交總額","交易成本","實際淨回收"])
        for r,s in enumerate(sells):
            vals=[s["id"],s["sell_date"],f"{s['shares']:,}",currency(s["sell_price"]),currency(s["gross_amount"]),currency(s["commission"]+s["tax"]+s["other_fee"]),currency(s["net_cash"])]
            for c,v in enumerate(vals): table.setItem(r,c,QTableWidgetItem(str(v)))
        table.resizeColumnsToContents(); root.addWidget(table); close=QPushButton("關閉"); close.clicked.connect(self.accept); root.addWidget(close)


class MainWindow(QMainWindow):
    def __init__(self, repository: PortfolioRepository, paths: AppPaths, backup: BackupService, startup_backup: dict | None = None):
        super().__init__(); self.repository=repository; self.paths=paths; self.backup=backup; self.portfolio=PortfolioService(repository); self.excel=ExcelService(repository); self._rows=[]
        self.setWindowTitle(APP_NAME); self.resize(1500, 850); self._build_toolbar(); self._build_central(); self._build_status(); self.refresh()
        if startup_backup: self.show_backup_result(startup_backup, startup=True)

    def _build_toolbar(self):
        toolbar=QToolBar("主要工具列"); toolbar.setMovable(False); toolbar.setToolButtonStyle(Qt.ToolButtonTextOnly); self.addToolBar(toolbar)
        self._button(toolbar,"新增買入",lambda:self.open_dialog(BuyDialog(self.repository,self)),role="primary")
        self._button(toolbar,"新增賣出",self.add_sell); self._button(toolbar,"新增股利",lambda:self.open_dialog(DividendDialog(self.repository,self)))
        self._button(toolbar,"公司行動",lambda:self.open_dialog(CorporateActionDialog(self.repository,self)))
        self._button(toolbar,"截圖匯入",lambda:OCRWorkbenchDialog(self.repository,self).exec())
        loan_menu=QMenu(self); loan_menu.addAction("新增貸款帳戶",lambda:self.open_dialog(LoanDialog(self.repository,self))); loan_menu.addAction("新增還款／利息",lambda:self.open_dialog(LoanTransactionDialog(self.repository,self)))
        self._menu_button(toolbar,"貸款與資金",loan_menu); toolbar.addSeparator()
        self._button(toolbar,"回本模擬",self.simulate); self._button(toolbar,"更新股價",lambda:self.open_dialog(PriceDialog(self.repository,self)))
        self._button(toolbar,"修改批次策略",self.edit_lot_strategy)
        self._button(toolbar,"對帳",lambda:self.open_dialog(ReconciliationDialog(self.repository,self))); self._button(toolbar,"分析",lambda:AnalysisDialog(self.repository,self).exec()); toolbar.addSeparator()
        data=QMenu(self); data.addAction("從 Excel 匯入",self.import_excel); data.addAction("匯出完整 Excel",self.export_excel); data.addAction("匯出目前表格 CSV",self.export_csv); data.addSeparator()
        data.addAction("立即完整備份",self.run_backup); data.addAction("備份歷史",lambda:BackupHistoryDialog(self.backup,self).exec()); data.addAction("備份設定",lambda:BackupSettingsDialog(self.backup,self).exec()); data.addSeparator(); data.addAction("稽核紀錄",lambda:AuditDialog(self.repository,self).exec())
        self._menu_button(toolbar,"資料",data); self._button(toolbar,"設定",lambda:self.open_dialog(SettingsDialog(self.repository,self)))

    @staticmethod
    def _button(toolbar, text, callback, role=None):
        action=QAction(text,toolbar); action.triggered.connect(callback); toolbar.addAction(action)
        if role:
            widget=toolbar.widgetForAction(action)
            if widget: widget.setProperty("role",role)
        return action
    @staticmethod
    def _menu_button(toolbar, text, menu):
        button=QToolButton(); button.setText(text+" ▼"); button.setMenu(menu); button.setPopupMode(QToolButton.InstantPopup); toolbar.addWidget(button)

    def _build_central(self):
        central=QWidget(); root=QVBoxLayout(central); self.setCentralWidget(central)
        filters=QHBoxLayout(); self.search=QLineEdit(); self.search.setPlaceholderText("搜尋股票、名稱、批次或券商…"); self.search.textChanged.connect(self.refresh)
        self.security_filter=QComboBox(); self.security_filter.addItem("全部股票",None); self.broker_filter=QComboBox(); self.broker_filter.addItem("全部券商",None)
        self.funding_filter=QComboBox(); self.funding_filter.addItem("全部資金來源",None)
        for item in FundingType: self.funding_filter.addItem(zh(item),item.value)
        self.status_filter=QComboBox(); self.status_filter.addItem("全部狀態",None)
        for item in StrategyStatus: self.status_filter.addItem(zh(item),item.value)
        for row in self.repository.list_securities(): self.security_filter.addItem(f"{row['symbol']} {row['name']}",row["id"])
        for row in self.repository.list_brokers(): self.broker_filter.addItem(row["name"],row["id"])
        for w in (self.security_filter,self.broker_filter,self.funding_filter,self.status_filter): w.currentIndexChanged.connect(self.refresh)
        self.view=QComboBox()
        for text,value in (("基本＋市場","basic"),("市場","market"),("回收","recovery"),("持股","position"),("貸款","loan"),("全部欄位","all")): self.view.addItem(text,value)
        self.view.currentIndexChanged.connect(lambda:self.table.apply_view(self.view.currentData()))
        for label,w in (("",self.search),("股票",self.security_filter),("券商",self.broker_filter),("資金",self.funding_filter),("狀態",self.status_filter),("欄位檢視",self.view)): 
            if label: filters.addWidget(QLabel(label))
            filters.addWidget(w)
        root.addLayout(filters); self.kpi=QLabel(); self.kpi.setObjectName("kpiBar"); root.addWidget(self.kpi)
        self.table=MasterTable(); self.table.doubleClicked.connect(self.show_detail); root.addWidget(self.table)

    def _build_status(self):
        status=QStatusBar(); self.setStatusBar(status); self.status_text=QLabel(); status.addWidget(self.status_text,1); self.backup_text=QLabel("備份：尚未執行"); set_widget_property(self.backup_text,"role","info"); status.addPermanentWidget(self.backup_text)

    def refresh(self):
        self._sync_filters()
        filters={"query":self.search.text(),"security_id":self.security_filter.currentData(),"broker_account_id":self.broker_filter.currentData(),"funding_type":self.funding_filter.currentData(),"strategy_status":self.status_filter.currentData()}
        self._rows=self.portfolio.master_rows(filters); self.table.load(self._rows); self.table.apply_view(self.view.currentData() or "basic")
        d=self.repository.dashboard(); ratio=(d["recovered_lots"]/d["total_lots"]*100) if d["total_lots"] else 0
        self.kpi.setText(f"已回本持股市值　<b>{currency(d['free_share_value'])}</b>　　尚未回收本金　<b>{currency(d['capital_at_risk'])}</b>　　目前貸款餘額　<b>{currency(d['loan_balance'])}</b>　　已回本批次　<b>{d['recovered_lots']} / {d['total_lots']}（{ratio:.1f}%）</b>")
        self.status_text.setText(f"顯示 {len(self._rows):,} 筆買進批次｜資料庫：{self.paths.database}")

    def _sync_filters(self):
        current_security=self.security_filter.currentData(); current_broker=self.broker_filter.currentData()
        securities={self.security_filter.itemData(i) for i in range(self.security_filter.count())}
        brokers={self.broker_filter.itemData(i) for i in range(self.broker_filter.count())}
        self.security_filter.blockSignals(True); self.broker_filter.blockSignals(True)
        for row in self.repository.list_securities():
            if row["id"] not in securities: self.security_filter.addItem(f"{row['symbol']} {row['name']}",row["id"])
        for row in self.repository.list_brokers():
            if row["id"] not in brokers: self.broker_filter.addItem(row["name"],row["id"])
        index=self.security_filter.findData(current_security); self.security_filter.setCurrentIndex(max(0,index))
        index=self.broker_filter.findData(current_broker); self.broker_filter.setCurrentIndex(max(0,index))
        self.security_filter.blockSignals(False); self.broker_filter.blockSignals(False)

    def open_dialog(self, dialog):
        if dialog.exec(): self.refresh()
    def selected_id(self): return self.table.selected_lot_id()
    def add_sell(self): self.open_dialog(SellDialog(self.repository,self.selected_id(),self))
    def simulate(self): RecoveryDialog(self.repository,self.selected_id(),self).exec()
    def edit_lot_strategy(self):
        lot_id=self.selected_id()
        if not lot_id: QMessageBox.information(self,"請選擇批次","請先在主表選取一筆買進批次"); return
        lot=self.repository.get_lot(lot_id); value,ok=QInputDialog.getDouble(self,"修改批次策略",f"{lot_id} 的目標報酬率（修改不影響股票預設值）",float(lot["target_return_pct"]),-99,1000,2)
        if ok: self.repository.update_lot_strategy(lot_id,value); self.refresh()
    def show_detail(self):
        lot_id=self.selected_id(); row=next((r for r in self._rows if r["id"]==lot_id),None)
        if row: LotDetailDialog(row,self.repository,self).exec()

    def import_excel(self):
        result=self.backup.run("BEFORE_EXCEL_IMPORT"); self.show_backup_result(result)
        if result["successes"] == 0 and result["total"] > 0:
            if QMessageBox.question(self,"備份失敗","匯入前備份未成功。仍要繼續進入匯入預覽嗎？") != QMessageBox.Yes: return
        self.open_dialog(ExcelImportDialog(self.repository,self))
    def export_excel(self):
        default=self.paths.exports/f"股票策略完整備份_{datetime.now():%Y%m%d_%H%M%S}.xlsx"; path,_=QFileDialog.getSaveFileName(self,"匯出完整 Excel",str(default),"Excel (*.xlsx)")
        if path:
            try: self.excel.export_complete(path); QMessageBox.information(self,"匯出完成",f"完整 Excel 已匯出：\n{path}")
            except Exception as exc: QMessageBox.warning(self,"匯出失敗",str(exc))
    def export_csv(self):
        default=self.paths.exports/f"目前買進批次_{datetime.now():%Y%m%d_%H%M%S}.csv"; path,_=QFileDialog.getSaveFileName(self,"匯出目前表格",str(default),"CSV (*.csv)")
        if path:
            try: self.excel.export_master_csv(path,self._rows); QMessageBox.information(self,"匯出完成",f"CSV 已匯出：\n{path}")
            except Exception as exc: QMessageBox.warning(self,"匯出失敗",str(exc))
    def run_backup(self): self.show_backup_result(self.backup.run("MANUAL"),notify=True)
    def show_backup_result(self,result,startup=False,notify=False):
        self.backup_text.setText(f"備份：{result.get('successes',0)} / {result.get('total',0)} 成功")
        status=result.get("status")
        role="success" if status in ("SUCCESS","SKIPPED") else "warning" if status=="PARTIAL" else "danger"
        set_widget_property(self.backup_text,"role",role)
        if notify or (startup and result.get("status") not in ("SUCCESS","SKIPPED")):
            labels={"SUCCESS":"成功","FAILED":"失敗","PARTIAL":"部分成功","SKIPPED":"今日已完成，略過"}
            text=f"備份狀態：{labels.get(result.get('status'),result.get('status'))}\n成功位置：{result.get('successes',0)} / {result.get('total',0)}"
            if result.get("error"): text+=f"\n{result['error']}"
            QMessageBox.information(self,"備份結果",text)
