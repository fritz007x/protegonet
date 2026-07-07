from __future__ import annotations

import io

import pytest

from cyber_agent.preprocessing.ocr import extract_invoice_fields


def test_png_bytes_route_to_ocr_and_degrade_gracefully():
    """A PNG that OCR can't read (or with no tesseract binary) must not crash;
    it degrades to empty text, keeping the pipeline offline-safe."""
    fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    fields = extract_invoice_fields(fake_png)
    assert isinstance(fields, dict)
    assert fields["text"] == ""
    assert fields["vendor"] is None


def _tesseract_available() -> bool:
    try:
        import pytesseract  # type: ignore

        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


@pytest.mark.skipif(not _tesseract_available(), reason="tesseract binary not installed")
def test_image_ocr_extracts_invoice_fields():
    from PIL import Image, ImageDraw  # type: ignore

    img = Image.new("RGB", (520, 120), "white")
    draw = ImageDraw.Draw(img)
    draw.text((10, 10), "Vendor: Acme Supplies", fill="black")
    draw.text((10, 50), "Amount Due: $500.00", fill="black")
    buf = io.BytesIO()
    img.save(buf, format="PNG")

    fields = extract_invoice_fields(buf.getvalue())
    assert "Acme" in (fields["text"] or "")
