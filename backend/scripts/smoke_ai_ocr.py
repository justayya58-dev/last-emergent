"""Live provider smoke test for a non-sensitive invoice fixture.

Run from backend/ with the real provider secret configured:
    python scripts/smoke_ai_ocr.py /secure/path/to/non-sensitive-invoice.pdf

Only field-presence flags and confidence are printed; extracted values are never logged.
"""
import asyncio
import mimetypes
import os
import sys
from pathlib import Path

from services.ocr import OCR_MODEL, OcrExtractionError, extract_invoice


async def main() -> int:
    if os.environ.get("AUDITPRO_TEST_OCR", "").strip().lower() == "true":
        print("FAIL: AUDITPRO_TEST_OCR must be disabled for a real provider smoke test.")
        return 2
    if not os.environ.get("EMERGENT_LLM_KEY", "").strip():
        print("FAIL: EMERGENT_LLM_KEY is not configured.")
        return 2
    if len(sys.argv) != 2:
        print("Usage: python scripts/smoke_ai_ocr.py /path/to/non-sensitive-invoice.pdf")
        return 2

    path = Path(sys.argv[1])
    if not path.is_file():
        print("FAIL: fixture file does not exist.")
        return 2
    suffix = path.suffix.lower()
    mime_type, _ = mimetypes.guess_type(path.name)
    if suffix not in {".pdf", ".png", ".jpg", ".jpeg", ".webp"} or not mime_type:
        print("FAIL: use a supported PDF or image fixture.")
        return 2
    if path.stat().st_size > 10 * 1024 * 1024:
        print("FAIL: fixture exceeds the 10 MiB upload limit.")
        return 2

    try:
        result, confidence = await extract_invoice(path.read_bytes(), mime_type, suffix)
    except OcrExtractionError as exc:
        print(f"FAIL: provider OCR failed safely ({type(exc).__name__}). Details are intentionally redacted.")
        return 1

    required = ("vendor", "invoice_number", "invoice_date", "due_date", "subtotal", "tax", "total")
    present = {
        field: bool(getattr(result, field, None) not in (None, "", "Tidak terdeteksi"))
        for field in required
    }
    print({
        "status": "PASS",
        "provider": "Gemini via Emergent integration SDK",
        "model": OCR_MODEL,
        "field_presence": present,
        "confidence": confidence,
        "note": "Extracted values intentionally omitted; manually compare against the fixture before sign-off."
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
