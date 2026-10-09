"""Shared Mongo handle — import `client`/`db` from here (server.py, routers, seed.py)."""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING, IndexModel

load_dotenv(Path(__file__).parent.parent / ".env")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

logger = logging.getLogger(__name__)

# One entry per collection: every field a route filters, sorts, or dedupes on. Applied by ensure_indexes() at startup.
INDEXES: dict[str, list[IndexModel]] = {
    "status_checks": [IndexModel([("timestamp", DESCENDING)], name="timestamp_desc")],
    "audit_documents": [IndexModel([("uploaded_at", DESCENDING)], name="uploaded_at_desc")],
    "audit_invoices": [
        IndexModel([("id", ASCENDING)], name="invoice_id", unique=True),
        IndexModel([("number", ASCENDING)], name="invoice_number", unique=True),
        IndexModel([("issue_date", DESCENDING)], name="issue_date_desc"),
    ],
    "audit_customers": [IndexModel([("id", ASCENDING)], name="customer_id", unique=True), IndexModel([("name", ASCENDING)], name="customer_name")],
    "audit_products": [IndexModel([("id", ASCENDING)], name="product_id", unique=True), IndexModel([("sku", ASCENDING)], name="product_sku", unique=True)],
    "audit_transactions": [
        IndexModel([("id", ASCENDING)], name="transaction_id", unique=True),
        IndexModel([("status", ASCENDING), ("transaction_date", DESCENDING)], name="status_transaction_date"),
        IndexModel([("reference_number", ASCENDING), ("total", ASCENDING)], name="reference_total"),
        IndexModel([("created_at", DESCENDING)], name="created_at_desc"),
    ],
    "audit_tax_documents": [
        IndexModel([("id", ASCENDING)], name="tax_document_id", unique=True),
        IndexModel([("source_type", ASCENDING), ("source_id", ASCENDING)], name="tax_source", unique=True),
        IndexModel([("tax_period", ASCENDING), ("status", ASCENDING)], name="tax_period_status"),
    ],
    "assistant_sessions": [IndexModel([("id", ASCENDING)], name="assistant_session_id", unique=True), IndexModel([("updated_at", DESCENDING)], name="assistant_session_updated")],
    "assistant_messages": [IndexModel([("session_id", ASCENDING), ("created_at", ASCENDING)], name="assistant_message_thread")],
    "assistant_proposals": [IndexModel([("id", ASCENDING)], name="assistant_proposal_id", unique=True), IndexModel([("session_id", ASCENDING), ("created_at", DESCENDING)], name="assistant_proposal_thread")],
    "assistant_audit": [IndexModel([("session_id", ASCENDING), ("timestamp", DESCENDING)], name="assistant_audit_thread")],
    "audit_exports": [IndexModel([("created_at", DESCENDING)], name="export_created_desc")],
}


async def ensure_indexes() -> None:
    for collection, models in INDEXES.items():
        for model in models:  # one at a time so a bad spec skips only itself
            try:
                await db[collection].create_indexes([model])
            except Exception as exc:  # never block boot on an index; the log line names what to fix
                logger.error("ensure_indexes(%s.%s): %s", collection, model.document["name"], exc)
