#!/usr/bin/env python3
"""
train.py — Required by competition rules.

For P5 Report Navigator, there is no offline model fine-tuning step needed —
the system dynamically builds its indexes at runtime directly from the target PDF.
This script validates that the pipeline and table discovery execute cleanly on the data.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.solver import DynamicReportSolver


def main():
    parser = argparse.ArgumentParser(description="Report Navigator — train (runtime validation)")
    parser.add_argument("--data-dir", default="data", help="Directory containing report PDFs")
    parser.add_argument("--out", default="models/", help="Output directory for metadata marker")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Prefer report_A.pdf if available
    pdf = data_dir / "report_A.pdf"
    if not pdf.exists():
        pdfs = list(data_dir.glob("*.pdf"))
        if not pdfs:
            print("[train] No PDFs found in data directory.", file=sys.stderr)
            sys.exit(0)
        pdf = pdfs[0]

    print(f"[train] Validating pipeline with {pdf.name}...")
    solver = DynamicReportSolver(str(pdf))

    print(f"[train] Document indexed ({solver.page_count} pages).")
    print(f"[train] Discovered tables: {solver.table_pages}")

    # Write confirmation marker to out_dir
    marker = out_dir / "validated.json"
    marker.write_text(json.dumps({
        "pdf": pdf.name,
        "pages": solver.page_count,
        "table_pages": solver.table_pages,
        "status": "READY"
    }, indent=2))

    print(f"[train] Validation complete! Marker written to {marker}")


if __name__ == "__main__":
    main()
