# 貸款槓桿存股管理系統 v1.1.0

依照《Leveraged Stock Accumulation Manager 功能需求規格 v0.8》與《GUI 規格 v0.7》建立的模組化 Python 桌面程式。

## 快速開始（Windows）

1. 安裝 Python 3.11（建議 3.11.9）或 Python 3.12。
2. 第一次使用：雙擊 `setup_and_run.bat`。程式會建立 `.venv` 並安裝套件。
3. 之後使用：雙擊 `run.bat`。

> v1.0.1 已將兩個 Windows 啟動檔改為 CRLF 格式，並使用程式自身所在資料夾作為工作目錄，避免從 `C:\Windows\System32` 啟動時發生路徑解析錯誤。

正式 SQLite 資料與輸出預設放在：

```text
%USERPROFILE%\StockAccumulationManager\
├─ data\portfolio.db
├─ backups\
├─ exports\
└─ logs\stock_manager.log
```

如需指定資料根目錄，可先設定環境變數 `STOCK_MANAGER_DATA_DIR`。

## 已實作重點

- 單一買進批次 Master Table、工具列、篩選、搜尋與欄位檢視。
- 每次買進建立獨立 Lot；賣出必須指定 Lot，不採 FIFO。
- 賣出股數不得超過該 Lot 剩餘股數。
- 本金回收率不封頂，可正確顯示超過 100%。
- 原始本金、完整成本、超額回收現金、尚未回收本金與已回本持股分開計算。
- Recovery Tolerance 與三種整數股最佳化模式。
- 每檔股票預設策略與 Lot 歷史策略分離；修改預設值不回溯舊 Lot。
- 貸款帳戶、還款、利息與賣出現金分開記錄。
- 券商下單／成交編號硬性防重複，跨買入與賣出共同檢查。
- 股利、公司行動、手動股價、持股對帳與稽核紀錄。
- 目前持股盤後股價自動更新：上市採 TWSE、上櫃採 TPEx 官方個股端點，不下載或保存全市場行情。
- 程式啟動背景補更新與可調整的 14:30／15:00／17:00 盤後排程；單檔失敗不影響其他股票或 GUI 操作。
- 保留 OHLC、成交量、成交金額、成交筆數、漲跌、資料來源與取得時間；失敗時沿用舊價格並標示狀態。
- 可選 FinMind 第三方備援（預設關閉、可設定 Token），並保留手動輸入作為最終備援。
- 完整多工作表 Excel、目前表格 CSV、欄位 Mapping 匯入。
- SQLite 一致性快照、Excel、Manifest、SHA-256、多位置備份與備份歷史。
- 可選 Google Drive for desktop 同步資料夾作為備份位置。
- 策略 KPI、本金風險、回收狀態與未回本 Lot 年齡分析。
- 多張券商截圖 OCR Draft；辨識後仍須進同一套正式表單人工確認。

## OCR 注意事項

Python 套件會自動安裝，但圖片文字辨識還需要作業系統安裝 Tesseract OCR 與繁體中文語言資料。未安裝時不會影響其他功能，可直接使用手動輸入或 Excel 匯入。

## 資料安全

- SQLite 是唯一正式主資料庫；Excel 是人類可讀備份與移轉格式。
- 首次啟動會建立預設本機備份位置。
- 預設每日第一次啟動執行完整備份。
- 大量 Excel 匯入前會先嘗試完整備份。
- 備份會驗證 SQLite `integrity_check`、Excel 可讀性與 SHA-256。

## 測試

在專案資料夾執行：

```powershell
.venv\Scripts\python.exe -m unittest discover -v
```

測試涵蓋本金回收、容許差額、整數股最佳化、券商編號防重複、Lot 賣出限制、股票策略歷史隔離、Excel、完整備份、舊資料庫升級、官方報價解析、持股篩選、快取與手動價格優先序。
