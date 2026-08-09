__all__ = ["PriceService", "PriceUpdateService"]


def __getattr__(name):
    # 避免 database.repository 載入報價資料模型時產生循環匯入。
    if name == "PriceService":
        from .price_service import PriceService

        return PriceService
    if name == "PriceUpdateService":
        from .price_update_service import PriceUpdateService

        return PriceUpdateService
    raise AttributeError(name)
