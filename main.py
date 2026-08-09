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
    from stock_manager.ui import apply_light_theme

    paths=AppPaths.resolve(); configure_logging(paths.logs); db=Database(paths.database); repository=PortfolioRepository(db)
    backup=BackupService(db,repository,paths.backups); backup.ensure_default_target(paths.backups)
    settings=repository.settings(); startup_result=None
    if settings.get("backup_on_startup")=="1":
        should_run=settings.get("backup_frequency")=="EVERY_START" or settings.get("last_startup_backup_date") != date.today().isoformat()
        if should_run:
            startup_result=backup.run("STARTUP")
            if startup_result.get("successes",0)>0: repository.set_setting("last_startup_backup_date",date.today().isoformat())
        else: startup_result={"status":"SKIPPED","successes":0,"total":len(backup.targets())}
    app=QApplication(sys.argv); app.setApplicationName(APP_NAME); apply_light_theme(app)
    window=MainWindow(repository,paths,backup,startup_result); window.show(); return app.exec()
