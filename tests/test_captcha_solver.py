"""
Unit tests for CaptchaSolver.
"""
import unittest
import io
from PIL import Image, ImageDraw
from backend.captcha_solver import CaptchaSolver


class TestCaptchaSolver(unittest.TestCase):
    def test_solver_availability(self):
        self.assertTrue(CaptchaSolver.is_available())

    def test_empty_bytes(self):
        self.assertIsNone(CaptchaSolver.solve(b""))

    def test_simple_image_solve(self):
        # Create a 28px standard text image
        img = Image.new("RGB", (160, 60), color=(255, 255, 255))
        d = ImageDraw.Draw(img)
        d.text((30, 20), "ABC", fill=(0, 0, 0))
        
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        res = CaptchaSolver.solve(buf.getvalue())
        self.assertIsNotNone(res)
        self.assertTrue(len(res) > 0)


if __name__ == "__main__":
    unittest.main()

