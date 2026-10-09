export type InvoiceTemplate = "modern" | "classic" | "minimal";
export type InvoiceStatus = "paid" | "pending" | "sent" | "overdue" | "draft";

export interface InvoiceItem {
  product_id: string | null;
  description: string;
  unit: string;
  quantity: number;
  price: number;
  total: number;
}

export interface InvoiceCreate {
  customer: string;
  customer_id: string | null;
  due_date: string;
  items: InvoiceItem[];
  template: InvoiceTemplate;
  notes: string;
  tax_rate: number;
  finalize: boolean;
}

export interface InvoiceUpdate {
  customer: string;
  customer_id: string | null;
  due_date: string;
  items: InvoiceItem[];
  template: InvoiceTemplate;
  notes: string;
  tax_rate: number;
}

export interface InvoiceActionRequest {
  action: "finalize" | "send" | "mark_paid" | "mark_overdue";
}

export interface Invoice {
  id: string;
  number: string;
  customer: string;
  customer_id: string | null;
  issue_date: string;
  due_date: string;
  subtotal: number;
  tax_rate: number;
  tax: number;
  total: number;
  amount_words: string;
  currency: string;
  template: InvoiceTemplate;
  notes: string;
  status: InvoiceStatus;
  sent_at: string | null;
  paid_at: string | null;
  items: InvoiceItem[];
}

export interface CompanyProfileUpdate {
  name: string;
  address: string;
  email: string;
  phone: string;
  tax_id: string;
  bank_name: string;
  bank_account: string;
  accent_color: string;
}

export interface CompanyProfile extends CompanyProfileUpdate {
  id: string;
  logo_data_url: string | null;
}

export interface CustomerCreate {
  name: string;
  email: string;
  phone: string;
  address: string;
  tax_id: string;
}

export interface Customer extends CustomerCreate {
  id: string;
  created_at: string;
}

export interface ProductCreate {
  name: string;
  description: string;
  sku: string;
  unit: string;
  price: number;
}

export interface Product extends ProductCreate {
  id: string;
  created_at: string;
}