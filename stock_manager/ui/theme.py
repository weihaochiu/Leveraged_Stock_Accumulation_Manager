from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtGui import QColor, QPalette


THEME_VERSION = "1.0.2"


COLORS = {
    "app_background": "#F8FAFC",
    "surface": "#FFFFFF",
    "surface_muted": "#F1F5F9",
    "text_primary": "#0F172A",
    "text_secondary": "#475569",
    "text_muted": "#64748B",
    "border": "#CBD5E1",
    "divider": "#E2E8F0",
    "primary": "#1D4ED8",
    "primary_hover": "#1E40AF",
    "primary_pressed": "#1E3A8A",
    "primary_soft": "#DBEAFE",
    "info": "#2563EB",
    "info_soft": "#EFF6FF",
    "info_text": "#1E3A8A",
    "success": "#047857",
    "success_soft": "#D1FAE5",
    "warning": "#B45309",
    "warning_soft": "#FEF3C7",
    "danger": "#B91C1C",
    "danger_hover": "#991B1B",
    "danger_soft": "#FEE2E2",
    "disabled_text": "#64748B",
    "disabled_background": "#E2E8F0",
}


def _color(name: str) -> QColor:
    return QColor(COLORS[name])


def _set_group(palette: QPalette, group: QPalette.ColorGroup) -> None:
    palette.setColor(group, QPalette.Window, _color("app_background"))
    palette.setColor(group, QPalette.WindowText, _color("text_primary"))
    palette.setColor(group, QPalette.Base, _color("surface"))
    palette.setColor(group, QPalette.AlternateBase, _color("app_background"))
    palette.setColor(group, QPalette.ToolTipBase, _color("text_primary"))
    palette.setColor(group, QPalette.ToolTipText, _color("surface"))
    palette.setColor(group, QPalette.Text, _color("text_primary"))
    palette.setColor(group, QPalette.Button, _color("surface"))
    palette.setColor(group, QPalette.ButtonText, _color("text_primary"))
    palette.setColor(group, QPalette.BrightText, _color("danger"))
    palette.setColor(group, QPalette.Link, _color("primary"))
    palette.setColor(group, QPalette.Highlight, _color("primary_soft"))
    palette.setColor(group, QPalette.HighlightedText, _color("text_primary"))
    palette.setColor(group, QPalette.PlaceholderText, _color("text_muted"))


def build_light_palette() -> QPalette:
    """建立不受作業系統深淺色模式影響的完整淺色調色盤。"""
    palette = QPalette()
    _set_group(palette, QPalette.Active)
    _set_group(palette, QPalette.Inactive)
    _set_group(palette, QPalette.Disabled)
    palette.setColor(QPalette.Disabled, QPalette.WindowText, _color("disabled_text"))
    palette.setColor(QPalette.Disabled, QPalette.Text, _color("disabled_text"))
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, _color("disabled_text"))
    palette.setColor(QPalette.Disabled, QPalette.Base, _color("disabled_background"))
    palette.setColor(QPalette.Disabled, QPalette.Button, _color("disabled_background"))
    return palette


def load_stylesheet() -> str:
    path = Path(__file__).with_name("styles.qss")
    stylesheet = path.read_text(encoding="utf-8")
    required_rules = ("QWidget {", "QToolBar {", "QHeaderView::section", "QLabel#kpiBar")
    missing = [rule for rule in required_rules if rule not in stylesheet]
    if missing:
        raise RuntimeError(f"styles.qss 不完整，缺少：{', '.join(missing)}")
    return stylesheet


def apply_light_theme(app: Any) -> None:
    """將固定淺色主題套用至整個 QApplication。"""
    app.setStyle("Fusion")
    app.setPalette(build_light_palette())
    app.setStyleSheet(load_stylesheet())
    app.setProperty("stockManagerThemeVersion", THEME_VERSION)


def set_widget_property(widget: Any, name: str, value: Any) -> None:
    """設定 QSS 動態屬性並立即重新整理元件樣式。"""
    widget.setProperty(name, value)
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


def return_foreground(value: float) -> str:
    """臺股慣例：正報酬紅、負報酬綠。零值維持中性色。"""
    numeric = float(value or 0)
    if numeric > 0:
        return COLORS["danger"]
    if numeric < 0:
        return COLORS["success"]
    return COLORS["text_primary"]


def strategy_colors(status: Any) -> tuple[str, str] | None:
    key = getattr(status, "value", status)
    return {
        "TARGET_REACHED": (COLORS["danger_soft"], COLORS["danger"]),
        "NEAR_TARGET": (COLORS["warning_soft"], COLORS["warning"]),
        "FREE_SHARES": (COLORS["success_soft"], COLORS["success"]),
        "COMPLETED_WITH_TOLERANCE": (COLORS["primary_soft"], COLORS["info_text"]),
    }.get(str(key))


def chart_colors() -> dict[str, str]:
    return {
        "primary": COLORS["info"],
        "success": COLORS["success"],
        "warning": COLORS["warning"],
        "danger": COLORS["danger"],
        "background": COLORS["surface"],
        "text": COLORS["text_primary"],
        "secondary_text": COLORS["text_secondary"],
        "grid": COLORS["divider"],
    }
