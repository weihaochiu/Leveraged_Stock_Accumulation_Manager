from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


APP_NAME = "貸款槓桿存股管理系統"
APP_VERSION = "1.0.2"
DB_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class AppPaths:
    root: Path
    data: Path
    database: Path
    logs: Path
    exports: Path
    backups: Path

    @classmethod
    def resolve(cls) -> "AppPaths":
        override = os.environ.get("STOCK_MANAGER_DATA_DIR")
        root = Path(override) if override else Path.home() / "StockAccumulationManager"
        paths = cls(
            root=root,
            data=root / "data",
            database=root / "data" / "portfolio.db",
            logs=root / "logs",
            exports=root / "exports",
            backups=root / "backups",
        )
        for directory in (paths.root, paths.data, paths.logs, paths.exports, paths.backups):
            directory.mkdir(parents=True, exist_ok=True)
        return paths
