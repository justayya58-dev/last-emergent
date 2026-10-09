"""Shared export audit logger — records every export activity to audit_exports.
Imported by multiple routers; kept in lib to avoid cross-router circular imports."""

import logging

from lib.db import db
from models.auditpro import ExportLog

logger = logging.getLogger(__name__)


async def log_export(
    export_type: str,
    export_format: str,
    title: str,
    *,
    scope: str = "",
    period_start: str | None = None,
    period_end: str | None = None,
    row_count: int = 0,
    actor: str = "Raka Adinata",
) -> None:
    """Best-effort: never fail an export because its audit write failed."""
    try:
        entry = ExportLog(
            export_type=export_type,
            export_format=export_format,
            title=title,
            scope=scope,
            period_start=period_start,
            period_end=period_end,
            row_count=row_count,
            actor=actor,
        )
        await db.audit_exports.insert_one(entry.model_dump())
    except Exception as exc:
        logger.error("log_export(%s.%s): %s", export_type, export_format, exc)
