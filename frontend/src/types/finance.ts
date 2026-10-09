export type TransactionStatus = "draft" | "review" | "approved" | "rejected";
export type TransactionAction = "submit" | "approve" | "reject";

export interface AuditEvent {
  action: "created" | "ocr_extracted" | "submitted" | "approved" | "rejected";
  actor: string;
  timestamp: string;
  note: string;
}

export interface TransactionCreate {
  type: "income" | "expense";
  transaction_date?: string | null;
  counterparty: string;
  reference_number: string;
  description: string;
  category: string;
  subtotal: number;
  tax: number;
  total: number;
}

export interface TransactionActionRequest {
  action: TransactionAction;
  actor: string;
  note: string;
}

export interface Transaction {
  id: string;
  source: "manual" | "ocr" | "invoice";
  document_id: string | null;
  type: "income" | "expense";
  transaction_date: string;
  counterparty: string;
  reference_number: string;
  description: string;
  category: string;
  subtotal: number;
  tax: number;
  total: number;
  status: TransactionStatus;
  duplicate_suspected: boolean;
  duplicate_of: string | null;
  created_at: string;
  updated_at: string;
  audit_trail: AuditEvent[];
}

export interface ReportCategory {
  category: string;
  income: number;
  expense: number;
}

export interface ReportSummary {
  period_start: string;
  period_end: string;
  sales_total: number;
  expense_total: number;
  net_profit: number;
  receivables: number;
  tax_collected: number;
  tax_paid: number;
  approved_count: number;
  pending_count: number;
  categories: ReportCategory[];
}

export interface ExportLog {
  id: string;
  export_type: string;
  export_format: "pdf" | "xlsx" | "csv";
  title: string;
  scope: string;
  period_start: string | null;
  period_end: string | null;
  row_count: number;
  actor: string;
  created_at: string;
}