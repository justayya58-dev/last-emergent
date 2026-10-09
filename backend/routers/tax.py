import csv
from datetime import date, datetime, timezone
import io

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from lib.dates import today_iso
from lib.db import db
from models.auditpro import (
    Customer,
    Invoice,
    TaxActionRequest,
    TaxDocument,
    TaxDocumentUpdate,
    TaxRateProfile,
    TaxRateSummary,
    TaxStatusEvent,
    TaxSummary,
    TaxSyncResult,
    Transaction,
)
from services.tax_exports import build_tax_xlsx


router = APIRouter(prefix="/tax", tags=["tax"])
RATE_PROFILES = [
    TaxRateProfile(rate=0, label="PPN 0%", description="Transaksi tidak terutang atau fasilitas PPN"),
    TaxRateProfile(rate=11, label="PPN 11%", description="Tarif reguler yang digunakan pada banyak transaksi"),
    TaxRateProfile(rate=12, label="PPN 12%", description="Profil tarif alternatif sesuai kebijakan transaksi"),
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def nearest_rate(dpp: float, vat: float) -> int:
    if dpp <= 0 or vat <= 0:
        return 0
    observed = vat / dpp * 100
    return min((0, 11, 12), key=lambda rate: abs(rate - observed))


def validate_tax_fields(document: TaxDocument) -> tuple[list[str], list[str], int]:
    checks = {
        "Referensi sumber": bool(document.source_reference.strip()),
        "NPWP": bool(document.npwp.strip()),
        "Nomor faktur pajak": bool(document.tax_invoice_number.strip()),
        "Tanggal dokumen": False,
        "DPP": document.dpp > 0,
        "Perhitungan PPN": abs(document.vat - round(document.dpp * document.tax_rate / 100, 2)) <= 1,
    }
    try:
        date.fromisoformat(document.document_date)
        checks["Tanggal dokumen"] = True
    except ValueError:
        pass
    missing = [label for label, valid in checks.items() if not valid]
    notes: list[str] = []
    if "Perhitungan PPN" in missing:
        notes.append("Nilai PPN tidak sesuai DPP × tarif pajak")
    if not document.npwp.strip():
        notes.append("NPWP pihak lawan transaksi belum tersedia")
    score = round((len(checks) - len(missing)) / len(checks) * 100)
    return missing, notes, score


def prepare_document(document: TaxDocument) -> TaxDocument:
    missing, notes, score = validate_tax_fields(document)
    document.missing_fields = missing
    document.validation_notes = notes
    document.completeness_score = score
    return document


async def sync_sources() -> int:
    created = 0
    invoice_docs = await db.audit_invoices.find({"status": {"$in": ["sent", "paid", "overdue"]}}).to_list(1000)
    for raw in invoice_docs:
        invoice = Invoice(**raw)
        if await db.audit_tax_documents.find_one({"source_type": "invoice", "source_id": invoice.id}):
            continue
        customer_doc = await db.audit_customers.find_one({"id": invoice.customer_id}) if invoice.customer_id else None
        customer = Customer(**customer_doc) if customer_doc else None
        rate = int(invoice.tax_rate) if int(invoice.tax_rate) in {0, 11, 12} else nearest_rate(invoice.subtotal, invoice.tax)
        dpp = invoice.subtotal or round(invoice.total / (1 + rate / 100), 2)
        vat = invoice.tax if invoice.tax else round(invoice.total - dpp, 2)
        item = TaxDocument(
            source_type="invoice", source_id=invoice.id, direction="output", counterparty=invoice.customer,
            npwp=customer.tax_id if customer else "", source_reference=invoice.number, document_date=invoice.issue_date,
            tax_period=invoice.issue_date[:7], dpp=dpp, tax_rate=rate, vat=vat,
            status_history=[TaxStatusEvent(status="draft", actor="System", note="Disinkronkan dari invoice")],
        )
        item = prepare_document(item)
        try:
            result = await db.audit_tax_documents.update_one(
                {"source_type": "invoice", "source_id": invoice.id},
                {"$setOnInsert": item.model_dump()},
                upsert=True,
            )
        except DuplicateKeyError:
            continue  # a concurrent sync inserted this source first
        if result.upserted_id is not None:
            created += 1
    transaction_docs = await db.audit_transactions.find({"status": "approved", "type": "expense"}).to_list(1000)
    for raw in transaction_docs:
        transaction = Transaction(**raw)
        if await db.audit_tax_documents.find_one({"source_type": "transaction", "source_id": transaction.id}):
            continue
        rate = nearest_rate(transaction.subtotal, transaction.tax)
        item = TaxDocument(
            source_type="transaction", source_id=transaction.id, direction="input", counterparty=transaction.counterparty,
            source_reference=transaction.reference_number, document_date=transaction.transaction_date,
            tax_period=transaction.transaction_date[:7], dpp=transaction.subtotal, tax_rate=rate, vat=transaction.tax,
            status_history=[TaxStatusEvent(status="draft", actor="System", note="Disinkronkan dari transaksi pengeluaran")],
        )
        item = prepare_document(item)
        try:
            result = await db.audit_tax_documents.update_one(
                {"source_type": "transaction", "source_id": transaction.id},
                {"$setOnInsert": item.model_dump()},
                upsert=True,
            )
        except DuplicateKeyError:
            continue  # a concurrent sync inserted this source first
        if result.upserted_id is not None:
            created += 1
    return created


def normalize_period(period: str | None) -> str:
    value = period or today_iso()[:7]
    try:
        date.fromisoformat(value + "-01")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Format masa pajak harus YYYY-MM") from exc
    return value


async def get_period_documents(period: str) -> list[TaxDocument]:
    await sync_sources()
    docs = await db.audit_tax_documents.find({"tax_period": period}).sort("document_date", -1).to_list(2000)
    return [TaxDocument(**doc) for doc in docs]


async def make_summary(period: str) -> TaxSummary:
    documents = await get_period_documents(period)
    output = [item for item in documents if item.direction == "output"]
    inputs = [item for item in documents if item.direction == "input"]
    status_counts: dict[str, int] = {}
    by_rate: list[TaxRateSummary] = []
    for item in documents:
        status_counts[item.status] = status_counts.get(item.status, 0) + 1
    for rate in (0, 11, 12):
        rows = [item for item in documents if item.tax_rate == rate]
        by_rate.append(TaxRateSummary(rate=rate, dpp=sum(item.dpp for item in rows), vat=sum(item.vat for item in rows), document_count=len(rows)))
    output_vat = sum(item.vat for item in output)
    input_vat = sum(item.vat for item in inputs)
    return TaxSummary(
        period=period,
        output_dpp=sum(item.dpp for item in output), output_vat=output_vat,
        input_dpp=sum(item.dpp for item in inputs), input_vat=input_vat,
        net_vat=output_vat - input_vat,
        ready_count=status_counts.get("ready", 0) + status_counts.get("reported", 0),
        issue_count=sum(item.completeness_score < 100 or item.status == "needs_correction" for item in documents),
        status_counts=status_counts, by_rate=by_rate,
    )


@router.get("/profiles", response_model=list[TaxRateProfile])
async def get_tax_profiles() -> list[TaxRateProfile]:
    return RATE_PROFILES


@router.post("/sync", response_model=TaxSyncResult)
async def sync_tax_sources() -> TaxSyncResult:
    created = await sync_sources()
    total = await db.audit_tax_documents.count_documents({})
    return TaxSyncResult(created=created, total=total)


@router.get("/documents", response_model=list[TaxDocument])
async def get_tax_documents(period: str | None = Query(default=None)) -> list[TaxDocument]:
    return await get_period_documents(normalize_period(period))


@router.put("/documents/{document_id}", response_model=TaxDocument)
async def update_tax_document(document_id: str, input: TaxDocumentUpdate) -> TaxDocument:
    raw = await db.audit_tax_documents.find_one({"id": document_id})
    if not raw:
        raise HTTPException(status_code=404, detail="Dokumen pajak tidak ditemukan")
    current = TaxDocument(**raw)
    try:
        date.fromisoformat(input.document_date)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Format tanggal harus YYYY-MM-DD") from exc
    current.npwp = input.npwp
    current.tax_invoice_number = input.tax_invoice_number
    current.document_date = input.document_date
    current.tax_period = input.document_date[:7]
    current.dpp = input.dpp
    current.tax_rate = input.tax_rate
    current.vat = round(input.dpp * input.tax_rate / 100, 2)
    current.updated_at = now_iso()
    if current.status in {"ready", "reported"}:
        current.status = "needs_correction"
        current.status_history.append(TaxStatusEvent(status="needs_correction", actor="System", note="Data diubah setelah siap/dilaporkan"))
    current = prepare_document(current)
    await db.audit_tax_documents.replace_one({"id": document_id}, current.model_dump())
    return current


@router.post("/documents/{document_id}/action", response_model=TaxDocument)
async def transition_tax_document(document_id: str, input: TaxActionRequest) -> TaxDocument:
    raw = await db.audit_tax_documents.find_one({"id": document_id})
    if not raw:
        raise HTTPException(status_code=404, detail="Dokumen pajak tidak ditemukan")
    current = prepare_document(TaxDocument(**raw))
    transitions = {
        ("draft", "submit_review"): "review", ("needs_correction", "submit_review"): "review",
        ("review", "mark_ready"): "ready", ("review", "request_correction"): "needs_correction",
        ("ready", "mark_reported"): "reported", ("ready", "request_correction"): "needs_correction",
    }
    target = transitions.get((current.status, input.action))
    if not target:
        raise HTTPException(status_code=409, detail=f"Aksi {input.action} tidak valid untuk status {current.status}")
    if target == "ready" and current.missing_fields:
        raise HTTPException(status_code=422, detail={"message": "Dokumen belum lengkap", "missing_fields": current.missing_fields})
    current.status = target
    current.updated_at = now_iso()
    current.status_history.append(TaxStatusEvent(status=target, actor=input.actor, note=input.note or f"Status diubah ke {target}"))
    await db.audit_tax_documents.replace_one({"id": document_id}, current.model_dump())
    return current


@router.get("/summary", response_model=TaxSummary)
async def get_tax_summary(period: str | None = Query(default=None)) -> TaxSummary:
    return await make_summary(normalize_period(period))


@router.get("/export.csv")
async def export_tax_csv(period: str | None = Query(default=None)):
    selected_period = normalize_period(period)
    documents = await get_period_documents(selected_period)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Arah", "Sumber", "Referensi", "Pihak", "NPWP", "Nomor Faktur", "Tanggal", "Masa", "DPP", "Tarif", "PPN", "Status", "Kelengkapan"])
    for item in documents:
        writer.writerow([item.direction, item.source_type, item.source_reference, item.counterparty, item.npwp, item.tax_invoice_number, item.document_date, item.tax_period, item.dpp, item.tax_rate, item.vat, item.status, item.completeness_score])
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="auditpro-tax-{selected_period}.csv"'})


@router.get("/export.xlsx")
async def export_tax_xlsx(period: str | None = Query(default=None)):
    selected_period = normalize_period(period)
    documents = await get_period_documents(selected_period)
    summary = await make_summary(selected_period)
    payload = build_tax_xlsx(summary, documents)
    return StreamingResponse(io.BytesIO(payload), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="auditpro-tax-{selected_period}.xlsx"'})


@router.get("/efaktur-preview.csv")
async def export_efaktur_preview(period: str | None = Query(default=None)):
    selected_period = normalize_period(period)
    documents = [item for item in await get_period_documents(selected_period) if item.status in {"ready", "reported"}]
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["FK", "KD_JENIS_TRANSAKSI", "FG_PENGGANTI", "NOMOR_FAKTUR", "MASA_PAJAK", "TAHUN_PAJAK", "TANGGAL_FAKTUR", "NPWP", "NAMA", "JUMLAH_DPP", "JUMLAH_PPN"])
    for item in documents:
        writer.writerow(["FK", "01", "0", item.tax_invoice_number, int(item.tax_period[5:7]), int(item.tax_period[:4]), item.document_date, item.npwp, item.counterparty, item.dpp, item.vat])
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="efaktur-preview-{selected_period}.csv"'})