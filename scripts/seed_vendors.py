"""Seed the vendor history table from invoices.jsonl.

Groups invoices by `provider_id` and upserts one vendor per group with the
most-common bank account, the mean total as `avg_amount`, the latest
`invoice_date` as `last_seen`, and a metadata blob carrying provenance.

Usage:
    python scripts/seed_vendors.py [--path invoices.jsonl.txt]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

# Ensure src/ is importable when run from the repo root.
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cyber_agent.data.watsonx_data import upsert_vendor  # noqa: E402


SUPPLIER_HANDLE_LEN = 8  # short slice of provider_id keeps IDs typeable for agents


def _supplier_id(provider_id: str) -> str:
    return f"vendor-{provider_id[:SUPPLIER_HANDLE_LEN]}"


def seed(path: Path) -> int:
    if not path.exists():
        raise SystemExit(f"invoices file not found: {path}")

    grouped: dict[str, list[dict]] = defaultdict(list)
    with path.open("r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                print(f"skipping line {line_no}: {exc}", file=sys.stderr)
                continue
            pid = row.get("provider_id")
            if not pid:
                continue
            grouped[pid].append(row)

    written = 0
    for pid, invoices in grouped.items():
        banks = [inv.get("bank_account") for inv in invoices if inv.get("bank_account")]
        totals = [inv.get("total") for inv in invoices if isinstance(inv.get("total"), (int, float))]
        dates = [inv.get("invoice_date") for inv in invoices if inv.get("invoice_date")]
        countries = sorted({inv.get("country") for inv in invoices if inv.get("country")})
        fraud_count = sum(1 for inv in invoices if inv.get("is_fraud"))

        bank_account = Counter(banks).most_common(1)[0][0] if banks else None
        avg_amount = round(mean(totals), 2) if totals else None
        last_seen = max(dates) if dates else None

        upsert_vendor(
            supplier_id=_supplier_id(pid),
            bank_account=bank_account,
            avg_amount=avg_amount,
            last_seen=last_seen,
            metadata={
                "provider_id": pid,
                "countries": countries,
                "invoice_count": len(invoices),
                "fraud_count": fraud_count,
            },
        )
        written += 1

    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--path",
        type=Path,
        default=ROOT / "invoices.jsonl.txt",
        help="Path to the JSONL invoices fixture (default: ./invoices.jsonl.txt).",
    )
    args = parser.parse_args()
    count = seed(args.path)
    print(f"seeded {count} vendors from {args.path}")


if __name__ == "__main__":
    main()
