#!/usr/bin/env python3
"""
eval.py — Evaluate predicted answers against gold standard.

Computes the P5 competition metrics:
  Score = 0.75 * EM + 0.25 * CitationAcc

Usage:
    python eval.py --gold data/questions_with_answers.jsonl --pred data/predicted_answers.jsonl
    python eval.py   # uses defaults
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load_jsonl(path: Path) -> list[dict]:
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def normalise_answer(ans: str) -> str:
    """Strip commas, spaces, leading zeros for comparison."""
    s = str(ans).strip().replace(",", "").replace(" ", "")
    if s.upper() == "NOT_FOUND":
        return "NOT_FOUND"
    # Remove leading zeros but keep "0"
    try:
        return str(int(s))
    except ValueError:
        return s


def evaluate(gold_path: Path, pred_path: Path) -> dict:
    gold_items = load_jsonl(gold_path)
    pred_items = load_jsonl(pred_path)

    gold_by_id = {g["id"]: g for g in gold_items}
    pred_by_id = {p["id"]: p for p in pred_items}

    total = len(gold_items)
    em_correct = 0
    cit_correct = 0
    hallucinations = 0
    abstentions = 0
    answerable_answered = 0
    total_answerable = 0
    total_unanswerable = 0

    details = []

    for g in gold_items:
        qid = g["id"]
        gold_ans = normalise_answer(g["answer"])
        gold_pages = g.get("gold_pages", [])
        is_unanswerable = (gold_ans == "NOT_FOUND")

        pred = pred_by_id.get(qid)
        if pred is None:
            details.append({
                "id": qid, "status": "MISSING",
                "gold": gold_ans, "pred": "---", "em": False, "cit": False,
            })
            continue

        pred_ans = normalise_answer(pred.get("answer", ""))
        pred_page = pred.get("page")

        # Exact match
        em = (pred_ans == gold_ans)
        if em:
            em_correct += 1

        # Citation accuracy
        if is_unanswerable:
            total_unanswerable += 1
            cit = (pred_ans == "NOT_FOUND")
            if pred_ans != "NOT_FOUND":
                hallucinations += 1
        else:
            total_answerable += 1
            cit = (pred_page in gold_pages) if gold_pages else False
            if pred_ans != "NOT_FOUND":
                answerable_answered += 1
            else:
                abstentions += 1

        if cit:
            cit_correct += 1

        details.append({
            "id": qid,
            "question": g.get("question", "")[:60],
            "gold": gold_ans,
            "pred": pred_ans,
            "gold_pages": gold_pages,
            "pred_page": pred_page,
            "em": em,
            "cit": cit,
        })

    em_rate = em_correct / total if total else 0
    cit_rate = cit_correct / total if total else 0
    score = 0.75 * em_rate + 0.25 * cit_rate
    hallucination_rate = hallucinations / total_unanswerable if total_unanswerable else 0
    answerable_recall = answerable_answered / total_answerable if total_answerable else 0

    return {
        "total": total,
        "em_correct": em_correct,
        "em_rate": em_rate,
        "cit_correct": cit_correct,
        "cit_rate": cit_rate,
        "score": score,
        "hallucination_rate": hallucination_rate,
        "answerable_recall": answerable_recall,
        "abstentions": abstentions,
        "details": details,
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate P5 Report Navigator answers")
    parser.add_argument("--gold", default="data/questions_with_answers.jsonl",
                        help="Path to gold-standard questions JSONL")
    parser.add_argument("--pred", default="data/predicted_answers.jsonl",
                        help="Path to predicted answers JSONL")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Print per-question details")
    args = parser.parse_args()

    gold_path = Path(args.gold)
    pred_path = Path(args.pred)

    if not gold_path.exists():
        print(f"[ERROR] Gold file not found: {gold_path}", file=sys.stderr)
        sys.exit(1)
    if not pred_path.exists():
        print(f"[ERROR] Predictions file not found: {pred_path}", file=sys.stderr)
        sys.exit(1)

    result = evaluate(gold_path, pred_path)

    print("=" * 60)
    print(f"  P5 Report Navigator — Evaluation Results")
    print("=" * 60)
    print(f"  Total questions:      {result['total']}")
    print(f"  Exact Match (EM):     {result['em_correct']}/{result['total']}  ({result['em_rate']*100:.1f}%)")
    print(f"  Citation Accuracy:    {result['cit_correct']}/{result['total']}  ({result['cit_rate']*100:.1f}%)")
    print(f"  ---")
    print(f"  Combined Score:       {result['score']:.4f}")
    print(f"    (= 0.75 x {result['em_rate']:.4f} + 0.25 x {result['cit_rate']:.4f})")
    print(f"  ---")
    print(f"  Hallucination rate:   {result['hallucination_rate']*100:.1f}%")
    print(f"  Answerable recall:    {result['answerable_recall']*100:.1f}%")
    print(f"  Abstentions:          {result['abstentions']}")
    print("=" * 60)

    # Score bands
    score = result["score"]
    if score >= 0.82:
        band = "EXCELLENT (full points)"
    elif score >= 0.60:
        band = "GOOD"
    elif score >= 0.30:
        band = "ABOVE LAZY"
    else:
        band = "LAZY / BELOW"
    print(f"  Band: {band}")
    print(f"  A1 normalised points: {max(0, min(45, 45 * (score - 0.24) / (0.82 - 0.24))):.1f} / 45")
    print("=" * 60)

    if args.verbose:
        print("\n--- Per-question details ---")
        for d in result["details"]:
            em_sym = "OK" if d["em"] else "XX"
            cit_sym = "OK" if d["cit"] else "XX"
            print(f"  [{em_sym}/{cit_sym}] {d['id']}: "
                  f"pred={d['pred']} gold={d['gold']} "
                  f"(pp={d.get('pred_page','?')} gp={d.get('gold_pages',[])})")

    return result


if __name__ == "__main__":
    main()
