"""
Test CAPTCHA solver using ddddocr.
Generates a test captcha image with PIL and verifies ddddocr recognition accuracy.
"""
import io
import ddddocr
from PIL import Image, ImageDraw, ImageFont

def test_ocr():
    ocr = ddddocr.DdddOcr(show_ad=False)
    
    # Create a simple test captcha image in memory (e.g. '8492')
    img = Image.new('RGB', (120, 45), color=(240, 240, 240))
    d = ImageDraw.Draw(img)
    
    # Draw simple text
    text = "8492"
    d.text((25, 12), text, fill=(20, 20, 20))
    
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    img_bytes = buf.getvalue()
    
    result = ocr.classification(img_bytes)
    print(f"Original Text: {text} | OCR Recognized: {result} | Match: {result == text}")
    assert result == text, f"Expected {text}, got {result}"
    print("ddddocr verification test PASSED!")

if __name__ == "__main__":
    test_ocr()

