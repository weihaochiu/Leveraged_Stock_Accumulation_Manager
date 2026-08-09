from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtWidgets import QDialog, QFileDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout

from stock_manager.database import PortfolioRepository
from stock_manager.dialogs.forms import BuyDialog, SellDialog
from stock_manager.ocr import OCRService


class OCRWorkbenchDialog(QDialog):
    def __init__(self, repository: PortfolioRepository, parent=None):
        super().__init__(parent); self.setWindowTitle("交易截圖 OCR 匯入工作台"); self.resize(1100, 650); self.repository=repository; self.ocr=OCRService(); self.drafts=[]
        root=QVBoxLayout(self); top=QHBoxLayout(); choose=QPushButton("選擇多張交易截圖"); choose.clicked.connect(self.choose); self.summary=QLabel("尚未選取圖片")
        top.addWidget(choose); top.addWidget(self.summary); top.addStretch(); root.addLayout(top)
        self.table=QTableWidget(0,9); self.table.setHorizontalHeaderLabels(["來源圖片","類型","股票","日期","價格","股數","券商編號","辨識狀態","正式確認"]); self.table.doubleClicked.connect(self.confirm_current); root.addWidget(self.table)
        note=QLabel("OCR 結果只建立待確認草稿，不會直接寫入正式交易。雙擊資料列後，會開啟與手動輸入相同的正式表單；仍須補完資金來源、貸款與買進批次等欄位。")
        note.setWordWrap(True); note.setStyleSheet("color:#64748b"); root.addWidget(note)
        actions=QHBoxLayout(); confirm=QPushButton("以正式表單確認選取列"); confirm.clicked.connect(self.confirm_current); close=QPushButton("關閉"); close.clicked.connect(self.accept); actions.addWidget(confirm); actions.addStretch(); actions.addWidget(close); root.addLayout(actions)

    def choose(self):
        files,_=QFileDialog.getOpenFileNames(self,"選擇券商交易截圖","","圖片 (*.png *.jpg *.jpeg)")
        if not files: return
        for file in files:
            try:
                text=self.ocr.extract_text(file); data=self.ocr.parse_trade(text); status="辨識完成"
            except Exception as exc:
                data={"raw_text":""}; status=str(exc)
            draft_id=self.repository.add_ocr_draft(file,"TRADE",data,duplicate_status="NOT_CHECKED")
            self.drafts.append({"id":draft_id,"file":file,"data":data,"status":status})
        self.refresh()

    def refresh(self):
        self.table.setRowCount(len(self.drafts)); complete=0
        for r,draft in enumerate(self.drafts):
            data=draft["data"]; required=all(data.get(k) for k in ("transaction_type","symbol","trade_date","price","shares")); complete+=int(required)
            values=[Path(draft["file"]).name, "買入" if data.get("transaction_type")=="BUY" else "賣出" if data.get("transaction_type")=="SELL" else "待確認", data.get("symbol",""), data.get("trade_date",""), data.get("price",""), data.get("shares",""), data.get("broker_order_id",""), draft["status"], "雙擊開啟"]
            for c,value in enumerate(values): self.table.setItem(r,c,QTableWidgetItem(str(value)))
        self.table.resizeColumnsToContents(); self.summary.setText(f"已選取 {len(self.drafts)} 張｜必要欄位辨識完整 {complete} 筆｜待人工處理 {len(self.drafts)-complete} 筆")

    def confirm_current(self):
        row=self.table.currentRow()
        if row<0 or row>=len(self.drafts): QMessageBox.information(self,"請選擇資料","請先選取一筆 OCR 草稿"); return
        data=self.drafts[row]["data"]
        if data.get("transaction_type")=="BUY": dialog=BuyDialog(self.repository,self,prefill=data)
        elif data.get("transaction_type")=="SELL": dialog=SellDialog(self.repository,parent=self,prefill=data)
        else: QMessageBox.warning(self,"交易類型不明","OCR 尚未判斷買入或賣出，請改用上方工具列的手動輸入表單。"); return
        dialog.exec()
