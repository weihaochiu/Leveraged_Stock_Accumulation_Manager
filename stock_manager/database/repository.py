from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from stock_manager.domain import calculate_lot_metrics, dec, money
from stock_manager.pricing.models import MarketQuote, SecurityUpdateResult
from .connection import Database


def _dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row else None


class DuplicateTradeError(ValueError):
    pass


class PortfolioRepository:
    def __init__(self, db: Database):
        self.db = db

    def settings(self) -> dict[str, str]:
        with self.db.connect() as conn:
            return {r["key"]: r["value"] for r in conn.execute("SELECT key,value FROM settings")}

    def set_setting(self, key: str, value: object) -> None:
        with self.db.transaction() as conn:
            old = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
            conn.execute("INSERT INTO settings(key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP", (key, str(value)))
            if key == "price_finmind_token":
                self._audit(conn, "修改", "設定", key, {"value": "***"} if old else None, {"value": "***"})
            else:
                self._audit(conn, "修改", "設定", key, _dict(old), {"value": str(value)})

    def list_securities(self) -> list[dict]:
        with self.db.connect() as conn:
            return [dict(r) for r in conn.execute("""
                SELECT s.*, ss.default_target_return_pct, ss.near_target_alert_pct,
                       ss.default_recovery_mode, ss.include_dividend_in_recovery,
                       ss.default_funding_preference, ss.default_buy_budget,
                       ss.recovery_tolerance_amount, ss.recovery_tolerance_pct
                FROM securities s JOIN security_strategies ss ON ss.security_id=s.id
                WHERE s.active=1 ORDER BY s.symbol
            """)]

    def ensure_security(self, symbol: str, name: str, market: str = "TW") -> int:
        symbol = symbol.strip().upper()
        if not symbol or not name.strip():
            raise ValueError("股票代號與名稱不可空白")
        settings = self.settings()
        with self.db.transaction() as conn:
            conn.execute("INSERT OR IGNORE INTO securities(symbol,name,market) VALUES (?,?,?)", (symbol, name.strip(), market))
            row = conn.execute("SELECT id FROM securities WHERE symbol=? AND market=?", (symbol, market)).fetchone()
            security_id = int(row[0])
            conn.execute("""
                INSERT OR IGNORE INTO security_strategies(
                    security_id,default_target_return_pct,near_target_alert_pct,
                    default_buy_budget,recovery_tolerance_amount
                ) VALUES (?,?,?,?,?)
            """, (security_id, float(settings["default_target_return_pct"]), float(settings["near_target_alert_pct"]), float(settings["default_buy_budget"]), float(settings["recovery_tolerance_amount"])))
            return security_id

    def update_security_market(self, security_id: int, market: str) -> None:
        if market not in {"TWSE", "TPEx", "TW"}:
            raise ValueError("市場必須為 TWSE、TPEx 或待辨識 TW")
        with self.db.transaction() as conn:
            conn.execute(
                "UPDATE securities SET market=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (market, security_id),
            )

    def list_held_securities(self, security_ids: list[int] | None = None) -> list[dict]:
        """僅回傳目前淨持股大於零的股票，每檔只出現一次。"""
        params: list[object] = []
        id_filter = ""
        if security_ids:
            placeholders = ",".join("?" for _ in security_ids)
            id_filter = f" AND s.id IN ({placeholders})"
            params.extend(security_ids)
        with self.db.connect() as conn:
            rows = conn.execute(
                f"""
                SELECT s.*,
                    COALESCE(SUM(b.original_shares),0)
                    + COALESCE((SELECT SUM(ca.share_change) FROM corporate_actions ca
                                JOIN buy_lots cb ON cb.id=ca.lot_id
                                WHERE ca.security_id=s.id AND cb.archived=0),0)
                    - COALESCE((SELECT SUM(st.shares) FROM sell_transactions st
                                JOIN buy_lots sb ON sb.id=st.lot_id
                                WHERE st.security_id=s.id AND sb.archived=0),0) AS held_shares
                FROM securities s
                JOIN buy_lots b ON b.security_id=s.id AND b.archived=0
                WHERE s.active=1 {id_filter}
                GROUP BY s.id
                HAVING held_shares > 0
                ORDER BY s.symbol
                """,
                params,
            )
            return [dict(row) for row in rows]

    def update_security_strategy(self, security_id: int, values: dict) -> None:
        allowed = {
            "default_target_return_pct", "near_target_alert_pct", "default_recovery_mode",
            "include_dividend_in_recovery", "default_funding_preference", "default_buy_budget",
            "recovery_tolerance_amount", "recovery_tolerance_pct", "reminder_enabled", "note",
        }
        data = {k: v for k, v in values.items() if k in allowed}
        if not data:
            return
        with self.db.transaction() as conn:
            old = _dict(conn.execute("SELECT * FROM security_strategies WHERE security_id=?", (security_id,)).fetchone())
            sql = ",".join(f"{k}=?" for k in data)
            conn.execute(f"UPDATE security_strategies SET {sql}, updated_at=CURRENT_TIMESTAMP WHERE security_id=?", (*data.values(), security_id))
            self._audit(conn, "修改", "股票策略", str(security_id), old, data)

    def list_brokers(self) -> list[dict]:
        with self.db.connect() as conn:
            return [dict(r) for r in conn.execute("SELECT * FROM broker_accounts ORDER BY name")]

    def add_broker(self, name: str, account_label: str = "", unique_scope: str = "ACCOUNT") -> str:
        with self.db.transaction() as conn:
            broker_id = self.db.next_id(conn, "broker", "BROKER")
            conn.execute("INSERT INTO broker_accounts(id,name,account_label,unique_scope) VALUES (?,?,?,?)", (broker_id, name.strip(), account_label.strip(), unique_scope))
            self._audit(conn, "新增", "券商帳戶", broker_id, None, {"name": name})
            return broker_id

    def list_loans(self) -> list[dict]:
        with self.db.connect() as conn:
            rows = conn.execute("""
                SELECT l.*,
                  l.original_principal
                  - COALESCE(SUM(CASE WHEN t.transaction_type='REPAYMENT' THEN t.amount ELSE 0 END),0) AS current_balance,
                  COALESCE(SUM(CASE WHEN t.transaction_type='INTEREST' THEN t.amount ELSE 0 END),0) AS interest_paid
                FROM loans l LEFT JOIN loan_transactions t ON t.loan_id=l.id
                GROUP BY l.id ORDER BY l.borrow_date DESC
            """)
            return [dict(r) for r in rows]

    def add_loan(self, values: dict) -> str:
        if dec(values.get("original_principal")) <= 0:
            raise ValueError("貸款原始本金必須大於 0")
        with self.db.transaction() as conn:
            loan_id = self.db.next_id(conn, "loan", "LOAN")
            conn.execute("""INSERT INTO loans(id,name,institution,borrow_date,original_principal,annual_interest_rate,rate_type,interest_start_date,maturity_date,repayment_method,note)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)""", (
                loan_id, values["name"], values.get("institution", ""), values["borrow_date"], float(dec(values["original_principal"])),
                float(dec(values.get("annual_interest_rate"))), values.get("rate_type", "FIXED"), values.get("interest_start_date"),
                values.get("maturity_date"), values.get("repayment_method", ""), values.get("note", "")))
            self._audit(conn, "新增", "貸款", loan_id, None, values)
            return loan_id

    def add_loan_transaction(self, values: dict) -> str:
        if dec(values.get("amount")) <= 0:
            raise ValueError("金額必須大於 0")
        with self.db.transaction() as conn:
            tx_id = self.db.next_id(conn, "loan_tx", "LTX")
            conn.execute("INSERT INTO loan_transactions(id,loan_id,transaction_date,transaction_type,amount,lot_id,sell_id,note) VALUES (?,?,?,?,?,?,?,?)", (
                tx_id, values["loan_id"], values["transaction_date"], values["transaction_type"], float(dec(values["amount"])), values.get("lot_id"), values.get("sell_id"), values.get("note", "")))
            self._audit(conn, "新增", "貸款交易", tx_id, None, values)
            return tx_id

    def add_buy_lot(self, values: dict) -> str:
        shares, price = int(values.get("original_shares") or 0), dec(values.get("buy_price"))
        if shares <= 0 or price <= 0:
            raise ValueError("買入股數與價格必須大於 0")
        stock_amount = money(values.get("stock_amount") or price * shares)
        original_capital = money(stock_amount + dec(values.get("buy_fee")) + dec(values.get("other_cost")))
        funded = money(dec(values.get("loan_funded")) + dec(values.get("cash_funded")))
        if abs(funded - original_capital) > Decimal("1"):
            raise ValueError("貸款投入與現金投入合計，必須等於原始總投入（容許 1 元四捨五入差額）")
        with self.db.transaction() as conn:
            lot_id = self.db.next_id(conn, "lot", "LOT")
            self._reserve_trade_key(conn, values, "BUY", lot_id)
            columns = (
                "id,security_id,broker_account_id,buy_date,buy_price,original_shares,stock_amount,buy_fee,other_cost,original_capital,"
                "funding_type,loan_id,loan_funded,cash_funded,target_return_pct,recovery_mode,recovery_tolerance_amount,"
                "recovery_tolerance_pct,strategy_created_from_security_default,broker_order_id,broker_execution_id,note"
            )
            conn.execute(f"INSERT INTO buy_lots({columns}) VALUES ({','.join('?' for _ in range(22))})", (
                lot_id, values["security_id"], values.get("broker_account_id"), values["buy_date"], float(price), shares,
                float(stock_amount), float(dec(values.get("buy_fee"))), float(dec(values.get("other_cost"))), float(original_capital),
                values["funding_type"], values.get("loan_id"), float(dec(values.get("loan_funded"))), float(dec(values.get("cash_funded"))),
                float(dec(values.get("target_return_pct"))), values.get("recovery_mode", "PRINCIPAL"),
                float(dec(values.get("recovery_tolerance_amount"))), float(dec(values.get("recovery_tolerance_pct"))),
                int(values.get("strategy_created_from_security_default", 1)), values.get("broker_order_id") or None,
                values.get("broker_execution_id") or None, values.get("note", "")))
            self._audit(conn, "新增", "買進批次", lot_id, None, values)
            return lot_id

    def add_sell(self, values: dict) -> str:
        shares = int(values.get("shares") or 0)
        if shares <= 0 or dec(values.get("sell_price")) <= 0:
            raise ValueError("賣出股數與價格必須大於 0")
        with self.db.transaction() as conn:
            lot = _dict(conn.execute("SELECT * FROM buy_lots WHERE id=?", (values["lot_id"],)).fetchone())
            if not lot:
                raise ValueError("找不到指定的買進批次")
            sold = conn.execute("SELECT COALESCE(SUM(shares),0) FROM sell_transactions WHERE lot_id=?", (values["lot_id"],)).fetchone()[0]
            if shares > int(lot["original_shares"]) - int(sold):
                raise ValueError("賣出股數不可大於該買進批次的剩餘股數")
            if int(values["security_id"]) != int(lot["security_id"]):
                raise ValueError("賣出股票與指定買進批次不一致")
            sell_id = self.db.next_id(conn, "sell", "SELL")
            self._reserve_trade_key(conn, values, "SELL", sell_id)
            conn.execute("""INSERT INTO sell_transactions(
                id,lot_id,security_id,broker_account_id,sell_date,sell_price,shares,gross_amount,commission,tax,other_fee,net_cash,
                repay_loan,loan_repayment_amount,broker_order_id,broker_execution_id,note
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
                sell_id, values["lot_id"], values["security_id"], values.get("broker_account_id"), values["sell_date"],
                float(dec(values["sell_price"])), shares, float(dec(values["gross_amount"])), float(dec(values.get("commission"))),
                float(dec(values.get("tax"))), float(dec(values.get("other_fee"))), float(dec(values["net_cash"])),
                int(bool(values.get("repay_loan"))), float(dec(values.get("loan_repayment_amount"))), values.get("broker_order_id") or None,
                values.get("broker_execution_id") or None, values.get("note", "")))
            if dec(values.get("loan_repayment_amount")) > 0 and lot.get("loan_id"):
                tx_id = self.db.next_id(conn, "loan_tx", "LTX")
                conn.execute("INSERT INTO loan_transactions(id,loan_id,transaction_date,transaction_type,amount,lot_id,sell_id,note) VALUES (?,?,?,?,?,?,?,?)", (
                    tx_id, lot["loan_id"], values["sell_date"], "REPAYMENT", float(dec(values["loan_repayment_amount"])), lot["id"], sell_id, "由賣出交易建立"))
            conn.execute("UPDATE buy_lots SET updated_at=CURRENT_TIMESTAMP WHERE id=?", (lot["id"],))
            self._audit(conn, "新增", "賣出交易", sell_id, None, values)
            return sell_id

    def add_dividend(self, values: dict) -> str:
        with self.db.transaction() as conn:
            dividend_id = self.db.next_id(conn, "dividend", "DIV")
            conn.execute("""INSERT INTO dividends(id,security_id,lot_id,broker_account_id,dividend_type,ex_date,payment_date,base_shares,dividend_per_share,gross_amount,tax,insurance_fee,other_fee,net_amount,include_in_recovery,note)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
                dividend_id, values["security_id"], values.get("lot_id"), values.get("broker_account_id"), values.get("dividend_type", "CASH"),
                values.get("ex_date"), values["payment_date"], float(dec(values.get("base_shares"))), float(dec(values.get("dividend_per_share"))),
                float(dec(values.get("gross_amount"))), float(dec(values.get("tax"))), float(dec(values.get("insurance_fee"))), float(dec(values.get("other_fee"))),
                float(dec(values.get("net_amount"))), int(bool(values.get("include_in_recovery"))), values.get("note", "")))
            self._audit(conn, "新增", "股利", dividend_id, None, values)
            return dividend_id

    def add_corporate_action(self, values: dict) -> str:
        with self.db.transaction() as conn:
            action_id = self.db.next_id(conn, "corporate_action", "CA")
            conn.execute("INSERT INTO corporate_actions(id,security_id,lot_id,action_type,effective_date,share_change,cash_amount,ratio,note) VALUES (?,?,?,?,?,?,?,?,?)", (
                action_id, values["security_id"], values.get("lot_id"), values["action_type"], values["effective_date"],
                float(dec(values.get("share_change"))), float(dec(values.get("cash_amount"))), float(dec(values.get("ratio"))), values.get("note", "")))
            self._audit(conn, "新增", "公司行動", action_id, None, values)
            return action_id

    def add_reconciliation(self, values: dict) -> str:
        with self.db.transaction() as conn:
            rec_id = self.db.next_id(conn, "reconciliation", "REC")
            difference = dec(values["broker_shares"]) - dec(values["system_shares"])
            status = "MATCHED" if difference == 0 else "MISMATCH"
            conn.execute("INSERT INTO reconciliations(id,session_date,security_id,broker_account_id,system_shares,broker_shares,difference,status,note) VALUES (?,?,?,?,?,?,?,?,?)", (
                rec_id, values["session_date"], values["security_id"], values.get("broker_account_id"), float(dec(values["system_shares"])),
                float(dec(values["broker_shares"])), float(difference), status, values.get("note", "")))
            self._audit(conn, "新增", "持股對帳", rec_id, None, {**values, "difference": str(difference), "status": status})
            return rec_id

    def add_ocr_draft(self, source_file: str, draft_type: str, extracted: dict, confidence: dict | None = None, duplicate_status: str = "NOT_CHECKED") -> str:
        with self.db.transaction() as conn:
            draft_id = self.db.next_id(conn, "ocr_draft", "OCR")
            conn.execute("INSERT INTO ocr_drafts(id,source_file,draft_type,extracted_json,confidence_json,duplicate_status) VALUES (?,?,?,?,?,?)", (
                draft_id, source_file, draft_type, json.dumps(extracted, ensure_ascii=False, default=str), json.dumps(confidence or {}, ensure_ascii=False), duplicate_status))
            return draft_id

    def add_price(self, security_id: int, price: object, price_date: str, source: str = "MANUAL") -> None:
        if dec(price) <= 0:
            raise ValueError("股價必須大於 0")
        with self.db.transaction() as conn:
            actual_source = "MANUAL" if source in {"MANUAL", "手動輸入"} else source
            conn.execute("""INSERT INTO price_history(
                    security_id,price,price_date,source,quote_type,fetched_at,is_manual_override
                ) VALUES (?,?,?,?,?,?,?)
                ON CONFLICT(security_id,price_date,source) DO UPDATE SET
                    price=excluded.price,quote_type=excluded.quote_type,fetched_at=excluded.fetched_at,
                    is_manual_override=excluded.is_manual_override,updated_at=CURRENT_TIMESTAMP""",
                (security_id, float(dec(price)), price_date, actual_source, "MANUAL", datetime.now().astimezone().isoformat(timespec="seconds"), 1))
            self._audit(conn, "修改", "股票價格", str(security_id), None, {"price": str(price), "price_date": price_date, "source": actual_source})

    def latest_price(self, security_id: int) -> dict | None:
        with self.db.connect() as conn:
            return _dict(conn.execute(
                """SELECT * FROM price_history WHERE security_id=?
                   ORDER BY price_date DESC,
                     CASE WHEN is_manual_override=1 THEN 3 WHEN source IN ('TWSE','TPEx') THEN 2 ELSE 1 END DESC,
                     updated_at DESC LIMIT 1""",
                (security_id,),
            ).fetchone())

    def save_market_quote(self, security_id: int, quote: MarketQuote) -> None:
        if quote.close <= 0:
            raise ValueError("收盤價必須大於 0")
        with self.db.transaction() as conn:
            conn.execute(
                """INSERT INTO price_history(
                    security_id,price,price_date,source,exchange,open_price,high_price,low_price,
                    volume_shares,turnover_twd,transaction_count,price_change,quote_type,fetched_at,
                    is_manual_override,warning_message
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,0,?)
                ON CONFLICT(security_id,price_date,source) DO UPDATE SET
                    price=excluded.price,exchange=excluded.exchange,open_price=excluded.open_price,
                    high_price=excluded.high_price,low_price=excluded.low_price,
                    volume_shares=excluded.volume_shares,turnover_twd=excluded.turnover_twd,
                    transaction_count=excluded.transaction_count,price_change=excluded.price_change,
                    quote_type=excluded.quote_type,fetched_at=excluded.fetched_at,
                    warning_message=excluded.warning_message,updated_at=CURRENT_TIMESTAMP""",
                (
                    security_id, float(quote.close), quote.trade_date.isoformat(), quote.source,
                    quote.exchange, float(quote.open) if quote.open is not None else None,
                    float(quote.high) if quote.high is not None else None,
                    float(quote.low) if quote.low is not None else None,
                    quote.volume_shares, quote.turnover_twd, quote.transaction_count,
                    float(quote.price_change) if quote.price_change is not None else None,
                    quote.quote_type, quote.fetched_at.isoformat(timespec="seconds"), quote.warning_message,
                ),
            )

    def create_price_update_run(self, trigger_type: str, planned_count: int, started_at: datetime) -> int:
        with self.db.transaction() as conn:
            cursor = conn.execute(
                "INSERT INTO price_update_runs(trigger_type,started_at,planned_count) VALUES (?,?,?)",
                (trigger_type, started_at.isoformat(timespec="seconds"), planned_count),
            )
            return int(cursor.lastrowid)

    def add_price_update_result(self, run_id: int, result: SecurityUpdateResult) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                """INSERT INTO price_update_details(
                    run_id,security_id,status,source,retry_count,trade_date,message
                ) VALUES (?,?,?,?,?,?,?)
                ON CONFLICT(run_id,security_id) DO UPDATE SET
                    status=excluded.status,source=excluded.source,retry_count=excluded.retry_count,
                    trade_date=excluded.trade_date,message=excluded.message,created_at=CURRENT_TIMESTAMP""",
                (run_id, result.security_id, result.status.value, result.source, result.retry_count,
                 result.trade_date.isoformat() if result.trade_date else None, result.message),
            )

    def finish_price_update_run(self, run_id: int, completed_at: datetime, counts: dict[str, int], status: str) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                """UPDATE price_update_runs SET completed_at=?,success_count=?,fallback_success_count=?,
                    failed_count=?,skipped_count=?,status=? WHERE id=?""",
                (completed_at.isoformat(timespec="seconds"), counts["success"], counts["fallback"],
                 counts["failed"], counts["skipped"], status, run_id),
            )

    def record_provider_health(self, source: str, success: bool, error: str = "") -> None:
        now = datetime.now().astimezone().isoformat(timespec="seconds")
        with self.db.transaction() as conn:
            conn.execute("INSERT OR IGNORE INTO price_provider_health(source) VALUES (?)", (source,))
            if success:
                conn.execute(
                    "UPDATE price_provider_health SET last_success_at=?,consecutive_failures=0,last_error='' WHERE source=?",
                    (now, source),
                )
            else:
                conn.execute(
                    """UPDATE price_provider_health SET last_failure_at=?,
                       consecutive_failures=consecutive_failures+1,last_error=? WHERE source=?""",
                    (now, error, source),
                )

    def price_status_rows(self) -> list[dict]:
        securities = self.list_held_securities()
        result = []
        with self.db.connect() as conn:
            for security in securities:
                latest = conn.execute(
                    """SELECT * FROM price_history WHERE security_id=? ORDER BY price_date DESC,
                       CASE WHEN is_manual_override=1 THEN 3 WHEN source IN ('TWSE','TPEx') THEN 2 ELSE 1 END DESC,
                       updated_at DESC LIMIT 1""",
                    (security["id"],),
                ).fetchone()
                failure = conn.execute(
                    """SELECT d.* FROM price_update_details d
                       WHERE d.security_id=? AND d.status='FAILED' ORDER BY d.created_at DESC LIMIT 1""",
                    (security["id"],),
                ).fetchone()
                row = {**security, **(dict(latest) if latest else {})}
                row["security_id"] = security["id"]
                fetched_at = str(row.get("fetched_at") or row.get("updated_at") or "")
                failed_time = str(failure["created_at"] if failure else "").replace("T", " ")[:19]
                price_time = fetched_at.replace("T", " ")[:19]
                failed_after_price = bool(failure and failed_time > price_time)
                if not latest:
                    row["price_status"] = "無價格"
                elif failed_after_price:
                    row["price_status"] = "過期／更新失敗"
                elif row.get("is_manual_override"):
                    row["price_status"] = "手動覆寫"
                elif row.get("source") == "FinMind":
                    row["price_status"] = "備援"
                elif fetched_at[:10] == date.today().isoformat():
                    row["price_status"] = "最新可取得"
                else:
                    row["price_status"] = "快取"
                row["last_error"] = failure["message"] if failed_after_price else ""
                result.append(row)
        return result

    def price_update_runs(self, limit: int = 200) -> list[dict]:
        with self.db.connect() as conn:
            return [dict(row) for row in conn.execute(
                "SELECT * FROM price_update_runs ORDER BY id DESC LIMIT ?", (limit,)
            )]

    def get_lot(self, lot_id: str) -> dict | None:
        with self.db.connect() as conn:
            return _dict(conn.execute("SELECT * FROM buy_lots WHERE id=?", (lot_id,)).fetchone())

    def update_lot_strategy(self, lot_id: str, target_return_pct: object, tolerance_amount: object | None = None) -> None:
        with self.db.transaction() as conn:
            old = _dict(conn.execute("SELECT target_return_pct,recovery_tolerance_amount FROM buy_lots WHERE id=?", (lot_id,)).fetchone())
            if not old:
                raise ValueError("找不到買進批次")
            tolerance = old["recovery_tolerance_amount"] if tolerance_amount is None else float(dec(tolerance_amount))
            conn.execute("UPDATE buy_lots SET target_return_pct=?,recovery_tolerance_amount=?,strategy_created_from_security_default=0,updated_at=CURRENT_TIMESTAMP WHERE id=?", (float(dec(target_return_pct)), tolerance, lot_id))
            self._audit(conn, "修改", "買進批次策略", lot_id, old, {"target_return_pct": str(target_return_pct), "recovery_tolerance_amount": str(tolerance)})

    def list_sells(self, lot_id: str | None = None) -> list[dict]:
        with self.db.connect() as conn:
            if lot_id:
                rows = conn.execute("SELECT * FROM sell_transactions WHERE lot_id=? ORDER BY sell_date,id", (lot_id,))
            else:
                rows = conn.execute("SELECT * FROM sell_transactions ORDER BY sell_date DESC,id DESC")
            return [dict(r) for r in rows]

    def master_rows(self) -> list[dict]:
        with self.db.connect() as conn:
            lots = [dict(r) for r in conn.execute("""
                SELECT b.*,s.symbol,s.name AS security_name,s.market,
                    br.name AS broker_name,ss.near_target_alert_pct,
                    (SELECT price FROM price_history p WHERE p.security_id=b.security_id ORDER BY p.price_date DESC,
                        CASE WHEN p.is_manual_override=1 THEN 3 WHEN p.source IN ('TWSE','TPEx') THEN 2 ELSE 1 END DESC,p.updated_at DESC LIMIT 1) current_price,
                    (SELECT price_date FROM price_history p WHERE p.security_id=b.security_id ORDER BY p.price_date DESC,
                        CASE WHEN p.is_manual_override=1 THEN 3 WHEN p.source IN ('TWSE','TPEx') THEN 2 ELSE 1 END DESC,p.updated_at DESC LIMIT 1) price_date,
                    COALESCE((SELECT SUM(amount) FROM loan_transactions lt WHERE lt.lot_id=b.id AND lt.transaction_type='INTEREST'),0) loan_interest,
                    COALESCE((SELECT SUM(net_amount) FROM dividends d WHERE d.lot_id=b.id AND d.include_in_recovery=1),0) dividend_recovery,
                    COALESCE((SELECT SUM(share_change) FROM corporate_actions ca WHERE ca.lot_id=b.id),0) action_share_change,
                    (SELECT MAX(sx.sell_date) FROM sell_transactions sx WHERE sx.lot_id=b.id) last_sell_date
                FROM buy_lots b JOIN securities s ON s.id=b.security_id
                JOIN security_strategies ss ON ss.security_id=s.id
                LEFT JOIN broker_accounts br ON br.id=b.broker_account_id
                WHERE b.archived=0 ORDER BY b.buy_date DESC,b.id DESC
            """)]
            sells_by_lot: dict[str, list[dict]] = {}
            for row in conn.execute("SELECT * FROM sell_transactions ORDER BY sell_date"):
                sells_by_lot.setdefault(row["lot_id"], []).append(dict(row))
        result = []
        for lot in lots:
            adjusted = dict(lot)
            adjusted["original_shares"] = int(lot["original_shares"] + lot.get("action_share_change", 0))
            metrics = calculate_lot_metrics(adjusted, sells_by_lot.get(lot["id"], []), current_price=lot.get("current_price") or 0,
                                            loan_interest=lot.get("loan_interest"), dividend_recovery=lot.get("dividend_recovery"),
                                            near_target_pct=lot.get("near_target_alert_pct"))
            row = {**lot, **metrics.__dict__}
            row["holding_days"] = (date.today() - date.fromisoformat(lot["buy_date"])).days
            result.append(row)
        return result

    def dashboard(self) -> dict:
        rows = self.master_rows()
        with self.db.connect() as conn:
            dividends = conn.execute("SELECT COALESCE(SUM(net_amount),0) FROM dividends").fetchone()[0]
            interest = conn.execute("SELECT COALESCE(SUM(amount),0) FROM loan_transactions WHERE transaction_type='INTEREST'").fetchone()[0]
            original_loans = conn.execute("SELECT COALESCE(SUM(original_principal),0) FROM loans").fetchone()[0]
            repayments = conn.execute("SELECT COALESCE(SUM(amount),0) FROM loan_transactions WHERE transaction_type='REPAYMENT'").fetchone()[0]
        recovered_count = sum(1 for r in rows if r["strategy_status"].value in {"COMPLETED_WITH_TOLERANCE", "PRINCIPAL_RECOVERED", "FULL_COST_RECOVERED", "FREE_SHARES", "CLOSED"})
        return {
            "market_value": sum(r["market_value"] for r in rows),
            "original_capital": sum(r["original_capital"] for r in rows),
            "net_cash_recovered": sum(r["net_cash_recovered"] for r in rows),
            "capital_at_risk": sum(r["remaining_capital_at_risk"] for r in rows),
            "free_share_value": sum(r["free_share_value"] for r in rows),
            "cash_surplus": sum(r["cash_surplus"] for r in rows),
            "dividends": dec(dividends), "loan_interest": dec(interest),
            "loan_balance": max(Decimal("0"), dec(original_loans) - dec(repayments)),
            "recovered_lots": recovered_count, "total_lots": len(rows),
        }

    def audit_rows(self, limit: int = 500) -> list[dict]:
        with self.db.connect() as conn:
            return [dict(r) for r in conn.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,))]

    def table_rows(self, table: str) -> list[dict]:
        allowed = {"buy_lots", "sell_transactions", "dividends", "corporate_actions", "loans", "loan_transactions", "securities", "security_strategies", "price_history", "price_update_runs", "price_update_details", "price_provider_health", "broker_accounts", "reconciliations", "ocr_drafts", "settings", "audit_log", "backup_targets", "backup_runs", "backup_target_results"}
        if table not in allowed:
            raise ValueError("不允許匯出的資料表")
        with self.db.connect() as conn:
            rows = [dict(r) for r in conn.execute(f"SELECT * FROM {table}")]
        if table == "settings":
            for row in rows:
                if row.get("key") == "price_finmind_token" and row.get("value"):
                    row["value"] = "***（未匯出）"
        return rows

    def _reserve_trade_key(self, conn: sqlite3.Connection, values: dict, tx_type: str, tx_id: str) -> None:
        broker_id = values.get("broker_account_id")
        order_id = (values.get("broker_order_id") or "").strip()
        execution_id = (values.get("broker_execution_id") or "").strip()
        if not broker_id or not order_id:
            return
        broker = conn.execute("SELECT unique_scope FROM broker_accounts WHERE id=?", (broker_id,)).fetchone()
        scope = broker[0] if broker else "ACCOUNT"
        trade_date = values.get("buy_date") or values.get("sell_date") or ""
        if scope == "DAILY":
            key = f"{broker_id}|{trade_date}|{order_id}|{execution_id}"
        elif scope == "ORDER_EXECUTION":
            key = f"{broker_id}|{order_id}|{execution_id}"
        else:
            key = f"{broker_id}|{order_id}"
        try:
            conn.execute("INSERT INTO broker_trade_keys(key,broker_account_id,trade_date,broker_order_id,broker_execution_id,transaction_type,transaction_id) VALUES (?,?,?,?,?,?,?)", (key, broker_id, trade_date, order_id, execution_id, tx_type, tx_id))
        except sqlite3.IntegrityError as exc:
            existing = conn.execute("SELECT transaction_type,transaction_id FROM broker_trade_keys WHERE key=?", (key,)).fetchone()
            raise DuplicateTradeError(f"此券商下單編號已存在：{existing['transaction_type']} {existing['transaction_id']}") from exc

    @staticmethod
    def _audit(conn: sqlite3.Connection, action: str, entity_type: str, entity_id: str, old: object, new: object) -> None:
        conn.execute("INSERT INTO audit_log(action,entity_type,entity_id,old_value,new_value) VALUES (?,?,?,?,?)", (
            action, entity_type, entity_id, json.dumps(old, ensure_ascii=False, default=str) if old is not None else None,
            json.dumps(new, ensure_ascii=False, default=str) if new is not None else None))
