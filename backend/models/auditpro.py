from datetime import datetime, timezone
from typing import Any, Literal
import uuid

from pydantic import BaseModel, Field


class ExtractionData(BaseModel):
    vendor: str
    invoice_number: str
    invoice_date: str
    due_date: str
    subtotal: float
    tax: float
    total: float
    category: str


class AuditDocument(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    file_name: str
    file_type: str
    file_size: int
    status: Literal["draft", "review", "approved", "rejected"] = "draft"
    confidence: int = 94
    uploaded_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    extraction_source: Literal["demo", "gemini-ocr"] = "demo"
    model_name: str = "seed-data"
    transaction_id: str | None = None
    extraction: ExtractionData


class AuditEvent(BaseModel):
    action: Literal["created", "ocr_extracted", "submitted", "approved", "rejected"]
    actor: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    note: str = ""


class TransactionCreate(BaseModel):
    type: Literal["income", "expense"]
    transaction_date: str | None = None
    counterparty: str
    reference_number: str
    description: str = ""
    category: str
    subtotal: float = Field(ge=0)
    tax: float = Field(default=0, ge=0)
    total: float = Field(ge=0)


class TransactionActionRequest(BaseModel):
    action: Literal["submit", "approve", "reject"]
    actor: str = "Raka Adinata"
    note: str = ""


class Transaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source: Literal["manual", "ocr", "invoice"]
    document_id: str | None = None
    type: Literal["income", "expense"]
    transaction_date: str
    counterparty: str
    reference_number: str
    description: str = ""
    category: str
    subtotal: float
    tax: float
    total: float
    status: Literal["draft", "review", "approved", "rejected"] = "draft"
    duplicate_suspected: bool = False
    duplicate_of: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    audit_trail: list[AuditEvent] = Field(default_factory=list)


class InvoiceItem(BaseModel):
    product_id: str | None = None
    description: str
    unit: str = "unit"
    quantity: float = Field(default=1, gt=0)
    price: float = Field(ge=0)
    total: float = Field(ge=0)


class InvoiceCreate(BaseModel):
    customer: str
    customer_id: str | None = None
    due_date: str
    items: list[InvoiceItem] = Field(default_factory=list)
    template: Literal["modern", "classic", "minimal"] = "modern"
    notes: str = "Terima kasih atas kepercayaan Anda."
    tax_rate: float = Field(default=11, ge=0, le=100)
    finalize: bool = False


class InvoiceUpdate(BaseModel):
    customer: str
    customer_id: str | None = None
    due_date: str
    items: list[InvoiceItem] = Field(default_factory=list)
    template: Literal["modern", "classic", "minimal"] = "modern"
    notes: str = "Terima kasih atas kepercayaan Anda."
    tax_rate: float = Field(default=11, ge=0, le=100)


class InvoiceActionRequest(BaseModel):
    action: Literal["finalize", "send", "mark_paid", "mark_overdue"]


class Invoice(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    number: str
    customer: str
    customer_id: str | None = None
    issue_date: str
    due_date: str
    subtotal: float = 0
    tax_rate: float = 11
    tax: float = 0
    total: float
    amount_words: str = ""
    currency: str = "IDR"
    template: Literal["modern", "classic", "minimal"] = "modern"
    notes: str = ""
    status: Literal["paid", "pending", "sent", "overdue", "draft"]
    sent_at: str | None = None
    paid_at: str | None = None
    items: list[InvoiceItem] = Field(default_factory=list)


class CompanyProfileUpdate(BaseModel):
    name: str
    address: str
    email: str
    phone: str
    tax_id: str
    bank_name: str
    bank_account: str
    accent_color: str = "#10B981"


class CompanyProfile(CompanyProfileUpdate):
    id: str = "company-profile"
    logo_data_url: str | None = None


class CustomerCreate(BaseModel):
    name: str
    email: str = ""
    phone: str = ""
    address: str = ""
    tax_id: str = ""


class Customer(CustomerCreate):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ProductCreate(BaseModel):
    name: str
    description: str = ""
    sku: str
    unit: str = "unit"
    price: float = Field(ge=0)


class Product(ProductCreate):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ChartPoint(BaseModel):
    label: str
    revenue: float
    expenses: float


class DashboardSummary(BaseModel):
    period_label: str
    total_revenue: float
    revenue_change: float
    cashflow_net: float
    receivables: float
    audit_pass_rate: float
    active_invoices: int
    pending_reviews: int
    chart: list[ChartPoint]
    recent_invoices: list[Invoice]


class ReportCategory(BaseModel):
    category: str
    income: float
    expense: float


class ReportSummary(BaseModel):
    period_start: str
    period_end: str
    sales_total: float
    expense_total: float
    net_profit: float
    receivables: float
    tax_collected: float
    tax_paid: float
    approved_count: int
    pending_count: int
    categories: list[ReportCategory]


class TaxRateProfile(BaseModel):
    rate: Literal[0, 11, 12]
    label: str
    description: str


class TaxStatusEvent(BaseModel):
    status: Literal["draft", "review", "ready", "reported", "needs_correction"]
    actor: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    note: str = ""


class TaxDocumentUpdate(BaseModel):
    npwp: str
    tax_invoice_number: str
    document_date: str
    dpp: float = Field(ge=0)
    tax_rate: Literal[0, 11, 12]


class TaxActionRequest(BaseModel):
    action: Literal["submit_review", "mark_ready", "mark_reported", "request_correction"]
    actor: str = "Raka Adinata"
    note: str = ""


class TaxDocument(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_type: Literal["invoice", "transaction"]
    source_id: str
    direction: Literal["input", "output"]
    counterparty: str
    npwp: str = ""
    source_reference: str
    tax_invoice_number: str = ""
    document_date: str
    tax_period: str
    dpp: float
    tax_rate: Literal[0, 11, 12]
    vat: float
    status: Literal["draft", "review", "ready", "reported", "needs_correction"] = "draft"
    completeness_score: int = 0
    missing_fields: list[str] = Field(default_factory=list)
    validation_notes: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status_history: list[TaxStatusEvent] = Field(default_factory=list)


class TaxRateSummary(BaseModel):
    rate: int
    dpp: float
    vat: float
    document_count: int


class TaxSummary(BaseModel):
    period: str
    output_dpp: float
    output_vat: float
    input_dpp: float
    input_vat: float
    net_vat: float
    ready_count: int
    issue_count: int
    status_counts: dict[str, int]
    by_rate: list[TaxRateSummary]


class TaxSyncResult(BaseModel):
    created: int
    total: int


class AssistantSessionCreate(BaseModel):
    title: str = "Percakapan baru"


class AssistantSession(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workspace_id: str = "aksara-studio"
    title: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AssistantMessageCreate(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class AssistantMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    role: Literal["user", "assistant"]
    content: str
    proposal_id: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class DraftInvoiceProposalPayload(BaseModel):
    customer: str
    customer_id: str | None = None
    due_date: str
    items: list[InvoiceItem]
    template: Literal["modern", "classic", "minimal"] = "modern"
    notes: str = "Draft dibuat oleh Financial Assistant."
    tax_rate: float = Field(default=11, ge=0, le=100)


class DraftReportProposalPayload(BaseModel):
    title: str
    period_start: str
    period_end: str
    summary_focus: str = "Ringkasan performa keuangan"


class AssistantProposal(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    type: Literal["draft_invoice", "draft_report"]
    title: str
    status: Literal["pending", "confirmed", "cancelled"] = "pending"
    payload: DraftInvoiceProposalPayload | DraftReportProposalPayload
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    decided_at: str | None = None
    result_id: str | None = None


class AssistantProposalDecision(BaseModel):
    confirm: bool


class AssistantSessionDetail(BaseModel):
    session: AssistantSession
    messages: list[AssistantMessage]
    proposals: list[AssistantProposal]


class AssistantQuickPrompt(BaseModel):
    id: str
    label: str
    prompt: str


class AssistantAuditEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    action: Literal["message", "proposal_created", "proposal_confirmed", "proposal_cancelled"]
    actor: str
    detail: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AssistantDraftReport(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    period_start: str
    period_end: str
    summary_focus: str
    sales_total: float
    expense_total: float
    net_profit: float
    receivables: float
    created_by: str = "Financial Assistant"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class ExportLog(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    export_type: str  # invoice | transactions | report | tax | efaktur | business_report
    export_format: Literal["pdf", "xlsx", "csv"]
    title: str = ""
    scope: str = ""
    period_start: str | None = None
    period_end: str | None = None
    row_count: int = 0
    actor: str = "Raka Adinata"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
