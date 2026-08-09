# Leveraged Stock Accumulation Manager
## 功能需求規格書

版本：Draft v0.1  
定位：以「貸款槓桿建立股票部位 → 上漲後賣出部分持股回收本金／償還貸款 → 剩餘股票轉為長期存股」為核心的股票交易與資金管理系統。

---

# 1. 系統核心概念

本系統不是一般股票記帳軟體，也不採用 FIFO（先進先出）方式處理股票成本。

每一次買進都建立一個獨立的 **Buy Lot（買進批次）**。

每一筆賣出交易都必須明確指定其所屬的 Buy Lot，因此：

- 不自動使用 FIFO。
- 不使用平均成本去決定某筆賣出屬於哪一次買進。
- 同一檔股票可以同時存在多個不同 Buy Lot。
- 一個 Buy Lot 可以對應多筆 Sell。
- 每一筆 Sell 只能對應到指定的 Buy Lot。
- 每個 Buy Lot 都有自己的買進價格、股數、貸款來源、利息、回收狀態與剩餘股票。

核心投資流程：

```text
貸款／資金
   ↓
建立 Buy Lot
   ↓
股票上漲
   ↓
賣出部分股票
   ↓
回收現金
   ↓
償還貸款／回收本金
   ↓
剩餘股票繼續持有
   ↓
形成存股／Free Shares
```

---

# 2. Buy Lot（買進批次）

每一次買進建立唯一 Lot ID。

例如：

```text
LOT-000001
股票：2330
買進日期：2026-01-10
買進股數：10 股
買進均價：924.3
原始買進金額：9,243
資金來源：貸款 L001
```

## 2.1 Buy Lot 必要欄位

至少包含：

- Lot ID
- 股票代號
- 股票名稱
- 市場
- 買進日期
- 原始買進股數
- 買進價格
- 股票成交金額
- 買進手續費
- 其他買進成本
- 原始總投入
- 資金來源
- 對應 Loan ID
- 使用貸款金額
- 使用自有資金金額
- 投資策略
- 目標獲利率
- 備註
- 建立時間
- 最後修改時間

## 2.2 Buy Lot 狀態

每個 Lot 應有狀態，例如：

- Active：仍在持有且本金尚未回收
- Principal Recovered：本金已回收
- Full Cost Recovered：本金、交易成本與已計貸款成本均已回收
- Free Shares：完整成本已回收且仍有剩餘持股
- Closed：股票已全部賣出
- Loss Closed：全部賣出且最終為虧損
- Archived：封存

---

# 3. Sell（賣出交易）

每一筆 Sell 必須手動選擇對應的 Buy Lot。

例如：

```text
Sell ID：SELL-000045
對應 Lot：LOT-000001
賣出日期：2026-03-20
賣出股數：4 股
賣出價格：1,100
```

## 3.1 Sell 必要欄位

- Sell ID
- Buy Lot ID
- 股票代號
- 賣出日期
- 賣出股數
- 實際成交價格
- 成交總額
- 賣出手續費
- 交易稅
- 其他費用
- 實際淨回收現金
- 是否用於償還貸款
- 實際償還貸款金額
- 備註

## 3.2 賣出限制

程式必須檢查：

- 賣出股數不得大於該 Buy Lot 當時剩餘股數。
- 不允許將賣出交易自動配對到其他 Lot。
- 修改歷史 Sell 時必須重新計算該 Lot 後續所有統計結果。

---

# 4. 本金回收模型

本系統不要求「回收金額剛好等於原始本金」。

例如：

```text
原始投入：9,243 元
部分賣出後實際淨回收：9,321 元
剩餘持股：6 股
```

系統應記錄為：

```text
Original Capital       9,243
Net Cash Recovered     9,321
Capital Recovery       100.84%
Cash Surplus               78
Remaining Shares            6
```

因此：

- 本金回收率可以高於 100%。
- 不將超額回收金額捨棄。
- 不要求回收金額等於本金。
- 不把超額回收金額強制轉成剩餘股票成本。
- 剩餘股票繼續獨立追蹤。

## 4.1 核心三項數值

每個 Lot 永遠維護：

1. Original Capital  
   原始投入金額。

2. Net Cash Recovered  
   該 Lot 所有 Sell 實際淨收入的累積值。

3. Remaining Shares  
   原始股數扣除所有 Sell 後剩餘股數。

## 4.2 Capital Recovery Ratio

```text
Capital Recovery Ratio
= Net Cash Recovered / Original Capital
```

可自然顯示：

- 72.5%
- 98.4%
- 100.0%
- 100.84%
- 115.2%

不得限制最大值為 100%。

## 4.3 Cash Surplus

當：

```text
Net Cash Recovered > Original Capital
```

則：

```text
Cash Surplus
= Net Cash Recovered - Original Capital
```

例如：

```text
9,321 - 9,243 = +78 元
```

這 78 元視為已實現的超額現金回收。

---

# 5. 完整成本回收

除單純本金回收外，系統還需要第二套指標：

**Full Cost Recovery**

完整成本可以包含：

- 原始股票投入
- 買進手續費
- 賣出手續費
- 交易稅
- 貸款利息
- 其他與該 Lot 有關的成本

例如：

```text
原始投入        9,243
買入成本           20
貸款利息          125
賣出交易成本        30
--------------------
Full Cost        9,418
```

如果目前累積淨回收為 9,321：

```text
本金回收率 = 100.84%
完整成本回收率 = 98.97%
```

因此可以出現：

```text
本金已回收 ✅
完整成本尚未完全回收 🟡
```

---

# 6. Free Shares／存股概念

當一個 Lot 已經完成完整成本回收，且仍有剩餘股票時，可以標記為：

**Free Shares**

Free Shares 不代表修改原始會計成本為 0。

系統必須同時保留：

- 原始買進成本
- 原始買進價格
- 歷史交易成本
- 歷史貸款成本

但是在「策略層」可以顯示：

```text
Capital at Risk = 0
Remaining Shares = 6
Free Shares = 6
```

Free Shares 的目前價值：

```text
Free Share Market Value
= Remaining Shares × Current Market Price
```

---

# 7. 每個 Lot 的策略成果

對已經回本的 Lot：

```text
Strategy Value
= Cash Surplus + Remaining Share Market Value
```

例如：

```text
原始投入             9,243
累積淨回收           9,321
Cash Surplus            78

剩餘股票                6 股
目前股價               205
剩餘股票市值         1,230

Strategy Value        1,308
```

這代表原始本金已回收後，目前由這個策略留下的額外經濟價值。

---

# 8. 貸款管理

貸款必須是獨立模組，而不是直接把一個利息數字寫在 Buy Lot 內。

## 8.1 Loan Account

每筆貸款至少包含：

- Loan ID
- 貸款名稱
- 金融機構
- 借款日期
- 原始本金
- 目前本金餘額
- 年利率
- 利率類型
- 起息日
- 到期日
- 還款方式
- 備註

## 8.2 Loan Transaction

記錄：

- 借款
- 還款
- 利息付款
- 利率調整
- 額外費用

## 8.3 Loan 與 Buy Lot 關係

每個 Buy Lot 可以記錄：

- 使用哪一筆 Loan
- 使用貸款金額
- 使用自有資金金額

未來應支援一個 Buy Lot：

- 100% 貸款
- 100% 自有資金
- 貸款＋自有資金混合

## 8.4 貸款利息分攤

需要保留彈性，未來可選：

- 按實際占用本金計算
- 按持有期間計算
- 使用使用者手動輸入的實際利息
- 依 Loan Account 自動計算
- 利息分攤至指定 Buy Lot

---

# 9. 償還貸款

賣出股票後取得的現金，不代表一定全部償還貸款。

每一筆 Sell 可以記錄：

```text
Net Cash Received = 9,321
Repay Loan = 9,000
Remain Cash = 321
```

因此要分開記錄：

- 股票賣出淨回收
- 實際貸款還款
- 留在帳戶中的現金

程式不可假設 Sell 收入一定等於 Loan Repayment。

---

# 10. 股票價格管理

系統需要一個獨立的「股票價格」頁面。

目的不是看盤，而是提供目前持股與每個 Buy Lot 的即時／最近價格基準。

## 10.1 股票價格頁面

顯示：

- 股票代號
- 股票名稱
- 市場
- 目前價格
- 今日漲跌
- 今日漲跌 %
- 最近交易日
- 價格更新時間
- 價格來源
- 自動／手動價格狀態

## 10.2 價格更新

需要：

- 更新全部持股價格
- 更新單一股票
- 自動取得價格
- 手動輸入價格
- API 失敗時可使用最近一次成功價格
- 清楚標示價格是否過期

## 10.3 價格來源

資料中必須保存：

```text
Price
Price Timestamp
Price Source
```

不可只保存價格而不知道資料時間。

## 10.4 非交易時間

週末、假日或市場休市時：

- 顯示最近一個交易日價格。
- 明確顯示資料日期。
- 不宣稱是即時價格。

---

# 11. 目前持股頁面

這是系統核心操作頁之一。

分成：

1. Stock Summary
2. Buy Lot Detail

## 11.1 Stock Summary

同一檔股票先彙整顯示一次：

- 股票代號
- 股票名稱
- 最新價格
- 總剩餘股數
- 總市值
- Buy Lot 數量
- 尚未回本 Lot 數
- 已回本 Lot 數
- Free Shares 股數
- Free Shares 市值

## 11.2 Buy Lot Detail

展開某一股票後顯示每一筆 Buy Lot：

- Lot ID
- 買進日期
- 原始股數
- 剩餘股數
- 買進價格
- 目前價格
- 目前價格報酬率 %
- 原始投入
- 已回收現金
- 本金回收率
- 完整成本回收率
- Cash Surplus
- 貸款利息
- Free Shares
- 剩餘股票目前市值
- Lot 狀態

---

# 12. 每筆 Buy Lot 的目前獲利／虧損 %

每個 Buy Lot 必須根據最新股票價格計算：

```text
Current Price Return %
= (Current Price - Buy Price) / Buy Price × 100%
```

例如：

```text
買進 100
目前 108

Current Return = +8%
```

即使是相同股票，不同 Buy Lot 仍分開顯示。

例如：

```text
2330

LOT-A：買進 900 → 現價 1000 → +11.11%
LOT-B：買進 950 → 現價 1000 → +5.26%
LOT-C：買進 1050 → 現價 1000 → -4.76%
```

---

# 13. 策略觸發價格

每個 Buy Lot 可以設定自己的策略目標，例如：

- +5%
- +10%
- +15%
- +20%
- 自訂 %

不可把 +10% 寫死。

顯示：

- 目前報酬 %
- 目標報酬 %
- 目標價格
- 距離目標價格差額
- 距離目標還差 %

例如：

```text
買進價格：100
目標：+10%
目標價：110
目前價：108

目前報酬：+8%
距離目標：+1.85%
```

---

# 14. 回本賣出模擬器

這是重要功能。

使用最新股票價格或自訂模擬價格，自動計算：

> 目前至少需要賣多少股，才可以達到指定的回收目標？

可以選擇目標：

- 回收原始本金
- 回收本金＋交易成本
- 回收本金＋已發生利息
- 回收全部完整成本
- 自訂回收金額

## 14.1 模擬結果

例如：

```text
目前價格：1,105

建議賣出：92 股
預估成交額：101,660
預估手續費：
預估交易稅：
預估淨回收：

原始本金：
完整成本：
預計 Cash Surplus：

預計剩餘：8 股
剩餘股票目前市值：
```

## 14.2 模擬與正式交易分開

模擬器：

- 不寫入正式交易資料。
- 不修改持股。

使用者實際成交後，再建立正式 Sell：

- 實際成交日期
- 實際成交價格
- 實際股數
- 實際手續費
- 實際交易稅

---

# 15. Lot 詳細頁

每個 Buy Lot 應有完整生命週期頁面。

例如：

```text
LOT-000001 / 2330

BUY
2026-01-10
10 股 @ 924.3
總投入 9,243

LOAN
Loan L001
使用貸款 9,243

SELL #1
2026-03-20
4 股 @ xxxx
淨回收 xxxx

SELL #2
2026-04-15
...
```

下方自動顯示：

```text
Original Shares
Sold Shares
Remaining Shares

Original Capital
Cash Recovered
Capital Recovery Ratio

Full Cost
Full Cost Recovery Ratio

Cash Surplus
Remaining Share Value
Strategy Value
```

---

# 16. Lot 狀態判斷

建議狀態：

## 🔴 Capital at Risk

```text
Net Cash Recovered < Original Capital
```

本金尚未完全回收。

## 🟡 Principal Recovered

```text
Net Cash Recovered >= Original Capital
```

但完整成本尚未回收。

## 🟢 Full Cost Recovered

本金、交易費用、貸款成本等已完全回收。

## 💎 Free Shares

```text
Full Cost Recovered
AND
Remaining Shares > 0
```

完整成本已回收且仍持有股票。

## ⚪ Closed

Remaining Shares = 0。

---

# 17. Dashboard

首頁需快速呈現整體策略狀況。

## 17.1 資金

- 累計投入股票本金
- 目前尚未回收本金
- 已回收本金
- Cash Surplus
- 現金餘額

## 17.2 貸款

- 累計借款
- 目前貸款餘額
- 累計償還本金
- 累計貸款利息
- 本月／今年利息

## 17.3 股票

- 目前持有股票市值
- 尚未回本股票市值
- Free Shares 股數
- Free Shares 市值
- Free Shares 股票種類數

## 17.4 策略成果

可顯示：

```text
累計投入本金
累計回收現金
尚未回收本金
Cash Surplus
Free Shares Market Value
累計貸款利息
Net Strategy Value
```

---

# 18. 個股分析

每檔股票可顯示：

- 歷史 Buy Lot 數
- Active Lot 數
- Free Share Lot 數
- 累積投入
- 累積回收
- Cash Surplus
- 目前剩餘股數
- Free Shares
- 目前市值
- 累計股利
- 累計利息成本
- 最終策略成果

---

# 19. 歷史交易

提供完整 Transaction History。

可以篩選：

- 股票
- Buy
- Sell
- 日期
- Buy Lot
- Loan
- 已回本
- 未回本
- Free Shares
- Closed

每筆資料可以追溯至原始 Lot。

---

# 20. Excel 匯入

第一版必須能匯入目前既有 Excel。

匯入流程應包含：

1. 選擇 Excel
2. 預覽欄位
3. 欄位 mapping
4. 資料檢查
5. 顯示錯誤／缺漏
6. 使用者確認
7. 寫入 SQLite

匯入時不可直接修改原 Excel。

---

# 21. Excel／CSV 匯出

可以輸出：

- 所有 Buy Lots
- 所有 Sell
- 目前持股
- Free Shares
- Loan
- Loan Repayment
- Lot Summary
- 個股 Summary
- Dashboard Summary

CSV 方便後續自行使用 Excel、Origin 或其他分析工具。

---

# 22. 資料庫

正式 Master Data 建議使用 SQLite。

Excel 不作為唯一主資料庫。

建議資料表至少包括：

```text
securities
price_history
buy_lots
sell_transactions
loans
loan_transactions
loan_lot_allocations
dividends
cash_transactions
settings
audit_log
```

---

# 23. 原始交易不可失去追溯性

所有結果都必須可以追溯。

例如：

```text
Strategy Value
    ↓
LOT-000001
    ↓
BUY-000001
SELL-000010
SELL-000025
LOAN-L001
INTEREST-00018
```

修改歷史紀錄時：

- 保留修改時間。
- 建議保留修改前內容。
- 自動重新計算衍生結果。

---

# 24. Audit Log

至少記錄：

- 新增
- 修改
- 刪除
- Excel 匯入
- 股價手動修改
- 貸款利率修改

內容包含：

- 時間
- 操作
- 資料 ID
- 原始值
- 新值

---

# 25. 股利

後續需要支援 Dividend。

每筆股利：

- 股票
- 日期
- 對應 Lot
- 股數
- 每股股利
- 稅前股利
- 稅／費用
- 淨股利

股利是否納入「完整成本回收」應作成可設定選項。

例如：

```text
Full Recovery Cash Flow
= Sell Cash + Dividend Cash
```

或只使用 Sell Cash。

---

# 26. 公司行動

公司行動已提升為 V1 核心功能。V1 優先支援：

- 股票分割
- 反向分割
- 股票股利／無償配股
- 現金股利
- 現金減資基本處理
- 有償配股／現金增資認購的資料結構

公司合併、股票代號更換等較複雜事件可於後續版本擴充。

所有公司行動皆以事件方式保存，不直接覆寫原始 Buy / Sell 紀錄。詳細規格見第 34 節。

---

# 27. 設定頁面

需要全域設定：

## 交易設定

- 預設市場
- 手續費算法
- 最低手續費
- 交易稅率
- 幣別

## 策略設定

- 預設目標報酬 %
- 預設回本模式
- Free Shares 判定方式
- 股利是否計入回本
- 利息是否計入 Full Cost

## 股價設定

- 價格來源
- 自動更新開關
- 更新頻率
- 市場時區

## 資料設定

- Database 路徑
- 自動備份
- 匯出位置

---

# 28. GUI 初步架構

```text
Leveraged Stock Accumulation Manager

Dashboard

目前持股
├─ Stock Summary
└─ Buy Lot Detail

Buy Lots
├─ Active
├─ Principal Recovered
├─ Free Shares
└─ Closed

交易
├─ 新增買進
├─ 新增賣出
├─ 回本賣出模擬器
└─ Transaction History

貸款
├─ Loan Accounts
├─ 借款
├─ 還款
├─ 利息
└─ Loan Allocation

股票價格
├─ Current Price
├─ Update All
├─ Update Selected
└─ Manual Price

分析
├─ Portfolio
├─ Individual Stock
├─ Capital Recovery
├─ Free Shares
├─ Loan Cost
└─ Strategy Performance

資料
├─ Import Excel
├─ Export Excel
├─ Export CSV
└─ Backup

設定
```

---

# 29. 第一版（V1）優先功能

V1 先完成核心可靠性，不追求太多外部功能。

優先順序：

1. SQLite Database
2. Excel 匯入
3. Buy Lot 建立與維護
4. 指定 Buy Lot 的 Sell
5. Remaining Shares 自動計算
6. Net Cash Recovered
7. Capital Recovery Ratio
8. Cash Surplus
9. 貸款帳戶
10. Loan ↔ Buy Lot 關聯
11. 利息紀錄
12. Full Cost Recovery
13. Free Shares 判斷
14. 股票價格頁
15. 最新價格更新
16. 每個 Lot Current Return %
17. 目前持股頁
18. 回本賣出模擬器
19. Dashboard
20. Excel／CSV Export
21. Backup

---

# 30. V2 可加入功能

後續再加入：

- 自動貸款利息進階計算
- 價格歷史
- 股價走勢
- Lot 報酬曲線
- 年度分析
- 月度分析
- XIRR
- Benchmark
- 資產配置
- 多幣別
- 匯率
- 公司合併／收購等進階 Corporate Actions
- 股票代號更換
- 通知功能

例如：

```text
LOT-000123
目前報酬 +9.8%
目標 +10%

接近策略觸發點
```

未來可增加提醒。

---

# 31. 目前最重要的設計原則

## 原則 1：Buy Lot 是核心

不是股票代號，也不是 FIFO。

每一次買進都是獨立投資事件。

## 原則 2：Sell 必須指定 Buy Lot

程式不自行猜測。

## 原則 3：本金回收不需要 exact match

例如：

```text
投入 9,243
收回 9,321
剩 6 股
```

是完全合法且正常的狀態。

## 原則 4：現金與股票分開統計

```text
Cash Recovered
Remaining Shares
```

不能混在一起。

## 原則 5：會計成本與策略成本分開

Free Shares 可以策略上視為「零本金風險」，但不能刪掉原始成本資料。

## 原則 6：貸款是真正核心資料

本系統的目的不是只看股票賺多少，而是理解：

```text
用了多少貸款
→ 承擔多少利息
→ 回收多少本金
→ 償還多少貸款
→ 最後留下多少股票
```

## 原則 7：所有計算都必須可追溯

任何 Dashboard 數字都能追到原始 Buy、Sell、Loan 與 Interest。

---

# 32. 系統最終希望回答的問題

這套程式最終應能直接回答：

- 我現在總共有多少個 Buy Lot？
- 哪些 Lot 正在賺錢？
- 哪些 Lot 正在虧錢？
- 每一個 Lot 現在是 +幾% 或 -幾%？
- 哪些 Lot 已經接近我的賣出觸發點？
- 現在賣多少股可以回收本金？
- 現在賣多少股可以回收完整成本？
- 哪些 Lot 已經收回本金？
- 哪些 Lot 已經完全回收利息與成本？
- 哪些股票已經成為 Free Shares？
- 我目前累積多少 Free Shares？
- Free Shares 現在值多少錢？
- 我累計借了多少錢？
- 我現在還欠多少貸款？
- 我總共支付多少利息？
- 每個 Buy Lot 分攤多少利息？
- 我透過這個策略實際留下多少股票資產？
- 使用貸款槓桿是否真的創造正的策略成果？
- 哪一檔股票最有效率地把貸款轉成 Free Shares？
- 哪些 Lot 因為持有太久，利息正在侵蝕獲利？

---

# 33. 系統定位總結

本系統的核心不是：

> 「這檔股票總共賺多少？」

而是：

> **「每一次用資金／貸款建立的股票部位，目前走到哪個階段；已經回收多少現金、償還多少貸款、花掉多少融資成本，最後成功留下多少可長期持有的股票。」**

核心資料單位：

```text
Loan
  ↓
Buy Lot
  ↓
Sell(s)
  ↓
Cash Recovery
  ↓
Loan Repayment
  ↓
Remaining Shares
  ↓
Free Shares
```

這套模型是後續 Python GUI、SQLite Schema、計算引擎與 Excel Migration 的設計基礎。


---

# 46. Security-Level Strategy／每檔股票獨立策略設定

不同股票的波動性、配息特性與持有目的不同，因此系統不得使用單一全域 Target Return % 套用所有股票。

每一檔股票必須有自己的預設策略設定，至少包含：

- Default Target Return %
- Near-Target Alert Range %
- Default Recovery Mode
- Dividend Included in Recovery：Yes / No
- Default Funding Preference：Cash / Loan / Mixed / None
- Strategy Reminder Enabled：Yes / No

例如：

```text
0056 元大高股息            Default Target = +8%
00878 國泰永續高股息       Default Target = +10%
006208 富邦台50            Default Target = +15%
2330 台積電                Default Target = +20%
```

## 46.1 Security Strategy 與 Buy Lot Strategy 分離

```text
Security Strategy
└─ default_target_return_pct

Buy Lot
└─ target_return_pct
```

建立新的 Buy Lot 時，自動複製當下股票預設值；建立完成後，Buy Lot 的 Target 成為該 Lot 自己的歷史策略設定。

## 46.2 修改股票預設策略不得回溯修改既有 Lot

例如 2025 年 006208 預設 +10%，LOT-001 建立時保存 +10%；2026 年將預設改為 +15% 後，LOT-001 仍維持 +10%，只有之後新建立的 Lot 使用 +15%。

## 46.3 Buy Lot 可個別覆寫 Target

新增 Buy Lot 時，系統帶入股票預設 Target，但使用者可修改。例如 Security Default = +15%，LOT-023 可設定為 +12%。之後該 Lot 的策略機會、目標價格、Near Target 與 Sell Simulation 都使用 +12%。

## 46.4 Target Price

```text
Target Price = Buy Price × (1 + Target Return %)
```

## 46.5 Distance to Target

每個 Lot 顯示：

- Current Return %
- Target Return %
- Target Price
- Distance to Target Price
- Distance to Target %

## 46.6 Near Target

每檔股票可設定 Near-Target Alert Range。若距 Target Price 小於設定範圍則標記 `NEAR TARGET`；達到或超過則標記 `TARGET REACHED`。

## 46.7 Strategy Action 狀態

```text
WAIT
NEAR TARGET
TARGET REACHED
PARTIAL RECOVERY
PRINCIPAL RECOVERED
FULL COST RECOVERED
FREE SHARES
CLOSED
```

Target 判定使用該 Buy Lot 自己的 `target_return_pct`。

---

# 47. 股票策略設定資料結構

新增或擴充：

```text
security_strategies
```

至少包含：

- security_id
- default_target_return_pct
- near_target_alert_pct
- default_recovery_mode
- include_dividend_in_recovery
- default_funding_preference
- reminder_enabled
- updated_at
- note

Buy Lot 保存自己的：

```text
target_return_pct
recovery_mode
strategy_created_from_security_default
```

股票策略修改需寫入 Audit Log。

---

# 48. Strategy Opportunity 計算

策略機會頁不可使用單一全域 Target。每一列依自己的 Buy Lot Target 計算，可依 TARGET REACHED、NEAR TARGET、距離 Target 最近、股票、Broker、Funding、Lot Status 篩選與排序。


---

# 49. Strategy Unit／固定金額 Buy Lot 策略

目前核心購買策略以固定金額作為一個獨立 Buy Lot 單位。

預設：

```text
Default Buy Budget = NT$10,000
```

原則：

- 每次 Buy Lot 的股票成交金額原則上不超過 NT$10,000。
- 因台灣股票以整數股交易，實際投入通常略低於 NT$10,000。
- 每個 Buy Lot 都是獨立策略單位。
- 後續本金回收也以該 Buy Lot 為單位，不使用 FIFO。
- 正常情況下一筆 Sell 對應一個 Buy Lot，不需要跨多個 Lot 自動分配。

例如：

```text
Current Price = 51.05
Budget        = 10,000

Suggested Shares = 195
Estimated Stock Amount = 9,954.75
```

系統可在新增 Buy Lot 時依 Budget 與價格建議最大整數股數，但使用者仍可修改。

未來資料模型可允許：

- 全域 Default Buy Budget
- 個別股票覆寫 Default Buy Budget

---

# 50. Recovery Tolerance／本金回收容許差額

由於台灣股票目前以整數股交易，本金回收不可能保證與原始投入完全相同。

例如：

```text
Original Capital       9,987
Actual Cash Recovered  9,954
Shortfall                 33
Accounting Recovery    99.67%
```

如果為了補回 33 元必須再多賣 1 股，可能反而犧牲原本希望保留下來的股票。

因此系統新增 `Recovery Tolerance`。

可支援：

```text
Recovery Tolerance Amount
Recovery Tolerance %
```

例如：

```text
Tolerance Amount = NT$100
```

若：

```text
Unrecovered Amount <= Tolerance
```

則帳務上仍保留真實差額，但策略狀態可判定為：

```text
COMPLETED_WITH_TOLERANCE
```

## 50.1 帳務結果與策略結果分離

不得因策略判定完成而修改實際現金流。

必須保存：

```text
Original Capital
Actual Cash Recovered
Accounting Recovery %
Unrecovered Amount
Recovery Rounding Difference
```

另外保存／計算：

```text
Strategy Recovery Status
```

例如：

```text
Original Capital        9,987
Actual Cash Recovered   9,954
Unrecovered Amount         33
Accounting Recovery     99.67%

Strategy Recovery:
COMPLETED_WITH_TOLERANCE
```

---

# 51. Recovery Optimization／整數股回本最佳化

回本模擬器不可只計算「第一個使回收金額大於等於本金的股數」。

應比較合理的整數股 Sell 方案。

至少支援三種模式：

```text
KEEP_MAX_SHARES
FULL_PRINCIPAL_RECOVERY
CLOSEST_TO_PRINCIPAL
```

## 51.1 KEEP_MAX_SHARES

預設推薦模式。

規則：

> 在 Recovery Tolerance 允許範圍內，選擇最少 Sell Shares，也就是留下最多股票。

例如：

```text
Original Capital = 9,987
Tolerance        = 100

Sell 45 shares
Net Cash         = 9,954
Difference       = -33
Remaining        = 6
Eligible         = YES

Sell 46 shares
Net Cash         = 10,175
Difference       = +188
Remaining        = 5
```

預設推薦：

```text
Sell 45 shares
```

因為 -33 在容許範圍內，且可多留下 1 股。

## 51.2 FULL_PRINCIPAL_RECOVERY

要求：

```text
Net Cash Recovered >= Recovery Target
```

即使需要多賣 1 股也必須完整達到本金回收。

## 51.3 CLOSEST_TO_PRINCIPAL

比較整數股方案，選擇：

```text
abs(Net Cash Recovered - Recovery Target)
```

最小者。

---

# 52. Recovery Rounding Difference

新增指標：

```text
Recovery Rounding Difference
= Actual Cash Recovered - Recovery Target
```

例如：

```text
Original Capital       9,987
Cash Recovered         9,954
Rounding Difference      -33
```

或：

```text
Original Capital       9,952
Cash Recovered        10,021
Rounding Difference      +69
```

Dashboard / Analysis 可統計所有已完成回本 Lot：

- Positive Recovery Difference
- Negative Recovery Difference
- Net Recovery Difference
- Average Absolute Recovery Difference

此數值不得與股票獲利、Cash Surplus 或貸款利息混為同一概念。

---

# 53. 截圖匯入與 Sell Lot 自動建議的策略調整

券商 App 截圖可以包含多筆交易。

系統流程：

```text
Screenshot
→ OCR / Image Parsing
→ Multiple Import Drafts
→ Field Validation
→ BUY / SELL 分流
→ User Confirmation
→ Database Commit
```

所有辨識結果先進入 Draft，不直接寫入正式資料庫。

## 53.1 BUY

BUY Draft 建立新的 Buy Lot，並帶入：

- Broker
- Funding 預設
- Security Default Target
- Strategy Unit / Buy Budget

使用者確認後才建立正式 Buy Lot。

## 53.2 SELL

由於每個 Buy Lot 約為 NT$10,000 的獨立策略單位，正常 Sell 也以單一 Buy Lot 回收本金，因此 V1 不需要預設 Multi-Lot Allocation。

系統對同股票 Active Lots 計算候選 Lot，預設：

```text
Highest Profit First
```

也就是優先預選目前預估獲利率最高、且剩餘股數足以對應此次 Sell 的 Buy Lot。

最後仍由使用者人工確認或改選。

建議顯示推薦理由：

```text
推薦 LOT-005

1. 目前候選 Lot 中預估獲利率最高
2. 剩餘股數足以對應本次 Sell
3. 本次 Sell 後預計進入本金回收完成狀態
```

## 53.3 Duplicate Detection

截圖匯入必須檢查可能重複交易，可參考：

- Broker
- Stock
- BUY / SELL
- Trade Date
- Trade Time（若有）
- Shares
- Price
- Amount
- Execution / Order ID（若有）

疑似重複時不得自動再次匯入，必須要求使用者確認。


---

# 54. 使用者介面語言

本程式正式 GUI 使用 **繁體中文**。

所有一般使用者可見內容均以中文顯示，包括：

- 選單
- 頁面名稱
- 欄位名稱
- 按鈕
- 狀態
- 提示
- 錯誤訊息
- 圖表
- 對帳結果
- 匯入確認
- 報表標題

程式內部可使用英文資料庫欄位、Python 變數與 Enum，以利維護，但必須透過 GUI 顯示層轉換為繁體中文，不直接暴露英文技術識別名稱。

例如：

```text
FREE_SHARES              → 已回本持股
TARGET_REACHED           → 已達目標
NEAR_TARGET              → 接近目標
MATCHED                  → 對帳一致
MISMATCH                 → 對帳不一致
COMPLETED_WITH_TOLERANCE → 容許差額內完成回本
```


---

# 55. GUI 操作架構更新

正式 GUI 採：

```text
單一 Master Table
+ 上方工具列
+ 彈出式輸入 / 分析視窗
```

不以大量分頁作為主要操作方式。

主要資料瀏覽維持在 Master Table。

---

# 56. 多圖 OCR 匯入

系統必須支援一次選取多個券商 App 截圖。

至少支援：

- PNG
- JPG
- JPEG
- 多檔案選取
- Drag & Drop
- 一張圖片包含多筆紀錄
- 多張圖片批次辨識

OCR 類型至少包括：

```text
交易截圖
股利截圖
```

---

# 57. OCR 不直接寫入正式資料庫

OCR 的責任：

```text
圖片辨識
→ 自動擷取欄位
→ 建立 Draft
→ 預填正式人工輸入表單
```

所有 OCR 匯入資料最後都必須通過：

```text
人工補完
資料驗證
使用者確認
```

才可以寫入正式 SQLite。

---

# 58. OCR 與人工輸入共用同一套表單

不可建立一套與手動輸入不同的 OCR 專用正式資料模型。

例如：

```text
新增買入表單
```

同時支援：

- 手動開啟：空白 / 預設欄位
- OCR 開啟：OCR 可辨識欄位已預填

新增賣出與新增股利同樣遵守此原則。

---

# 59. 多筆 OCR Draft

一張或多張截圖辨識後，可產生多筆 Draft。

Draft 必須保存：

- 來源圖片
- 圖片檔名
- 辨識類型
- 擷取欄位
- OCR 信心資訊（若可取得）
- 是否已人工確認
- 是否疑似重複
- 是否已正式匯入

Draft 不等於正式交易。

---

# 60. 批次共同欄位

多圖 OCR 工作台應允許設定本次共同預設，例如：

- 券商
- Funding
- Loan Account

提供：

```text
套用到所有空白欄位
```

不可覆蓋人工已修改資料。

---

# 61. OCR SELL Lot 建議

SELL 截圖辨識後，系統自動搜尋同股票 Active Buy Lots。

預設建議：

```text
目前獲利率最高且剩餘股數足夠的 Buy Lot
```

但正式寫入前必須由使用者確認或改選。

---

# 62. OCR 股利匯入

股利截圖可自動擷取畫面存在的資料，例如：

- 股票
- 入帳日期
- 基準股數
- 每股股利
- 稅前金額
- 稅費
- 實收金額

截圖中不存在的必要資料：

- 股利類型
- 券商
- 基準日
- 其他欄位

由預設值、資料庫推導或人工補完。

所有股利 OCR Draft 最後進入正式股利輸入表單人工確認。

---

# 63. OCR 資料驗證與重複檢查

正式提交前必須做：

- 必填欄位檢查
- 金額合理性檢查
- SELL 股數檢查
- Sell Lot 關聯檢查
- 股利乘積合理性檢查
- 可能重複紀錄檢查

疑似重複不得靜默加入。


---

# 64. 券商下單／成交編號與硬性防重複機制

每一筆券商買入或賣出交易應盡可能保存券商提供的「下單編號／委託編號／成交編號」。

由於不同券商的編號規則可能不同，系統資料結構至少保留：

- broker_account_id
- broker_order_id
- broker_execution_id（若券商另有成交編號）
- trade_date
- transaction_type
- source

其中：

```text
broker_order_id
```

為主要防重複欄位。

## 64.1 唯一性原則

同一券商帳戶內，同一個有效的券商下單／成交識別編號不得重複寫入正式資料庫。

建議資料庫建立 Unique Constraint，例如概念上：

```text
UNIQUE(
    broker_account_id,
    broker_order_id
)
```

若券商的下單編號可能每日重新編號，則唯一鍵可依券商規則改為：

```text
UNIQUE(
    broker_account_id,
    trade_date,
    broker_order_id
)
```

實際採用哪一種模式應由券商設定決定。

## 64.2 資料庫硬性阻擋

即使 GUI 或 OCR 前端漏掉重複檢查，SQLite 寫入層仍必須阻擋重複交易。

不得只依賴：

- 股票
- 日期
- 股數
- 價格
- 金額

做唯一判定。

券商編號存在時，應優先以券商編號作為最高可信度的 Duplicate Key。

## 64.3 OCR 匯入

若券商截圖中可以辨識：

```text
委託編號
下單編號
成交編號
```

OCR 應自動填入正式買入／賣出表單。

建立 Draft 時立即查詢正式資料庫。

若已存在相同券商 + 有效編號：

```text
重複交易
```

該 Draft 必須：

- 標示紅色
- 禁止正式提交
- 顯示既有資料
- 允許使用者取消／忽略此 Draft
- 不提供一般「仍然匯入」繞過 Unique Constraint

## 64.4 手動輸入

手動新增買入／賣出表單也包含：

```text
券商下單編號
券商成交編號（如有）
```

在離開欄位或提交時即時檢查。

若重複：

```text
此券商下單編號已存在
```

並顯示既有交易摘要。

## 64.5 券商編號缺失

若某些歷史資料或截圖沒有券商編號：

- 仍允許建立交易
- 標記 `券商編號未提供`
- 使用第二層模糊 Duplicate Detection

第二層可比較：

- 券商
- 股票
- 買／賣
- 日期
- 股數
- 價格
- 成交金額
- 成交時間（若有）

此時屬於「疑似重複」，由使用者確認；但有券商編號時則採硬性唯一規則。

## 64.6 訂單與多筆成交的預留

若未來遇到一個券商下單編號拆成多筆成交，不可單純將 `broker_order_id` 當成每筆 execution 的唯一鍵。

資料模型預留：

```text
broker_order_id
broker_execution_id
```

若券商提供 execution ID，正式唯一鍵可使用：

```text
broker_account_id
+ broker_order_id
+ broker_execution_id
```

若券商畫面只提供單一成交紀錄編號，則以該券商實際可取得的最細識別碼為準。

---

# 65. 更新後 Duplicate Detection 優先順序

資料驗證依以下優先級：

```text
Level 1：券商唯一識別碼
        ↓
完全相同 → 硬性禁止加入

Level 2：交易欄位完全相似
        ↓
疑似重複 → 人工確認

Level 3：一般資料合理性檢查
```

Level 1 優先於所有 OCR 相似度與欄位比對。


---

# 66. 模組化程式架構

整個程式必須採模組化設計，避免 GUI、資料庫、計算、OCR、股價與匯入匯出全部集中在單一大型 Python 檔案。

建議模組：

```text
stock_manager/
│
├─ main.py
├─ app/
│   ├─ main_window.py
│   ├─ toolbar.py
│   └─ master_table.py
├─ dialogs/
│   ├─ buy_dialog.py
│   ├─ sell_dialog.py
│   ├─ dividend_dialog.py
│   ├─ corporate_action_dialog.py
│   ├─ reconciliation_dialog.py
│   └─ recovery_simulator_dialog.py
├─ database/
│   ├─ connection.py
│   ├─ schema.py
│   ├─ migrations.py
│   └─ repositories/
├─ services/
│   ├─ lot_service.py
│   ├─ recovery_service.py
│   ├─ portfolio_service.py
│   ├─ loan_service.py
│   ├─ dividend_service.py
│   ├─ reconciliation_service.py
│   └─ duplicate_service.py
├─ pricing/
│   ├─ price_service.py
│   └─ providers/
├─ ocr/
│   ├─ image_importer.py
│   ├─ trade_parser.py
│   ├─ dividend_parser.py
│   └─ ocr_validation.py
├─ import_export/
│   ├─ excel_import.py
│   ├─ excel_export.py
│   ├─ csv_export.py
│   └─ backup_service.py
├─ analytics/
│   ├─ performance.py
│   ├─ cashflow.py
│   ├─ dividend_analysis.py
│   └─ charts.py
└─ utils/
    ├─ validators.py
    ├─ formatting.py
    └─ logging.py
```

核心原則：

- GUI 只負責顯示與輸入。
- 商業邏輯集中在 `services/`。
- SQLite 存取集中在 `database/`。
- OCR 集中在 `ocr/`。
- 股價來源集中在 `pricing/`。
- Excel / CSV / Backup 集中在 `import_export/`。
- 分析與圖表集中在 `analytics/`。
- 模組間使用明確介面，避免互相直接修改資料。

---

# 67. Excel 匯入 / 匯出

V1 必須支援 Excel 匯入與匯出。

## 67.1 Excel 匯入

至少支援：

1. 既有 Excel 歷史資料移轉
2. 本程式格式 Excel 的重新匯入 / 還原

匯入前必須：

- 預覽資料
- 欄位 Mapping
- 必填欄位驗證
- 券商下單編號防重複
- 疑似重複交易檢查
- 人工確認

## 67.2 完整 Excel 匯出

完整備份 Excel 不只匯出主畫面可見欄位。

建議 Workbook 至少包含：

```text
交易總覽
買入批次
賣出紀錄
股利紀錄
公司行動
貸款
貸款交易
股票資料
股票策略
股價紀錄
券商帳戶
對帳紀錄
OCR匯入紀錄
設定摘要
```

Excel 主要用途：

- 人類可讀備份
- 人工檢查
- 歷史查詢
- 災難復原輔助

SQLite 仍然是正式 Master Database。

---

# 68. 完整備份內容

每次「完整備份」至少產生：

```text
portfolio.db
portfolio.xlsx
backup_manifest.json
```

其中：

- `portfolio.db`：完整 SQLite 資料庫快照
- `portfolio.xlsx`：完整人類可讀 Excel 備份
- `backup_manifest.json`：備份時間、程式版本、資料庫版本、檔案雜湊、備份來源等資訊

建議資料夾格式：

```text
Backup/
└─ 2026-08-09_073500/
    ├─ portfolio.db
    ├─ portfolio.xlsx
    └─ backup_manifest.json
```

---

# 69. 啟動程式自動備份

程式每次啟動時，在載入正式資料庫後、進入主要操作前，自動執行一次備份。

流程：

```text
啟動程式
↓
開啟 / 驗證 SQLite
↓
建立一致性資料庫快照
↓
產生完整 Excel
↓
產生 Manifest
↓
寫入所有啟用的備份位置
↓
記錄每個位置的成功 / 失敗
↓
進入主畫面
```

自動備份失敗不得造成資料庫損壞。

如果至少一個主要備份位置成功，程式可正常開啟，但應提示其他失敗位置。

如果所有備份位置均失敗，可依設定：

```text
只警告後繼續
或
要求使用者確認後才繼續
```

---

# 70. 多位置備份

系統必須支援同時設定多個 Backup Target。

例如：

```text
位置 1：
D:\StockManager\Backup
啟用：是

位置 2：
G:\我的雲端硬碟\StockManager_Backup
啟用：是

位置 3：
E:\StockBackup
啟用：是
```

每次完整備份時，同一份 Backup Package 必須複製到所有啟用位置。

每個 Backup Target 分別保存：

- Target ID
- 顯示名稱
- 路徑
- 類型
- 是否啟用
- 是否主要位置
- 最後成功備份時間
- 最後失敗時間
- 最後錯誤訊息
- 保留規則

---

# 71. Google Drive 備份

V1 優先支援 Google Drive for desktop 的本機同步資料夾。

例如：

```text
G:\我的雲端硬碟\StockManager_Backup
```

程式把它視為一般 Backup Target。

優點：

- 不需要在程式內保存 Google OAuth Token
- 不需要自行處理 Drive API
- Google Drive Desktop 自動負責雲端同步
- 本機仍可直接檢查備份檔

設定畫面需允許使用者選取 Google Drive 同步資料夾。

未來可擴充直接 Google Drive API：

```text
Backup Target Type:
LOCAL_FOLDER
GOOGLE_DRIVE_SYNC_FOLDER
GOOGLE_DRIVE_API
```

V1 不必強制實作直接 Google Drive API。

---

# 72. 備份觸發條件

至少支援：

- 程式啟動時自動備份
- 手動「立即完整備份」
- 程式關閉時自動備份（可設定）
- 重大操作前備份（可設定）
- 每日首次啟動才備份（可選）
- 每次啟動都備份（可選）

重大操作例如：

- 大量 Excel 匯入
- 批次 OCR 正式提交
- 資料庫 Migration
- 大量刪除 / 修正

---

# 73. 備份保留策略

每個 Backup Target 可個別設定：

```text
保留最近 N 份
保留最近 N 天
每日最多保留 1 份
每週保留 1 份
每月保留 1 份
永不自動刪除
```

建議預設：

```text
每日首次啟動完整備份
保留最近 30 日
每月再保留 1 份長期備份
```

清除舊備份前需先確認該 Target 目前存在至少一份有效新備份。

---

# 74. 備份完整性驗證

備份不能只做檔案 Copy。

至少驗證：

- SQLite 備份檔可開啟
- SQLite `PRAGMA integrity_check` 通過
- Excel 成功建立且可讀
- Manifest 已產生
- 目的地檔案存在
- 可選：SHA-256 Hash 比對

每個備份位置最後產生：

```text
成功
部分成功
失敗
```

---

# 75. 備份歷史

資料庫保存 Backup History：

```text
backup_runs
backup_target_results
```

至少包含：

- Backup ID
- Trigger
- 開始時間
- 完成時間
- DB Snapshot 狀態
- Excel Export 狀態
- 每個 Target 結果
- 檔案路徑
- Hash
- Error Message

Dashboard / 狀態列可顯示：

```text
最後成功完整備份：
2026/08/09 07:35

3 / 3 備份位置成功
```

---

# 76. 資料還原

系統至少支援：

## SQLite 完整還原

選擇備份的 `portfolio.db`。

還原前：

1. 自動備份目前資料
2. 驗證選取備份
3. 顯示備份日期與版本
4. 使用者確認
5. 進行 Restore
6. 重新啟動資料層

## Excel 還原 / 匯入

Excel 不直接覆寫 SQLite。

必須經：

```text
讀取
→ 驗證
→ Duplicate Check
→ 預覽
→ 人工確認
→ 寫入
```

---

# 77. 備份失敗安全原則

若某個外接硬碟、NAS 或 Google Drive 同步資料夾目前不存在：

- 不刪除其他成功備份
- 不破壞正式 SQLite
- 記錄該 Target 失敗
- 主畫面顯示警告
- 下次啟動重新嘗試

不得因其中一個備份位置離線而造成整個程式無法使用，除非使用者設定為「強制備份成功才能進入」。


---

# 78. KPI 與分析圖表規格

分析功能的目的不是只呈現傳統「總報酬率」，而是回答本策略最核心的問題：

```text
投入多少資金
→ 已回收多少現金
→ 還有多少本金暴露在市場
→ 已經留下多少已回本持股
→ 為此支付多少貸款與交易成本
→ 在不同市場環境下，策略目前運作到什麼程度
```

## 78.1 核心 KPI 卡片

分析視窗最上方至少顯示：

- 股票總市值
- 原始累積投入
- 累積回收現金
- 尚未回收本金
- 已回本持股市值
- 累積現金股利
- 累積貸款利息
- 目前貸款餘額
- 累積 Cash Surplus / 超額回收現金
- 已回本 Lot 數
- 已回本 Lot 比例
- 最後完整對帳日期

其中優先 KPI：

```text
已回本持股市值
尚未回收本金
目前貸款餘額
```

---

# 79. 資產形成 Waterfall

圖表目的：

> 顯示資金如何從原始投入轉換成已回收現金、成本與剩餘已回本股票。

建議包含：

- 原始累積投入
- 累積賣股回收
- Recovery Difference
- 累積交易成本
- 累積貸款利息
- 累積現金股利
- Cash Surplus
- 已回本持股市值

此圖應明確區分：

```text
現金流
持股市值
成本
```

避免將不同性質數字誤加成單一會計值。

---

# 80. 已回本持股成長曲線

時間序列圖。

可切換：

```text
已回本持股總市值
已回本股數
累積完成回本 Lot 數
```

用來觀察長期策略是否持續累積不再占用原始本金的股票資產。

---

# 81. 貸款餘額 vs 已回本持股市值

雙指標時間趨勢圖。

至少比較：

```text
貸款餘額
已回本持股市值
```

目的：

- 觀察貸款餘額是否下降
- 觀察已回本資產是否增加
- 辨識策略重要里程碑

例如：

```text
已回本持股市值 > 尚未償還貸款
```

可作為策略里程碑顯示，但不可直接視為淨資產或獲利等價。

---

# 82. 尚未回收本金分布

建議使用 Bar Chart。

可以切換維度：

```text
依股票
依券商
依貸款帳戶
依資金來源
```

例如：

```text
006208    85,000
0056      40,000
00878     30,000
2330      20,000
```

目的：

> 快速找出目前 Capital at Risk 集中在哪些股票與資金來源。

---

# 83. Buy Lot 回收狀態分布

至少統計：

- 未達目標
- 接近目標
- 已達目標待處理
- 部分回本
- 容許差額內完成回本
- 完整成本回收
- 已回本持股
- Closed

可用 Bar / Donut。

分析圖可作為 Master Table Filter 的入口。

例如點擊：

```text
已達目標待處理
```

即可切回 Master Table 並只顯示該類 Lot。

---

# 84. 月度現金流圖

按月份呈現：

- 買入支出
- 賣出淨回收
- 現金股利
- 貸款本金還款
- 貸款利息
- 手續費與交易稅
- 月度淨現金流

可另顯示：

```text
累積淨現金流
```

目的：

- 了解每月實際現金流出 / 流入
- 觀察策略是否逐步產生自身現金流
- 觀察貸款與股票回收之間關係

---

# 85. 股利分析

至少包含兩種圖：

## 每月 / 每年股利收入

時間序列呈現：

```text
現金股利收入
```

## 累積股利曲線

顯示自開始記錄以來累積收到的現金股利。

並可切換：

```text
全部持股股利
已回本持股產生的股利
尚未回本持股產生的股利
```

---

# 86. 股利來源結構

依股票統計股利貢獻。

若股票種類少，可用 Pie / Donut。

若股票種類較多，改用 Bar Chart。

至少可回答：

> 哪些股票對現金股利貢獻最大？

可切換：

```text
全部股利
已回本持股產生股利
```

---

# 87. 貸款成本分析

至少包含：

## 每月貸款利息

顯示各月份實際支付或累積的貸款利息。

## 累積貸款利息

時間序列顯示融資成本累積速度。

## 貸款成本 vs 策略資產

可比較：

```text
累積貸款利息
已回本持股市值
累積股利
Cash Surplus
```

目的為理解槓桿成本與策略產出之間的關係。

不可把此圖直接解讀成因果關係。

---

# 88. Recovery Difference／回本差額分析

每一完成回本 Lot 計算：

```text
Recovery Difference
= Actual Cash Recovered - Recovery Target
```

至少顯示：

- 累積 Positive Difference
- 累積 Negative Difference
- Net Recovery Difference
- Average Recovery Difference
- Average Absolute Recovery Difference

圖表可使用：

- Histogram
- 分組 Bar
- 股票別 Recovery Difference

此分析用來驗證目前的 Recovery Tolerance 是否合理。

---

# 89. 個股策略成果比較

每檔股票至少比較：

- Buy Lot 數
- 已完成回本 Lot 數
- 回本完成率
- 尚未回收本金
- 已回本持股股數
- 已回本持股市值
- 累積股利
- 累積貸款利息
- 累積 Cash Surplus

此分析的目標不是單純比較股價報酬，而是比較：

> 哪些股票實際替策略累積最多已回本資產。

---

# 90. 回本天數分析

不將 Target % 單獨視為回本速度的主要原因。

至少分析：

- 已完成回本 Lot 的持有天數分布
- Median Recovery Days
- Average Recovery Days
- 股票別回本天數
- 年度別回本天數
- 現金 Lot vs 貸款 Lot

目的：

> 描述策略實際需要多久完成本金回收。

---

# 91. 尚未回本 Lot 年齡分布

針對目前仍未完成回本的 Buy Lots。

建議分組：

```text
< 30 天
30–90 天
90–180 天
180–365 天
> 1 年
```

可額外顯示每組：

- Lot 數量
- 尚未回收本金
- 貸款資金金額
- 累積利息

此圖特別用來找出：

> 長時間占用貸款資金、持續產生利息的 Lot。

---

# 92. 回本完成率

回本完成率不可只看全部歷史 Lot 的單一比例。

建議按 Lot Age Cohort 計算，例如：

```text
買入滿 30 天的 Lot 中，完成回本比例
買入滿 90 天的 Lot 中，完成回本比例
買入滿 180 天的 Lot 中，完成回本比例
買入滿 365 天的 Lot 中，完成回本比例
```

也可依股票比較。

---

# 93. 市場環境與回本表現

不建立「Target % 效率分析」作為核心 KPI。

原因：

> 回本天數同時受大盤環境、個股走勢、波動度、買入時點、配息與目標設定影響，不能將回本天數直接歸因於 Target %。

因此改為保留 Benchmark Data。

台股可預設：

```text
TAIEX / 加權指數
```

或由使用者設定其他 Benchmark。

每個 Buy Lot 可計算：

```text
Buy Date → Recovery Date
同期 Benchmark Return
同期個股 Return
Recovery Days
```

---

# 94. 同期大盤報酬 vs 回本時間

Scatter Plot：

```text
X：Buy 到 Recovery 期間的 Benchmark Return %
Y：Recovery Days
```

目的：

> 描述市場環境與回本速度的關聯性。

不可直接宣稱市場報酬是回本速度的唯一原因。

可依：

- 股票
- 年度
- Funding
- Benchmark

篩選。

---

# 95. 市場階段策略表現

可按：

- 年度
- 使用者自訂期間
- Benchmark 上漲 / 下跌區間

統計：

- 新增 Lot 數
- 完成回本 Lot 數
- 回本完成率
- 尚未回收本金變化
- 已回本持股新增市值
- 貸款利息

第一版不必強制將市場硬分類成「牛市／熊市」。

優先使用客觀 Benchmark Return 與使用者自訂期間。

---

# 96. 分析頁最終分類

分析視窗建議分類為：

```text
策略總覽
├─ KPI Cards
├─ 資產形成 Waterfall
├─ 已回本持股成長
└─ 貸款餘額 vs 已回本資產

本金回收
├─ 尚未回收本金分布
├─ Lot 回收狀態
├─ Recovery Difference
├─ 回本天數
├─ 未回本 Lot 年齡
└─ 回本完成率

現金流
├─ 月度現金流
└─ 累積現金回收

股利
├─ 每月 / 每年股利
├─ 累積股利
└─ 股利來源結構

貸款
├─ 貸款餘額
├─ 每月利息
└─ 貸款成本 vs 策略資產

個股
└─ 個股策略成果比較

市場環境
├─ Benchmark 同期報酬
├─ 大盤報酬 vs 回本時間
└─ 市場階段策略表現
```

明確取消將「Target % 效率」作為核心策略 KPI。
