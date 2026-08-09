from __future__ import annotations

import re
from pathlib import Path


class OCRService:
    """將辨識結果保留為 Draft；正式資料仍須經人工表單確認。"""

    def extract_text(self, image_path: str | Path) -> str:
        try:
            import pytesseract
            from PIL import Image
        except ImportError as exc:
            raise RuntimeError("尚未安裝 OCR 套件；請重新執行 setup_and_run.bat") from exc
        try:
            return pytesseract.image_to_string(Image.open(image_path), lang="chi_tra+eng")
        except pytesseract.TesseractNotFoundError as exc:
            raise RuntimeError("尚未安裝 Tesseract OCR。可先使用手動輸入，或安裝後再辨識截圖。") from exc

    def parse_trade(self, text: str) -> dict:
        result: dict[str, object] = {"raw_text": text}
        upper = text.upper()
        result["transaction_type"] = "SELL" if any(x in upper for x in ("賣出", "SELL")) else "BUY" if any(x in upper for x in ("買入", "BUY")) else ""
        symbol = re.search(r"(?<!\d)(\d{4,6})(?!\d)", text)
        date_match = re.search(r"(20\d{2})[/.\-](\d{1,2})[/.\-](\d{1,2})", text)
        order = re.search(r"(?:委託|下單|訂單)(?:編號|序號)?\s*[:：]?\s*([A-Z0-9\-]+)", upper)
        shares = re.search(r"(?:股數|成交股數|數量)\s*[:：]?\s*([\d,]+)", text)
        price = re.search(r"(?:成交價|價格|均價)\s*[:：]?\s*([\d,.]+)", text)
        amount = re.search(r"(?:成交金額|金額)\s*[:：]?\s*([\d,]+)", text)
        if symbol: result["symbol"] = symbol.group(1)
        if date_match: result["trade_date"] = f"{int(date_match.group(1)):04d}-{int(date_match.group(2)):02d}-{int(date_match.group(3)):02d}"
        if order: result["broker_order_id"] = order.group(1)
        if shares: result["shares"] = int(shares.group(1).replace(",", ""))
        if price: result["price"] = float(price.group(1).replace(",", ""))
        if amount: result["amount"] = float(amount.group(1).replace(",", ""))
        return result
