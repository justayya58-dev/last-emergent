"""Read-only preflight for legacy documents before unique indexes are enforced.

Run from backend/ against a restored staging copy:
    python scripts/preflight_legacy_migration.py

This script reports duplicate groups only. It never deletes or modifies documents.
"""
import asyncio
import json

from lib.db import INDEXES, client, db


async def main() -> int:
    findings = []
    for collection_name, models in INDEXES.items():
        collection = db[collection_name]
        for model in models:
            spec = model.document
            if not spec.get("unique", False):
                continue
            key_fields = [field for field, _direction in spec["key"]]
            group_key = {field: f"${field}" for field in key_fields}
            pipeline = [
                {"$group": {"_id": group_key, "count": {"$sum": 1}}},
                {"$match": {"count": {"$gt": 1}}},
                {"$limit": 20},
            ]
            groups = await collection.aggregate(pipeline).to_list(length=20)
            if groups:
                findings.append({
                    "collection": collection_name,
                    "index": spec.get("name", "unnamed"),
                    "key_fields": key_fields,
                    "duplicate_groups_sampled": len(groups),
                    "sample_counts": [group["count"] for group in groups[:5]],
                    "truncated_at_20": len(groups) == 20,
                })

    if findings:
        print(json.dumps({"status": "BLOCKED", "duplicate_indexes": findings}, indent=2))
        print("Resolve duplicates with an approved, backed-up migration; no data was changed.")
        return 1

    print(json.dumps({
        "status": "READY_FOR_INDEX_REVIEW",
        "unique_indexes_checked": sum(
            1 for models in INDEXES.values() for model in models
            if model.document.get("unique", False)
        ),
        "note": "Read-only duplicate scan only; this is not a complete migration or backup verification."
    }, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    finally:
        client.close()
