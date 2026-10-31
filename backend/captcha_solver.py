"""
CAPTCHA Recognition Engine using ddddocr.
Provides automated classification and solving for Lawbank & Lawdata verification codes.
"""
import io
from typing import Optional

try:
    import ddddocr
    _ocr_instance = None

    def get_ocr_instance():
        global _ocr_instance
        if _ocr_instance is None:
            _ocr_instance = ddddocr.DdddOcr(show_ad=False)
        return _ocr_instance

except ImportError:
    get_ocr_instance = None


class CaptchaSolver:
    @staticmethod
    def is_available() -> bool:
        return get_ocr_instance is not None

    @staticmethod
    def solve(image_bytes: bytes) -> Optional[str]:
        """
        Recognizes captcha from raw image bytes (PNG, JPEG, GIF, BMP).
        Returns the recognized string, cleaned of spaces.
        """
        if not image_bytes or not CaptchaSolver.is_available():
            return None
        try:
            ocr = get_ocr_instance()
            result = ocr.classification(image_bytes)
            if result:
                cleaned = str(result).strip().replace(" ", "")
                return cleaned
            return None
        except Exception as e:
            print(f"Captcha recognition error: {e}")
            return None

