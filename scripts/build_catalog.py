"""
Build the combined category catalog CSV from the two source files.

Joins ``tests/data/data_catalog.csv`` with ``tests/data/catalog_ids.csv`` on
``data_catalog.Subcatgoria == catalog_ids."Nome Antigo"`` and writes the result
to ``app/data/catalog.csv``.

Run once and commit the generated file:

    python scripts/build_catalog.py
"""

import csv
import os
import sys


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG_IDS = os.path.join(REPO_ROOT, "tests", "data", "catalog_ids.csv")
DATA_CATALOG = os.path.join(REPO_ROOT, "tests", "data", "data_catalog.csv")
GATEWAY_CATALOG = os.path.join(REPO_ROOT, "tests", "data", "gateway_catalog.csv")
OUTPUT = os.path.join(REPO_ROOT, "app", "data", "catalog.csv")

# Gateway rows have no IDs in the source files, so they are mapped here.
# Keyed by subcategory_name ("Nome Novo").
GATEWAY_CATEGORY_NAME = "HPE SUZANO - GATEWAY"
GATEWAY_CATEGORY_ID = "9206469b-3e39-4ba1-94cc-7b7d9014547a"
GATEWAY_IDS = {
    "VPROBE.THREADPOOL.REJECTED": "21f9053e-9e7d-4900-96a6-d7a61a6e335f",
    "VPROBE.MSG.RECENT.PKT.SENT.TIM": "ccf99f1f-e14a-4bc8-aad8-5ff644bf17a4",
    "VPROBE.MON.RECENT.PKT.SENT.TIM": "7b93391c-e143-4417-9461-2283f514c4b0",
    "SERVICE.STATUS": "ab3b3662-45e7-44f0-84f8-c1883fae4aab",
}

OUTPUT_FIELDS = [
    "monitor_name",
    "metric_name",
    "subcatgoria",
    "category_name",
    "subcategory_name",
    "category_id",
    "subcategory_id",
    "alert_subject",
    "alert_body",
]


def load_catalog_ids(path):
    """Map ``Nome Antigo`` -> category/subcategory names and ids."""
    index = {}
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            key = (row.get("Nome Antigo") or "").strip()
            if not key:
                continue
            entry = {
                "category_name": (row.get("Categoria") or "").strip(),
                "subcategory_name": (row.get("Nome Novo") or "").strip(),
                "category_id": (row.get("ID Categoria") or "").strip(),
                "subcategory_id": (row.get("ID Subcategoria") or "").strip(),
            }
            existing = index.get(key)
            if existing is not None and existing != entry:
                print(
                    f"WARNING: conflicting catalog_ids rows for 'Nome Antigo'='{key}'; keeping first.",
                    file=sys.stderr,
                )
                continue
            index.setdefault(key, entry)
    return index


def build_rows(ids_index, path):
    rows = []
    seen = set()
    matched = 0
    unmatched = 0
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            sub = (row.get("Subcatgoria") or "").strip()
            ids = ids_index.get(sub)
            if ids is None:
                unmatched += 1
                continue
            matched += 1
            out = {
                "monitor_name": (row.get("Monitor_Name") or "").strip(),
                "metric_name": (row.get("Metric_Name") or "").strip(),
                "subcatgoria": sub,
                "category_name": ids["category_name"],
                "subcategory_name": ids["subcategory_name"],
                "category_id": ids["category_id"],
                "subcategory_id": ids["subcategory_id"],
                "alert_subject": (row.get("Alert Subject") or "").strip(),
                "alert_body": (row.get("Alert Body") or "").strip(),
            }
            dedupe_key = tuple(out[field] for field in OUTPUT_FIELDS)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            rows.append(out)
    return rows, matched, unmatched


def build_gateway_rows(ids_index, path):
    """
    Build catalog rows from the gateway file, which lacks IDs.

    The subcategory_name ("Nome Novo") is resolved via catalog_ids (Nome Antigo
    == Subcatgoria); the IDs come from the embedded GATEWAY_IDS map.
    """
    rows = []
    if not os.path.exists(path):
        print(f"WARNING: gateway catalog not found at {path}, skipping.", file=sys.stderr)
        return rows

    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            # The gateway file uses the correct spelling "Subcategoria";
            # data_catalog uses the misspelled "Subcatgoria". Accept both.
            sub = (row.get("Subcategoria") or row.get("Subcatgoria") or "").strip()
            if not sub:
                continue
            ids = ids_index.get(sub)
            subcategory_name = ids["subcategory_name"] if ids else sub.upper()
            subcategory_id = GATEWAY_IDS.get(subcategory_name)
            if not subcategory_id:
                print(
                    f"WARNING: no Gateway ID mapping for subcategory '{subcategory_name}' "
                    f"(Subcatgoria='{sub}'), skipping.",
                    file=sys.stderr,
                )
                continue
            rows.append(
                {
                    "monitor_name": (row.get("Monitor_Name") or "").strip(),
                    "metric_name": (row.get("Metric_Name") or "").strip(),
                    "subcatgoria": sub,
                    "category_name": GATEWAY_CATEGORY_NAME,
                    "subcategory_name": subcategory_name,
                    "category_id": GATEWAY_CATEGORY_ID,
                    "subcategory_id": subcategory_id,
                    "alert_subject": (row.get("Alert Subject") or "").strip(),
                    "alert_body": (row.get("Alert Body") or "").strip(),
                }
            )
    return rows


def main():
    ids_index = load_catalog_ids(CATALOG_IDS)
    rows, matched, unmatched = build_rows(ids_index, DATA_CATALOG)

    gateway_rows = build_gateway_rows(ids_index, GATEWAY_CATALOG)
    existing = {tuple(r[field] for field in OUTPUT_FIELDS) for r in rows}
    for row in gateway_rows:
        key = tuple(row[field] for field in OUTPUT_FIELDS)
        if key not in existing:
            existing.add(key)
            rows.append(row)

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)

    print(
        f"Wrote {len(rows)} unique rows to {OUTPUT} "
        f"(matched={matched}, unmatched={unmatched}, gateway={len(gateway_rows)})."
    )


if __name__ == "__main__":
    main()
