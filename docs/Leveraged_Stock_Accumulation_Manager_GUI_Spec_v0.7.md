# Leveraged Stock Accumulation Manager
## GUI 規格書

版本：Draft v0.1

GUI 不直接複製 Excel 排版，而依工作流程規劃：

```text
查看整體狀況
→ 查看目前持股
→ 展開 Buy Lots
→ 找到接近策略目標的 Lot
→ 模擬回本賣出
→ 紀錄成交
→ 更新貸款／股利／公司行動
→ 與券商持股對帳
```

# 1. 主畫面

```text
Dashboard
目前持股 ★
策略機會 ★
交易 / Lots
股利 / 公司行動
貸款與資金
績效分析
股票價格
對帳 ★
資料 / 設定
```

# 2. Dashboard

KPI：

- 股票總市值
- 貸款餘額
- 尚未回收本金
- Free Shares 市值
- 累計 Cash Surplus
- 累計現金股利
- 累計貸款利息
- Strategy Net Value
- 最後完整對帳日期

建議圖表：

1. 資產形成 Waterfall
2. 月度 Cash Flow
3. 年度策略績效
4. Loan Balance vs Free Shares Value
5. Capital-at-Risk Distribution
6. Free Shares Value Growth

# 3. 目前持股

一檔股票一列：

| 股票 | 現價 | System Shares | Broker Shares | 差異 | 市值 | Lots | Free Shares | Free Value | 未回收本金 | Default Target | 對帳 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|

選取股票時顯示：

```text
006208 富邦台50

Current Price             235.35
System Shares             1,303
Broker Shares             1,303
Reconciliation            MATCHED

Default Target Return     +15%
Near Target Range          2%
Default Recovery Mode      Principal

[策略設定]
```

# 4. 股票策略設定 Dialog

每檔股票有自己的預設策略：

```text
預設目標報酬
[ 15.0 ] %

接近目標提示範圍
[ 2.0 ] %

預設回收模式
[ 回收原始本金 ▼ ]

股利是否納入回收
[ ] Yes

預設 Funding
[ Loan ▼ ]

策略提醒
[x] Enabled

[取消] [儲存]
```

規則：

- 修改股票策略只影響未來新 Buy Lot。
- 不修改既有 Lot 的歷史 Target。
- 修改寫入 Audit Log。

# 5. Buy Lot Table

| Lot | 買入日 | Broker | Funding | Buy Price | 原股數 | 現股數 | Current Return | Lot Target | Distance | Recovery | Status |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|

同一股票不同 Lot 可以有不同 Target，例如 +5%、+8%、+12%。即使股票目前 Default Target 已改為 +15%，歷史 Lot 不變。

# 6. Lot Detail Panel

右側 Drawer 顯示：

## Buy
- 日期
- Broker
- Buy Price
- Original Shares
- Original Investment
- Fees

## Funding
- CASH / LOAN / MIXED
- Cash Funded
- Loan Funded
- Loan ID
- Loan Principal Repaid
- Outstanding Loan
- Loan Interest

## Strategy

```text
Lot Target Return      +12%
Target Price           164.08
Current Return         +15.3%
Distance to Target     Reached
Recovery Mode          Principal

[修改此 Lot 策略]
```

## Recovery
- Net Cash Recovered
- Capital Recovery Ratio
- Full Cost Recovery Ratio
- Cash Surplus
- Remaining Capital at Risk
- Strategy Cost / Remaining Share

## Position
- Remaining Shares
- Stock Dividend Shares
- Current Market Value
- Free Shares
- Free Share Value

快捷按鈕：

```text
[模擬回本賣出]
[新增 Sell]
[新增公司行動]
[查看 Timeline]
[編輯 Lot]
```

# 7. 新增 Buy Lot

選股票後自動帶入該股票 Default Target：

```text
Security Default Target
+15%

This Lot Target
[15.0] %
```

使用者可在建立前覆寫，例如改成 +12%。建立後該 Lot 固定保存 +12%。

# 8. 策略機會頁

用來找出「目前接近或已達各自 Target」的 Buy Lot。每一個 Lot 使用自己的 `target_return_pct`。

| 股票 | Lot | Buy Price | Current | Current Return | Lot Target | Distance | Recovery | 建議賣股 | 預計剩餘 | Action |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|

篩選：

- TARGET REACHED
- NEAR TARGET
- All Active
- 股票
- Broker
- Funding
- Recovery Status

預設排序：

1. TARGET REACHED
2. 距 Target 最近
3. Current Return
4. Buy Date

每列提供 `[模擬]`，不直接建立 Sell。

# 9. 回本賣出模擬器

帶入 Current Price、Current Return、Lot Target、Target Price、Original Capital、Net Cash Recovered、Full Cost、Remaining Shares。

可切換：

```text
Recovery Target:
( ) Principal
( ) Principal + Trading Cost
( ) Full Cost
( ) Custom
```

顯示 Suggested Sell Shares、Estimated Net Cash、Capital Recovery after Sell、Loan Repayment Potential、Cash Surplus after Sell、Remaining Shares、Remaining Market Value。

# 10. 交易 / Lots

Tabs：

```text
Buy Lots
Sell Transactions
All Transactions
Lot Timeline
```

# 11. 股利 / 公司行動

Tabs：

```text
Cash Dividend
Stock Dividend / 配股
Stock Split
Reverse Split
Capital Reduction
Paid Allocation
```

# 12. 貸款與資金

顯示 Original Loan Principal、Current Loan Balance、Interest Rate、Interest Paid、Active Lot Exposure、Repaid from Sell。

建議圖表：Loan Balance vs Free Shares Market Value。

# 13. 股票價格

顯示 Stock、Current Price、Daily Change %、Price Date、Updated At、Source、Fresh / Stale。

操作：

```text
[Update All]
[Update Selected]
[Manual Price]
```

# 14. 對帳

| 股票 | System Shares | Broker Shares | Difference | Last Match | Status |
|---|---:|---:|---:|---|---|

按「完成本次對帳」建立 Reconciliation Session；Mismatch 不自動修正。

# 15. 績效分析

Tabs：

```text
Strategy Overview
Free Shares
Dividend
Loan Cost
Annual
Monthly Cash Flow
Broker
Stock
```

分析分成：

### Market Performance
Buy Price → Current Price

### Capital Recovery
Original Capital → Cash Recovered → Remaining Capital at Risk

### Strategy Performance
Cash Surplus + Free Shares Value + Dividend - Loan Interest - Trading Cost

不可混成單一報酬率。

# 16. GUI 顯示原則

1. 主表只放高頻資訊，完整資料放 Detail Panel / Timeline。
2. 股票 Default Target 與 Lot Target 必須同時清楚可見。
3. 修改股票 Default Target 不可回溯修改舊 Lot。
4. Lot Target 可以個別修改。
5. Market Return、Capital Recovery、Strategy Performance 分開顯示。
6. 對帳狀態明確使用 MATCHED / MISMATCH / NOT CHECKED。
7. Strategy Opportunity 頁依每個 Lot 自己的 Target 計算，不使用單一全域門檻。

這份 GUI 規格作為後續 PySide6 Wireframe 與實作基準。


---

# 17. Strategy Unit 與新增 Buy GUI

新增 Buy Lot 頁加入：

```text
Default Buy Budget
NT$10,000

Current / Input Price
NT$51.05

Suggested Shares
195

Estimated Stock Amount
NT$9,954.75
```

系統依固定 Budget 建議「不超過 Budget 的最大整數股數」。

使用者仍可修改股數與實際成交價格。

---

# 18. 回本模擬器：Recovery Tolerance

回本模擬器新增：

```text
Recovery Tolerance
[ NT$100 ]

Optimization Mode
● 優先保留最多股票
○ 必須完整回收本金
○ 最接近本金
```

模擬結果至少同時顯示兩個相鄰整數股方案：

| 方案 | Sell Shares | Net Cash | Difference | Remaining Shares | Status |
|---|---:|---:|---:|---:|---|
| 保留較多股票 | 45 | 9,954 | -33 | 6 | Recommended |
| 完整超過本金 | 46 | 10,175 | +188 | 5 | Alternative |

若差額在 Tolerance 內：

```text
Accounting Recovery     99.67%
Strategy Status         COMPLETED_WITH_TOLERANCE
Recovery Difference     -33
Remaining Shares        6
```

GUI 不得把 99.67% 偽裝成 100%。

---

# 19. 截圖匯入工作台

支援一張券商 App 截圖辨識多筆交易。

主表：

| # | 股票 | 類型 | 股數 | 價格 | OCR 狀態 | Lot 建議 | 確認狀態 |
|---|---|---|---:|---:|---|---|---|

BUY：

- 建立 Buy Lot Draft
- 帶入 Funding 預設
- 帶入股票 Default Target
- 帶入 Strategy Unit

SELL：

- 搜尋同股票 Active Lots
- 預設選取預估獲利率最高且股數足夠的 Lot
- 使用者最後確認或改選

正常 V1 Sell 不做跨多 Lot 自動分配。

疑似重複交易顯示：

```text
POSSIBLE DUPLICATE
```

並提供查看既有交易、忽略或仍然匯入。


---

# 20. 介面語言規範

本系統 GUI 一律採用 **繁體中文介面**。

所有使用者直接看到的內容，包括：

- 左側導覽列
- 頁面標題
- 表格欄位名稱
- 按鈕
- 下拉選單
- 狀態標籤
- 提示訊息
- 錯誤訊息
- 對帳結果
- 匯入確認畫面
- 圖表標題
- KPI 名稱
- 報表輸出標題

均以繁體中文顯示。

例如原本概念名稱在 GUI 中改為：

```text
Dashboard                 → 儀表板
Current Holdings          → 目前持股
Strategy Opportunities    → 策略機會
Transactions / Lots       → 交易 / 買進批次
Corporate Actions         → 股利 / 公司行動
Loans & Funding           → 貸款與資金
Performance Analysis      → 績效分析
Stock Prices              → 股票價格
Reconciliation            → 對帳
Data / Settings           → 資料 / 設定

Buy Lot                   → 買進批次
Sell                      → 賣出
Current Return            → 目前報酬率
Target Return             → 目標報酬率
Target Price              → 目標價格
Distance to Target        → 距離目標
Capital Recovery          → 本金回收
Full Cost Recovery        → 完整成本回收
Cash Surplus              → 超額回收現金
Remaining Capital at Risk → 尚未回收本金
Free Shares               → 免費持股 / 已回本持股
System Shares             → 系統計算持股
Broker Shares             → 券商實際持股
Difference                → 差異股數
Matched                   → 對帳一致
Mismatch                  → 對帳不一致
Not Checked               → 尚未對帳
Near Target               → 接近目標
Target Reached            → 已達目標
```

程式內部、SQLite 欄位名稱、Python Enum、資料表名稱與開發文件可以保留英文識別名稱，例如：

```text
buy_lots
sell_transactions
target_return_pct
MATCHED
MISMATCH
```

但這些英文內部識別名稱不得直接顯示在一般使用者介面。

GUI 必須經由中文顯示文字轉換，例如：

```text
MATCHED                  → 對帳一致
MISMATCH                 → 對帳不一致
COMPLETED_WITH_TOLERANCE → 容許差額內完成回本
FREE_SHARES              → 已回本持股
```

技術性英文名稱如有必要，可在「說明 / Help」或開發模式中以括號輔助，但預設介面只呈現繁體中文。


---

# 21. GUI 架構重整：單一主表格 + 工具列

GUI 不再採用大量左側主頁切換。

核心操作改為：

```text
主畫面
= 交易 / 持股 Master Table

上方工具列
= 所有新增、匯入、更新、對帳、分析與設定入口
```

主畫面長時間維持在同一張核心表格，讓操作方式接近既有 Excel 使用習慣。

---

# 22. 主畫面配置

建議：

```text
┌────────────────────────────────────────────────────────────────────────────┐
│ 功能表 / 工具列                                                           │
├────────────────────────────────────────────────────────────────────────────┤
│ 篩選列：股票 / 券商 / 資金來源 / 狀態 / 日期 / 搜尋                       │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│                      核心交易 / 持股 Master Table                          │
│                                                                            │
├────────────────────────────────────────────────────────────────────────────┤
│ 狀態列：資料筆數 / 價格更新時間 / 對帳狀態 / 資料庫狀態                   │
└────────────────────────────────────────────────────────────────────────────┘
```

不設計多層級複雜 Navigation。

---

# 23. 上方工具列

工具列作為主要操作入口。

建議順序：

```text
[新增買入]
[新增賣出]
[新增股利]
[公司行動]

[截圖匯入 ▼]
    ├─ 交易截圖
    └─ 股利截圖

[回本模擬]
[更新股價]
[對帳]

[分析 ▼]
    ├─ 整體績效
    ├─ 年度績效
    ├─ 月度現金流
    ├─ 股利分析
    ├─ 已回本持股
    ├─ 貸款分析
    └─ 個股分析

[資料 ▼]
    ├─ Excel 匯入
    ├─ Excel 匯出
    ├─ CSV 匯出
    └─ 備份

[設定]
```

---

# 24. 核心 Master Table

Master Table 以每一個 Buy Lot 為一列。

建議欄位群組：

## 24.1 基本資料

- 買入日期
- 券商
- 股票
- 股票代號
- 資金來源
- Loan ID（如適用）

## 24.2 買入資料

- 買入價格
- 原始股數
- 買入成本
- 手續費
- 原始總投入

## 24.3 市場資料

- 現價
- 目前報酬率 %
- 目標報酬率 %
- 目標價格
- 距離目標 %
- 策略狀態

## 24.4 回收資料

- 累積淨回收現金
- 本金回收率
- 完整成本回收率
- 尚未回收本金
- 回本差額
- 回本狀態

## 24.5 持股資料

- 目前股數
- 已回本持股
- 目前市值
- 已回本持股市值
- 配股累積股數

## 24.6 貸款資料

- 貸款投入
- 已還貸款本金
- 尚未償還貸款本金
- 累積利息

## 24.7 歷史摘要

- 最近賣出日期
- 累積賣出股數
- 累積賣出所得
- 持有天數
- 最後修改時間

---

# 25. Master Table 欄位顯示模式

為避免欄位過多，工具列增加欄位視圖：

```text
[基本]
[市場]
[回收]
[持股]
[貸款]
[全部欄位]
```

不同模式只切換可見欄位，不改變底層資料。

使用者可以：

- 排序
- 篩選
- 搜尋
- 固定欄位
- 調整欄寬
- 儲存欄位配置

---

# 26. 條件格式

保留 Excel 熟悉的視覺提示。

例如：

- 目前報酬率：紅綠 Data Bar 或漸層
- 已達目標：醒目標籤
- 接近目標：黃色提示
- 已回本持股：特殊圖示
- 對帳不一致：紅色警示
- 價格過期：橘色警示
- OCR 待補欄位：淡黃色背景

---

# 27. 新增買入視窗

由工具列 `[新增買入]` 開啟。

正式輸入表單包含完整欄位。

例如：

```text
股票
券商
買入日期
買入價格
買入股數
買入成本
手續費

資金來源
貸款帳戶
現金投入
貸款投入

股票預設目標 %
此 Lot 目標 %

回本容許差額
回本模式

備註
```

手動新增時表單為空白或載入預設值。

OCR 新增時使用完全相同的正式表單，只是部分欄位已自動填入。

---

# 28. 新增賣出視窗

由 `[新增賣出]` 開啟。

包含：

- 股票
- 賣出日期
- 賣出價格
- 賣出股數
- 成交金額
- 手續費
- 交易稅
- 實際淨回收

系統自動列出該股票 Active Buy Lots。

預設建議：

```text
目前獲利率最高且股數足夠的 Lot
```

但最後由使用者確認或改選。

顯示：

- Buy Lot 原始買價
- 目前／此次賣出報酬
- 該 Lot 目前股數
- 賣出後剩餘股數
- 本金回收率
- 是否達回本容許範圍
- 預計已回本持股

---

# 29. 新增股利視窗

由 `[新增股利]` 開啟。

正式表單可包含：

- 股票
- 券商
- 股利類型
- 除息／除權基準日
- 入帳日
- 基準股數
- 每股股利
- 稅前股利
- 稅額
- 補充保費
- 其他費用
- 實收股利
- 備註

若資訊不足，不強制所有非必要欄位。

系統可依基準日持股協助驗證股數。

---

# 30. 多圖 OCR 匯入

工具列：

```text
[截圖匯入]
```

支援：

- 一次選取多個 PNG / JPG / JPEG
- Drag & Drop 多圖
- 同一張圖片辨識多筆交易
- 多張圖片一次批次辨識
- 可混合處理多張相同類型截圖

V1 建議分成：

```text
交易截圖
股利截圖
```

避免 OCR 類型判斷過度複雜。

---

# 31. OCR 的定位

OCR 不直接建立正式資料。

OCR 只做：

```text
辨識圖片
→ 擷取可辨識欄位
→ 建立待確認 Draft
→ 將辨識值填入正式人工輸入表單
```

原因：

- 截圖不一定包含所有資料庫必要欄位
- 資金來源通常無法從券商截圖判斷
- 貸款帳戶需要人工確認
- Lot Target 可能來自股票預設或人工覆寫
- Sell 對應哪個 Buy Lot 必須最後確認

因此：

```text
OCR ≠ 直接匯入
OCR = 自動預填人工輸入表單
```

---

# 32. 多圖 OCR 匯入工作台

一次選取多張圖後，先進入匯入工作台。

上方顯示：

```text
已選取圖片：8 張
辨識完成：8 張
辨識資料：23 筆
待人工處理：5 筆
```

圖片層清單：

| 圖片 | 辨識筆數 | 類型 | 狀態 |
|---|---:|---|---|
| IMG_001.png | 4 | 交易 | 完成 |
| IMG_002.png | 6 | 交易 | 完成 |
| IMG_003.png | 3 | 股利 | 有疑問 |

---

# 33. OCR Draft Table

辨識結果先形成 Draft Table。

交易例如：

| 勾選 | 股票 | 類型 | 日期 | 價格 | 股數 | 金額 | 資金來源 | 目標% | 對應 Lot | 狀態 |
|---|---|---|---|---:|---:|---:|---|---:|---|---|

股利例如：

| 勾選 | 股票 | 入帳日 | 基準股數 | 每股股利 | 稅前 | 實收 | 狀態 |
|---|---|---|---:|---:|---:|---:|---|

雙擊任一 Draft：

```text
→ 開啟同一套正式人工輸入表單
→ OCR 欄位已自動填入
→ 缺少欄位由使用者補完
→ 使用者最後確認
```

---

# 34. OCR 欄位來源標記

正式表單中可用圖示或淡色標示：

```text
OCR 自動填入
系統預設
系統計算
人工輸入
```

例如：

```text
買入價格   176.30     [OCR]
資金來源   貸款       [人工]
目標報酬   5.0%       [股票預設]
買入成本   9,873      [系統驗算]
```

這可以讓使用者快速知道哪些欄位最需要人工注意。

---

# 35. 批次共同欄位

多圖匯入工作台提供批次預設：

```text
本次券商
本次資金來源
本次貸款帳戶
```

並提供：

```text
[套用到所有空白欄位]
```

只填補空白，不覆蓋 OCR 已確認值或人工已修改值。

---

# 36. OCR BUY 流程

例如 OCR 辨識：

```text
股票：富邦50
日期：2026/03/04
價格：176.3
股數：56
金額：9,873
```

正式表單自動填入以上資料。

系統再補：

```text
股票 Default Target
Strategy Unit
建議 Funding（若有設定）
```

使用者補：

```text
資金來源
貸款帳戶
必要備註
```

確認後才建立 Buy Lot。

---

# 37. OCR SELL 流程

OCR 辨識：

```text
股票
日期
賣出價格
賣出股數
成交金額
```

正式賣出表單再自動搜尋候選 Buy Lots。

預選：

```text
目前獲利率最高且股數足夠的 Lot
```

最後使用者確認。

---

# 38. OCR 股利流程

OCR 可自動擷取：

- 股票
- 股利入帳日期
- 基準股數（若畫面有）
- 每股股利（若畫面有）
- 稅前金額（若畫面有）
- 稅費（若畫面有）
- 實收金額

再開啟正式股利表單。

缺少：

- 除息／除權基準日
- 股利類型
- 券商
- 其他欄位

由系統預設、資料庫推導或人工補完。

確認後才建立正式 Dividend Event。

---

# 39. OCR 驗證

提交前至少進行：

## 交易

- 股票有效
- 日期有效
- 股數 > 0
- 價格 > 0
- 金額與股數 × 價格合理
- BUY Funding 已填
- SELL 對應 Lot 已確認
- SELL 股數 <= Lot 可用股數

## 股利

- 股票有效
- 金額合理
- 若有基準股數與每股股利，檢查乘積
- 若系統有基準日持股，提供交叉比對

---

# 40. 重複匯入檢查

OCR Draft 建立前檢查可能重複紀錄。

交易參考：

- 券商
- 股票
- 買／賣
- 日期
- 時間（若有）
- 股數
- 價格
- 金額
- 成交序號（若有）

股利參考：

- 券商
- 股票
- 入帳日期
- 股利類型
- 實收金額

疑似重複：

```text
可能重複
```

必須人工決定：

```text
[查看既有資料]
[忽略]
[仍然加入]
```

---

# 41. 分析功能呈現方式

分析不作為大量常駐主頁。

從工具列 `[分析]` 開啟獨立分析視窗或分頁。

內容包括：

- 整體績效
- 年度績效
- 月度現金流
- 股利
- 已回本持股
- 貸款
- 個股
- 回本差額統計
- 對帳歷史

關閉分析後回到同一張 Master Table。

---

# 42. GUI 最終使用流程

日常：

```text
開啟程式
↓
Master Table
↓
更新股價
↓
查看目前報酬 / 目標 / 回收狀態
↓
需要操作時使用上方工具列
```

大量輸入：

```text
截圖匯入
↓
一次選多張圖片
↓
OCR 批次辨識
↓
Draft Table
↓
雙擊 Draft
↓
同一套正式人工輸入表單
↓
補完缺少欄位
↓
驗證
↓
人工確認
↓
正式寫入 SQLite
```

此架構優先考慮：
- 熟悉 Excel 的使用習慣
- 減少頁面切換
- 保留完整資料庫與自動計算能力
- OCR 只負責加速輸入，不取代人工確認


---

# 43. 券商下單編號與成交編號

正式「新增買入」與「新增賣出」表單加入：

```text
券商下單編號
券商成交編號（如有）
```

券商下單編號應放在交易基本資料區，而不是備註。

例如：

```text
券商             [口袋證券 ▼]
交易日期         [2026/08/09]
券商下單編號     [A123456789]
券商成交編號     [987654321]   （若有）
股票             [富邦50]
...
```

---

# 44. 即時重複編號檢查

當：

- OCR 自動填入券商下單編號
- 使用者手動輸入券商下單編號
- 使用者按下「確認加入」

都必須查詢正式資料庫。

若相同券商帳戶已有相同有效編號：

```text
⚠ 此券商下單編號已存在，不能重複加入
```

並顯示：

```text
既有交易

日期：
股票：
買入 / 賣出：
股數：
價格：
券商下單編號：

[查看既有交易]
[取消本次輸入]
```

重複券商編號不得以一般確認按鈕強制加入。

---

# 45. OCR Draft 重複狀態

OCR Draft Table 新增：

```text
券商編號
重複檢查
```

例如：

| 股票 | 類型 | 日期 | 股數 | 價格 | 券商編號 | 重複檢查 | 狀態 |
|---|---|---|---:|---:|---|---|---|
| 富邦50 | 買入 | 3/4 | 56 | 176.3 | A12345 | 未發現 | 可確認 |
| 富邦50 | 賣出 | 8/18 | 40 | 124.35 | A12291 | 已存在 | 禁止匯入 |

狀態：

```text
未發現重複
疑似重複
確定重複
券商編號缺失
```

其中「確定重複」列不可勾選進行正式匯入。

---

# 46. 券商編號缺失時的 GUI

若 OCR 沒有讀到或歷史交易沒有編號：

```text
券商下單編號
[                    ]

⚠ 未提供券商編號，將使用交易日期、股票、股數、價格與金額進行疑似重複檢查
```

不因此禁止建立歷史資料，但應保留警示。

---

# 47. 券商編號規則設定

設定視窗的「券商帳戶」中預留：

```text
券商編號唯一範圍

● 整個帳戶唯一
○ 每交易日重新編號
○ 下單編號 + 成交編號
```

不同券商可使用不同 Duplicate Key 規則。


---

# 48. 資料與備份工具列

上方工具列的 `[資料]` 選單調整為：

```text
資料 ▼
├─ 從 Excel 匯入
├─ 匯出完整 Excel
├─ 匯出目前表格
├─ 匯出 CSV
├─ 立即完整備份
├─ 備份歷史
├─ 還原備份
└─ 備份設定
```

---

# 49. 備份設定視窗

採繁體中文介面。

## 49.1 自動備份

```text
☑ 程式啟動時自動備份

備份頻率
● 每次啟動
○ 每日第一次啟動

☐ 程式關閉時自動備份
☑ 大量資料匯入前自動備份
☑ 資料庫升級前自動備份
```

## 49.2 多位置備份

使用表格管理：

| 啟用 | 名稱 | 類型 | 備份位置 | 最後成功 | 狀態 |
|---|---|---|---|---|---|
| ☑ | 本機備份 | 本機資料夾 | D:\StockManager\Backup | 今天 07:35 | 成功 |
| ☑ | Google Drive | Google Drive 同步資料夾 | G:\我的雲端硬碟\StockManager | 今天 07:35 | 成功 |
| ☑ | 外接硬碟 | 本機資料夾 | E:\StockBackup | 昨天 | 未連線 |

操作：

```text
[新增位置]
[編輯]
[停用]
[測試寫入]
[立即備份到此位置]
```

---

# 50. 新增備份位置視窗

```text
名稱
[Google Drive]

類型
[Google Drive 同步資料夾 ▼]

路徑
[G:\我的雲端硬碟\StockManager_Backup] [瀏覽]

☑ 啟用

保留方式
[最近 30 日 ▼]

[測試]
[取消]
[儲存]
```

V1 Google Drive 使用 Google Drive for desktop 同步資料夾。

未來可增加「Google Drive API」類型。

---

# 51. 程式啟動備份提示

啟動程式時不要跳出大量阻塞視窗。

建議在 Splash / Status 顯示：

```text
正在檢查資料庫...
正在建立自動備份...
本機備份：成功
Google Drive：成功
外接硬碟：未連線
```

進入主畫面後狀態列顯示：

```text
備份：2 / 3 成功  ⚠
```

點擊後查看詳細資訊。

若全部成功：

```text
備份：3 / 3 成功
```

---

# 52. 備份歷史視窗

表格：

| 日期時間 | 觸發方式 | DB | Excel | 備份位置成功數 | 狀態 |
|---|---|---|---|---:|---|
| 2026/08/09 07:35 | 程式啟動 | 成功 | 成功 | 3/3 | 成功 |
| 2026/08/08 19:12 | 手動 | 成功 | 成功 | 2/3 | 部分成功 |

點擊一筆可以查看：

- 每個位置結果
- 實際路徑
- 錯誤訊息
- Manifest
- Hash
- 是否可還原

---

# 53. 完整 Excel 匯出視窗

提供：

```text
匯出類型

● 完整備份 Excel
○ 目前 Master Table
○ 目前篩選結果
```

完整備份 Excel 包含多個 Sheet，不只目前表格。

完成後顯示：

```text
匯出完成
檔案：
...

[開啟所在資料夾]
```

---

# 54. 還原備份視窗

SQLite Restore 流程：

```text
選擇備份
↓
顯示日期 / 程式版本 / DB 版本
↓
驗證完整性
↓
自動備份目前資料
↓
再次確認
↓
還原
```

不得提供未確認的一鍵覆寫正式資料庫。


---

# 55. KPI 與分析視窗

分析視窗從上方工具列：

```text
[分析]
```

開啟。

不影響主畫面 Master Table。

分析視窗第一頁預設為：

```text
策略總覽
```

---

# 56. 策略總覽版面

上方 KPI Cards：

```text
股票總市值
原始累積投入
累積回收現金
尚未回收本金
已回本持股市值
累積股利
累積貸款利息
目前貸款餘額
已回本 Lot 數 / 比例
```

優先放大：

```text
已回本持股市值
尚未回收本金
目前貸款餘額
```

下方主要圖：

1. 資產形成 Waterfall
2. 已回本持股成長曲線
3. 貸款餘額 vs 已回本持股市值
4. Lot 回收狀態分布

---

# 57. 本金回收分析

Tabs / Section：

```text
尚未回收本金
回收狀態
回本差額
回本天數
未回本 Lot 年齡
回本完成率
```

## 尚未回本本金

Bar Chart，可切換：

```text
依股票
依券商
依貸款
依資金來源
```

## 未回本 Lot 年齡

建議：

```text
<30天
30–90天
90–180天
180–365天
>1年
```

並顯示該區間：

- Lot 數
- 尚未回收本金
- 貸款曝險
- 利息

---

# 58. 現金流分析

至少：

```text
月度現金流
累積現金回收
```

月度現金流可顯示：

- 買入支出
- 賣出淨回收
- 股利
- 貸款還款
- 利息
- 交易成本
- 淨現金流

---

# 59. 股利分析

至少：

```text
每月股利
年度股利
累積股利
股利來源結構
```

可切換：

```text
全部股利
已回本持股股利
尚未回本持股股利
```

---

# 60. 貸款分析

至少：

```text
貸款餘額趨勢
每月利息
累積利息
貸款成本 vs 已回本資產
```

---

# 61. 個股分析

比較：

- Buy Lot 數
- 已回本 Lot 數
- 回本完成率
- 尚未回收本金
- 已回本持股市值
- 累積股利
- 累積利息
- Cash Surplus

目的為比較策略成果，不只是股價報酬。

---

# 62. 市場環境分析

取消「Target % 效率」作為核心分析。

改為：

```text
Benchmark 同期報酬
同期大盤報酬 vs 回本時間
市場階段策略表現
```

Scatter Plot：

```text
X 軸：
Buy → Recovery 期間 Benchmark Return %

Y 軸：
Recovery Days
```

Benchmark 預設可使用台灣加權指數，並允許使用者變更。

第一版不強制將市場分類為牛市 / 熊市。

---

# 63. 圖表互動

分析圖應盡量可與 Master Table 連動。

例如：

```text
點擊「已達目標待處理」
→ 關閉 / 切回主畫面
→ Master Table 套用此狀態 Filter
```

或：

```text
點擊某股票 Bar
→ Master Table 只顯示該股票
```

分析不是純靜態報表，而是資料探索入口。
