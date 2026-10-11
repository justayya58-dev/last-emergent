import json
import os
from pathlib import Path
import tempfile

from emergentintegrations.llm.chat import (
    FileContentWithMimeType,
    LlmChat,
    StreamDone,
    TextDelta,
    UserMessage,
)

from models.auditpro import ExtractionData


OCR_MODEL = "gemini-3.8-flash"


class OcrExtractionError(RuntimeError):
    """Raised when the OCR provider cannot return a valid invoice extraction."""


def _extract_json(content: str) -> dict:
    start = content.find("{")
    end = content.rfind("}")
    if start < 0 or end <= start:
        raise OcrExtractionError("Respons OCR tidak berisi JSON yang valid")
    try:
        parsed = json.loads(content[start : end + 1])
    except json.JSONDecodeError as exc:
        raise OcrExtractionError("Respons OCR tidak dapat dibaca") from exc
    if not isinstance(parsed, dict):
        raise OcrExtractionError("Format respons OCR tidak sesuai")
    return parsed


async def extract_invoice(file_bytes: bytes, mime_type: str, suffix: str) -> tuple[ExtractionData, int]:
    # Deterministic fixture extraction is only enabled in the isolated CI environment.
    # Never enable AUDITPRO_TEST_OCR in production deployments.
    if os.environ.get("AUDITPRO_TEST_OCR") == "true":
        extraction = ExtractionData(
            vendor="PT Tscheck Mandiri Jaya",
            invoice_number="TSK-INV-90210",
            invoice_date="2026-05-01",
            due_date="2026-05-31",
            subtotal=500000,
            tax=55000,
            total=555000,
            category="Operasional",
        )
        return extraction, 98

    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise OcrExtractionError("Layanan OCR belum dikonfigurasi")

    temp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(file_bytes)
            temp_path = temp_file.name

        attachment = FileContentWithMimeType(mime_type=mime_type, file_path=temp_path)
        chat = (
            LlmChat(
                api_key=api_key,
                session_id=f"auditpro-ocr-{Path(temp_path).stem}",
                system_message=(
                    "Anda adalah mesin OCR invoice bisnis Indonesia. Baca hanya informasi yang terlihat "
                    "pada dokumen. Jangan mengarang nilai yang tidak ditemukan. Kembalikan JSON saja."
                ),
            )
            .with_model("gemini", OCR_MODEL)
            .with_params(temperature=0.0, max_tokens=1200)
        )
        prompt = """Ekstrak invoice atau kuitansi terlampir menjadi SATU objek JSON dengan tepat skema ini:
{
  "vendor": "nama vendor atau 'Tidak terdeteksi'",
  "invoice_number": "nomor invoice atau 'Tidak terdeteksi'",
  "invoice_date": "YYYY-MM-DD atau string kosong",
  "due_date": "YYYY-MM-DD atau string kosong",
  "subtotal": 0,
  "tax": 0,
  "total": 0,
  "category": "kategori biaya singkat dalam Bahasa Indonesia",
  "confidence": 0
}
Semua nominal harus angka tanpa simbol mata uang atau pemisah ribuan. Confidence adalah integer 0-100 berdasarkan keterbacaan dan kelengkapan. Jika due date tidak terlihat, gunakan string kosong; jangan menyamakannya dengan tanggal invoice. Jangan sertakan markdown atau penjelasan."""

        chunks: list[str] = []
        async for event in chat.stream_message(UserMessage(text=prompt, file_contents=[attachment])):
            if isinstance(event, TextDelta):
                chunks.append(event.content)
            elif isinstance(event, StreamDone) and event.content and not chunks:
                chunks.append(event.content)

        raw = _extract_json("".join(chunks))
        extraction = ExtractionData.model_validate(raw)
        confidence = max(0, min(100, int(raw.get("confidence", 0))))
        return extraction, confidence
    except OcrExtractionError:
        raise
    except Exception as exc:
        raise OcrExtractionError("Gemini tidak dapat memproses dokumen ini") from exc
    finally:
        if temp_path:
            Path(temp_path).unlink(missing_ok=True)