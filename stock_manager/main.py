from __future__ import annotations

import sys
from datetime import date

from stock_manager.config import APP_NAME, AppPaths
from stock_manager.database import Database, PortfolioRepository
from stock_manager.import_export import BackupService
from stock_manager.utils.logging_setup import configure_logging


def main() -> int:
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox
    except ImportError:
        print("缺少 PySide6。Windows 使用者請雙擊 setup_and_run.bat 完成安裝。")
        return 2
    from stock_manager.app.main_window import MainWindow
    try:
        from stock_manager.ui import THEME_VERSION, apply_light_theme
    except (ImportError, OSError) as exc:
        print(f"配色主題檔案不完整或未放在正確位置：{exc}")
        print("請將更新 ZIP 解壓縮到原程式根目錄，並確認已覆蓋 stock_manager 資料夾。")
        return 3

    paths=AppPaths.resolve(); configure_logging(paths.logs); db=Database(paths.database); repository=PortfolioRepository(db)
    backup=BackupService(db,repository,paths.backups); backup.ensure_default_target(paths.backups)
    settings=repository.settings(); startup_result=None
    if settings.get("backup_on_startup")=="1":
        should_run=settings.get("backup_frequency")=="EVERY_START" or settings.get("last_startup_backup_date") != date.today().isoformat()
        if should_run:
            startup_result=backup.run("STARTUP")
            if startup_result.get("successes",0)>0: repository.set_setting("last_startup_backup_date",date.today().isoformat())
        else: startup_result={"status":"SKIPPED","successes":0,"total":len(backup.targets())}
    app=QApplication(sys.argv); app.setApplicationName(APP_NAME)
    try:
        apply_light_theme(app)
    except Exception as exc:
        QMessageBox.critical(
            None,
            "配色主題載入失敗",
            "新版配色沒有成功載入。\n\n"
            f"錯誤：{exc}\n\n"
            "請重新將更新 ZIP 解壓縮到原程式根目錄並覆蓋檔案。",
        )
        return 3
    window=MainWindow(repository,paths,backup,startup_result)
    window.setWindowTitle(f"{APP_NAME} v{THEME_VERSION}｜淺色主題修正版")
    window.show(); return app.exec()
