import json
from pathlib import Path
from typing import Dict, Any, List
import config
from qa import QAEngine

def run_evaluation(eval_file: Path = Path("eval_questions.jsonl")):
    if not eval_file.exists():
        print(f"Eval file {eval_file} not found.")
        return

    questions: List[Dict[str, Any]] = []
    with open(eval_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                questions.append(json.loads(line))

    print(f"\n================ Running Evaluation ({len(questions)} questions) ================")
    engine = QAEngine()

    total = len(questions)
    answerable_total = 0
    unanswerable_total = 0

    retrieval_hits = 0
    citation_page_hits = 0
    answer_correctness_hits = 0
    abstention_hits = 0

    for idx, item in enumerate(questions, 1):
        q = item["question"]
        is_answerable = item.get("answerable", True)
        exp_pages = item.get("expected_pages", [])
        exp_contains = item.get("expected_contains", [])

        print(f"\n[{idx}/{total}] Q: {q}")
        res = engine.answer(query=q)

        found = res.get("found", False)
        answer_text = res.get("answer", "")
        citations = res.get("citations", [])
        retrieved_pages = [s.get("page") for s in res.get("retrieval_trace", {}).get("top_sources", [])]
        cited_pages = [c.get("page") for c in citations if c.get("verified")]

        if not is_answerable:
            unanswerable_total += 1
            if not found or "not found" in answer_text.lower():
                abstention_hits += 1
                print("  -> Abstention Check: PASS (Correctly abstained)")
            else:
                print("  -> Abstention Check: FAIL (Model hallucinated or guessed)")
        else:
            answerable_total += 1
            # Retrieval hit@8 check
            hit_retrieval = any(p in retrieved_pages for p in exp_pages)
            if hit_retrieval:
                retrieval_hits += 1
                print("  -> Retrieval Hit@8: PASS")
            else:
                print(f"  -> Retrieval Hit@8: FAIL (Expected {exp_pages}, got {retrieved_pages})")

            # Citation page accuracy check
            hit_citation = any(p in cited_pages for p in exp_pages)
            if hit_citation:
                citation_page_hits += 1
                print("  -> Citation Page: PASS")
            else:
                print(f"  -> Citation Page: FAIL (Cited pages {cited_pages})")

            # Content substring check
            hit_content = all(sub.lower() in answer_text.lower() for sub in exp_contains) if exp_contains else True
            if hit_content:
                answer_correctness_hits += 1
                print("  -> Answer Correctness: PASS")
            else:
                print(f"  -> Answer Correctness: FAIL (Missing expected substrings: {exp_contains})")

    print("\n" + "=" * 50)
    print("                 EVALUATION SUMMARY")
    print("=" * 50)
    if answerable_total > 0:
        print(f"Retrieval Hit@8 Rate       : {retrieval_hits}/{answerable_total} ({retrieval_hits / answerable_total * 100:.1f}%)")
        print(f"Citation Page Accuracy     : {citation_page_hits}/{answerable_total} ({citation_page_hits / answerable_total * 100:.1f}%)")
        print(f"Answer Correctness Rate    : {answer_correctness_hits}/{answerable_total} ({answer_correctness_hits / answerable_total * 100:.1f}%)")
    if unanswerable_total > 0:
        print(f"Abstention Accuracy        : {abstention_hits}/{unanswerable_total} ({abstention_hits / unanswerable_total * 100:.1f}%)")
    print("=" * 50)

if __name__ == "__main__":
    run_evaluation()
