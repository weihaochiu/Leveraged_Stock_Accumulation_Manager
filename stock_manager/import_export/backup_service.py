from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from stock_manager import __version__
from stock_manager.config import DB_SCHEMA_VERSION
from stock_manager.database import Database, PortfolioRepository
from .excel_service import ExcelService


class BackupService:
    def __init__(self, db: Database, repository: PortfolioRepository, staging_root: Path):
        self.db = db
        self.repository = repository
        self.staging_root = Path(staging_root)
        self.excel = ExcelService(repository)

    def ensure_default_target(self, path: Path) -> None:
        with self.db.transaction() as conn:
            if conn.execute("SELECT COUNT(*) FROM backup_targets").fetchone()[0] == 0:
                conn.execute("INSERT INTO backup_targets(id,name,path,enabled,is_primary) VALUES ('BACKUP-DEFAULT','本機備份',?,1,1)", (str(path),))

    def targets(self) -> list[dict]:
        with self.db.connect() as conn:
            return [dict(r) for r in conn.execute("SELECT * FROM backup_targets ORDER BY is_primary DESC,name")]

    def add_target(self, name: str, path: str, target_type: str = "LOCAL_FOLDER", retention_days: int = 30) -> str:
        with self.db.transaction() as conn:
            target_id = self.db.next_id(conn, "backup_target", "BT")
            conn.execute("INSERT INTO backup_targets(id,name,target_type,path,retention_days) VALUES (?,?,?,?,?)", (target_id, name, target_type, path, retention_days))
            return target_id

    def run(self, trigger: str = "MANUAL") -> dict:
        stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        backup_id = f"BACKUP-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        staging = self.staging_root / f".{backup_id}"
        staging.mkdir(parents=True, exist_ok=True)
        db_snapshot, xlsx, manifest_path = staging / "portfolio.db", staging / "portfolio.xlsx", staging / "backup_manifest.json"
        started = datetime.now().isoformat(timespec="seconds")
        with self.db.transaction() as conn:
            conn.execute("INSERT INTO backup_runs(id,trigger_type,started_at) VALUES (?,?,?)", (backup_id, trigger, started))
        results = []
        try:
            self._snapshot(db_snapshot)
            self.excel.export_complete(xlsx)
            manifest = {
                "backup_id": backup_id, "created_at": datetime.now().isoformat(timespec="seconds"),
                "trigger": trigger, "application_version": __version__, "database_schema_version": DB_SCHEMA_VERSION,
                "files": {
                    "portfolio.db": self._sha256(db_snapshot),
                    "portfolio.xlsx": self._sha256(xlsx),
                },
            }
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            for target in [t for t in self.targets() if t["enabled"]]:
                try:
                    root = Path(target["path"])
                    root.mkdir(parents=True, exist_ok=True)
                    destination = root / stamp
                    shutil.copytree(staging, destination)
                    if not self._verify_package(destination):
                        raise RuntimeError("備份完整性驗證失敗")
                    results.append({"target": target, "status": "SUCCESS", "path": str(destination), "error": None})
                    with self.db.transaction() as conn:
                        conn.execute("UPDATE backup_targets SET last_success_at=CURRENT_TIMESTAMP,last_error=NULL WHERE id=?", (target["id"],))
                    self._prune(root, int(target["retention_days"]), bool(target["keep_forever"]))
                except Exception as exc:
                    results.append({"target": target, "status": "FAILED", "path": None, "error": str(exc)})
                    with self.db.transaction() as conn:
                        conn.execute("UPDATE backup_targets SET last_failure_at=CURRENT_TIMESTAMP,last_error=? WHERE id=?", (str(exc), target["id"]))
            successes = sum(1 for r in results if r["status"] == "SUCCESS")
            status = "SUCCESS" if results and successes == len(results) else "PARTIAL" if successes else "FAILED"
            with self.db.transaction() as conn:
                conn.execute("UPDATE backup_runs SET completed_at=?,db_status='SUCCESS',excel_status='SUCCESS',status=?,manifest_json=? WHERE id=?", (datetime.now().isoformat(timespec="seconds"), status, json.dumps(manifest, ensure_ascii=False), backup_id))
                for result in results:
                    conn.execute("INSERT INTO backup_target_results(backup_id,target_id,status,destination_path,error_message) VALUES (?,?,?,?,?)", (backup_id, result["target"]["id"], result["status"], result["path"], result["error"]))
            return {"backup_id": backup_id, "status": status, "successes": successes, "total": len(results), "results": results}
        except Exception as exc:
            with self.db.transaction() as conn:
                conn.execute("UPDATE backup_runs SET completed_at=?,status='FAILED',error_message=? WHERE id=?", (datetime.now().isoformat(timespec="seconds"), str(exc), backup_id))
            return {"backup_id": backup_id, "status": "FAILED", "successes": 0, "total": len(results), "results": results, "error": str(exc)}
        finally:
            shutil.rmtree(staging, ignore_errors=True)

    def history(self) -> list[dict]:
        with self.db.connect() as conn:
            return [dict(r) for r in conn.execute("SELECT * FROM backup_runs ORDER BY started_at DESC LIMIT 200")]

    def _snapshot(self, destination: Path) -> None:
        source = sqlite3.connect(self.db.path)
        target = sqlite3.connect(destination)
        try:
            source.backup(target)
            if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise RuntimeError("SQLite 完整性檢查未通過")
        finally:
            target.close(); source.close()

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _verify_package(self, folder: Path) -> bool:
        manifest = json.loads((folder / "backup_manifest.json").read_text(encoding="utf-8"))
        return all((folder / name).exists() and self._sha256(folder / name) == expected for name, expected in manifest["files"].items())

    @staticmethod
    def _prune(root: Path, retention_days: int, keep_forever: bool) -> None:
        if keep_forever or retention_days <= 0:
            return
        cutoff = datetime.now() - timedelta(days=retention_days)
        valid = [p for p in root.iterdir() if p.is_dir() and (p / "backup_manifest.json").exists()]
        if not valid:
            return
        for folder in valid:
            try:
                created = datetime.strptime(folder.name, "%Y-%m-%d_%H%M%S")
                if created < cutoff and len(valid) > 1:
                    shutil.rmtree(folder)
                    valid.remove(folder)
            except ValueError:
                continue

