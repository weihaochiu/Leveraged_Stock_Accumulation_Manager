SCHEMA_SQL = r"""
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_info (
    version INTEGER NOT NULL,
    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS sequences (
    name TEXT PRIMARY KEY,
    value INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS broker_accounts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    account_label TEXT NOT NULL DEFAULT '',
    unique_scope TEXT NOT NULL DEFAULT 'ACCOUNT',
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS securities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    name TEXT NOT NULL,
    market TEXT NOT NULL DEFAULT 'TW',
    currency TEXT NOT NULL DEFAULT 'TWD',
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, market)
);
CREATE TABLE IF NOT EXISTS security_strategies (
    security_id INTEGER PRIMARY KEY REFERENCES securities(id),
    default_target_return_pct REAL NOT NULL DEFAULT 10,
    near_target_alert_pct REAL NOT NULL DEFAULT 2,
    default_recovery_mode TEXT NOT NULL DEFAULT 'PRINCIPAL',
    include_dividend_in_recovery INTEGER NOT NULL DEFAULT 0,
    default_funding_preference TEXT NOT NULL DEFAULT 'LOAN',
    default_buy_budget REAL NOT NULL DEFAULT 10000,
    recovery_tolerance_amount REAL NOT NULL DEFAULT 100,
    recovery_tolerance_pct REAL NOT NULL DEFAULT 0,
    reminder_enabled INTEGER NOT NULL DEFAULT 1,
    note TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS loans (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    institution TEXT NOT NULL DEFAULT '',
    borrow_date TEXT NOT NULL,
    original_principal REAL NOT NULL CHECK(original_principal >= 0),
    annual_interest_rate REAL NOT NULL DEFAULT 0,
    rate_type TEXT NOT NULL DEFAULT 'FIXED',
    interest_start_date TEXT,
    maturity_date TEXT,
    repayment_method TEXT NOT NULL DEFAULT '',
    note TEXT NOT NULL DEFAULT '',
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS loan_transactions (
    id TEXT PRIMARY KEY,
    loan_id TEXT NOT NULL REFERENCES loans(id),
    transaction_date TEXT NOT NULL,
    transaction_type TEXT NOT NULL,
    amount REAL NOT NULL CHECK(amount >= 0),
    lot_id TEXT,
    sell_id TEXT,
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS buy_lots (
    id TEXT PRIMARY KEY,
    security_id INTEGER NOT NULL REFERENCES securities(id),
    broker_account_id TEXT REFERENCES broker_accounts(id),
    buy_date TEXT NOT NULL,
    buy_price REAL NOT NULL CHECK(buy_price > 0),
    original_shares INTEGER NOT NULL CHECK(original_shares > 0),
    stock_amount REAL NOT NULL CHECK(stock_amount >= 0),
    buy_fee REAL NOT NULL DEFAULT 0 CHECK(buy_fee >= 0),
    other_cost REAL NOT NULL DEFAULT 0 CHECK(other_cost >= 0),
    original_capital REAL NOT NULL CHECK(original_capital >= 0),
    funding_type TEXT NOT NULL,
    loan_id TEXT REFERENCES loans(id),
    loan_funded REAL NOT NULL DEFAULT 0 CHECK(loan_funded >= 0),
    cash_funded REAL NOT NULL DEFAULT 0 CHECK(cash_funded >= 0),
    target_return_pct REAL NOT NULL,
    recovery_mode TEXT NOT NULL DEFAULT 'PRINCIPAL',
    recovery_tolerance_amount REAL NOT NULL DEFAULT 100,
    recovery_tolerance_pct REAL NOT NULL DEFAULT 0,
    strategy_created_from_security_default INTEGER NOT NULL DEFAULT 1,
    broker_order_id TEXT,
    broker_execution_id TEXT,
    note TEXT NOT NULL DEFAULT '',
    archived INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS sell_transactions (
    id TEXT PRIMARY KEY,
    lot_id TEXT NOT NULL REFERENCES buy_lots(id),
    security_id INTEGER NOT NULL REFERENCES securities(id),
    broker_account_id TEXT REFERENCES broker_accounts(id),
    sell_date TEXT NOT NULL,
    sell_price REAL NOT NULL CHECK(sell_price > 0),
    shares INTEGER NOT NULL CHECK(shares > 0),
    gross_amount REAL NOT NULL CHECK(gross_amount >= 0),
    commission REAL NOT NULL DEFAULT 0 CHECK(commission >= 0),
    tax REAL NOT NULL DEFAULT 0 CHECK(tax >= 0),
    other_fee REAL NOT NULL DEFAULT 0 CHECK(other_fee >= 0),
    net_cash REAL NOT NULL,
    repay_loan INTEGER NOT NULL DEFAULT 0,
    loan_repayment_amount REAL NOT NULL DEFAULT 0 CHECK(loan_repayment_amount >= 0),
    broker_order_id TEXT,
    broker_execution_id TEXT,
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS broker_trade_keys (
    key TEXT PRIMARY KEY,
    broker_account_id TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    broker_order_id TEXT NOT NULL,
    broker_execution_id TEXT NOT NULL DEFAULT '',
    transaction_type TEXT NOT NULL,
    transaction_id TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS dividends (
    id TEXT PRIMARY KEY,
    security_id INTEGER NOT NULL REFERENCES securities(id),
    lot_id TEXT REFERENCES buy_lots(id),
    broker_account_id TEXT REFERENCES broker_accounts(id),
    dividend_type TEXT NOT NULL DEFAULT 'CASH',
    ex_date TEXT,
    payment_date TEXT NOT NULL,
    base_shares REAL NOT NULL DEFAULT 0,
    dividend_per_share REAL NOT NULL DEFAULT 0,
    gross_amount REAL NOT NULL DEFAULT 0,
    tax REAL NOT NULL DEFAULT 0,
    insurance_fee REAL NOT NULL DEFAULT 0,
    other_fee REAL NOT NULL DEFAULT 0,
    net_amount REAL NOT NULL DEFAULT 0,
    include_in_recovery INTEGER NOT NULL DEFAULT 0,
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS corporate_actions (
    id TEXT PRIMARY KEY,
    security_id INTEGER NOT NULL REFERENCES securities(id),
    lot_id TEXT REFERENCES buy_lots(id),
    action_type TEXT NOT NULL,
    effective_date TEXT NOT NULL,
    share_change REAL NOT NULL DEFAULT 0,
    cash_amount REAL NOT NULL DEFAULT 0,
    ratio REAL NOT NULL DEFAULT 0,
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    security_id INTEGER NOT NULL REFERENCES securities(id),
    price REAL NOT NULL CHECK(price > 0),
    price_date TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source TEXT NOT NULL DEFAULT 'MANUAL',
    daily_change_pct REAL,
    UNIQUE(security_id, price_date, source)
);
CREATE TABLE IF NOT EXISTS reconciliations (
    id TEXT PRIMARY KEY,
    session_date TEXT NOT NULL,
    security_id INTEGER NOT NULL REFERENCES securities(id),
    broker_account_id TEXT REFERENCES broker_accounts(id),
    system_shares REAL NOT NULL,
    broker_shares REAL NOT NULL,
    difference REAL NOT NULL,
    status TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    occurred_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    note TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS backup_targets (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    target_type TEXT NOT NULL DEFAULT 'LOCAL_FOLDER',
    path TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    is_primary INTEGER NOT NULL DEFAULT 0,
    retention_days INTEGER NOT NULL DEFAULT 30,
    keep_forever INTEGER NOT NULL DEFAULT 0,
    last_success_at TEXT,
    last_failure_at TEXT,
    last_error TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS backup_runs (
    id TEXT PRIMARY KEY,
    trigger_type TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    db_status TEXT NOT NULL DEFAULT 'PENDING',
    excel_status TEXT NOT NULL DEFAULT 'PENDING',
    status TEXT NOT NULL DEFAULT 'PENDING',
    package_path TEXT,
    manifest_json TEXT,
    error_message TEXT
);
CREATE TABLE IF NOT EXISTS backup_target_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    backup_id TEXT NOT NULL REFERENCES backup_runs(id),
    target_id TEXT NOT NULL REFERENCES backup_targets(id),
    status TEXT NOT NULL,
    destination_path TEXT,
    error_message TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS ocr_drafts (
    id TEXT PRIMARY KEY,
    source_file TEXT NOT NULL,
    draft_type TEXT NOT NULL,
    extracted_json TEXT NOT NULL DEFAULT '{}',
    confidence_json TEXT NOT NULL DEFAULT '{}',
    duplicate_status TEXT NOT NULL DEFAULT 'NOT_CHECKED',
    confirmed INTEGER NOT NULL DEFAULT 0,
    imported INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_lots_security ON buy_lots(security_id);
CREATE INDEX IF NOT EXISTS idx_sells_lot ON sell_transactions(lot_id);
CREATE INDEX IF NOT EXISTS idx_prices_security_date ON price_history(security_id, price_date DESC);
CREATE INDEX IF NOT EXISTS idx_dividends_lot ON dividends(lot_id);
"""

DEFAULT_SETTINGS = {
    "default_market": "TW",
    "currency": "TWD",
    "commission_rate": "0.001425",
    "commission_discount": "0.6",
    "minimum_commission": "1",
    "sell_tax_rate": "0.003",
    "default_target_return_pct": "10",
    "near_target_alert_pct": "2",
    "default_buy_budget": "10000",
    "recovery_tolerance_amount": "100",
    "include_interest_in_full_cost": "1",
    "backup_on_startup": "1",
    "backup_frequency": "DAILY_FIRST",
    "backup_on_exit": "0",
    "last_startup_backup_date": "",
}

