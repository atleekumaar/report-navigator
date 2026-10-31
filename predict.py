#!/usr/bin/env python3
"""
predict.py — Competition entry point for P5 Report Navigator.

Usage:
    python predict.py --pdf {pdf_path} --questions {questions_jsonl} --output {answers_jsonl}

Features:
- Fast runtime indexing (< 3 seconds)
- 100% offline (no network calls)
- Zero memory leakage
- Exactly matches competition schema:
    {"id": "P000", "answer": "351", "page": 101, "confidence": 0.95}
    {"id": "P011", "answer": "NOT_FOUND", "page": null, "confidence": 0.95}
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.solver import DynamicReportSolver


def main():
    parser = argparse.ArgumentParser(description="Report Navigator — P5 Competition Entry Point")
    parser.add_argument("--pdf", required=True, help="Path to the PDF report")
    parser.add_argument("--questions", required=True, help="Path to questions JSONL")
    parser.add_argument("--output", required=True, help="Path to output answers JSONL")
    parser.add_argument("--data-dir", default=None, help="Optional data directory (for compatibility)")
    parser.add_argument("--grid", default=None, help="Optional grid argument (for compatibility)")
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    questions_path = Path(args.questions)
    output_path = Path(args.output)

    if not pdf_path.exists():
        print(f"[ERROR] PDF file not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)
    if not questions_path.exists():
        print(f"[ERROR] Questions file not found: {questions_path}", file=sys.stderr)
        sys.exit(1)

    t0 = time.time()
    print(f"[predict] Initializing DynamicReportSolver on {pdf_path.name}...")
    solver = DynamicReportSolver(str(pdf_path))
    t_index = time.time() - t0
    print(f"[predict] Document indexed ({solver.page_count} pages) in {t_index:.2f}s.")

    # Load questions
    questions = []
    with open(questions_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                questions.append(json.loads(line))

    print(f"[predict] Answering {len(questions)} questions...")
    answers = []

    for q in questions:
        qid = q["id"]
        question_text = q["question"]
        qtype = q.get("qtype")
        res = solver.solve(qid=qid, question=question_text, qtype=qtype)

        answers.append({
            "id": res.qid,
            "answer": res.answer,
            "page": res.page,
            "confidence": round(res.confidence, 4)
        })

    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for a in answers:
            f.write(json.dumps(a, ensure_ascii=False) + "\n")

    t_total = time.time() - t0
    print(f"[predict] Complete! {len(answers)} answers written to {output_path} in {t_total:.2f}s.")


if __name__ == "__main__":
    main()
