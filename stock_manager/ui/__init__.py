"""使用者介面主題與共用視覺工具。

主題物件採延遲載入，避免只執行資料層測試時就要求安裝 PySide6。
"""

from importlib import import_module

__all__ = [
    "COLORS",
    "THEME_VERSION",
    "apply_light_theme",
    "chart_colors",
    "return_foreground",
    "set_widget_property",
    "strategy_colors",
]


def __getattr__(name: str):
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    theme = import_module(".theme", __name__)
    value = getattr(theme, name)
    globals()[name] = value
    return value
