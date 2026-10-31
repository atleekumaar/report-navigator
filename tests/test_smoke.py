"""
test_smoke.py — Automated smoke test checked by the competition evaluator.
Validates that predict.py can execute on sample input and produce valid JSONL.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path
import pytest


def _run_predict_and_validate(pdf_path: Path, questions_path: Path):
    repo_root = Path(__file__).resolve().parent.parent
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as tmp_out:
        out_path = Path(tmp_out.name)

    try:
        cmd = [
            sys.executable,
            str(repo_root / "predict.py"),
            "--pdf", str(pdf_path),
            "--questions", str(questions_path),
            "--output", str(out_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        assert result.returncode == 0, f"predict.py failed: {result.stderr}"

        lines = [line.strip() for line in out_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        assert len(lines) > 0, "No answers output by predict.py"

        for line in lines[:10]:
            item = json.loads(line)
            assert "id" in item, "Missing 'id' field in answer"
            assert "answer" in item, "Missing 'answer' field in answer"
            assert "page" in item, "Missing 'page' field in answer"
            assert "confidence" in item, "Missing 'confidence' field in answer"
            assert isinstance(item["confidence"], (int, float)), "Confidence must be a number"
            assert 0.0 <= item["confidence"] <= 1.0, "Confidence out of bounds"
            if item["answer"] != "NOT_FOUND":
                assert item["answer"].isdigit(), f"Answer must be digits only: {item['answer']}"
                assert isinstance(item["page"], int), "Page must be integer for answered queries"

        return len(lines)
    finally:
        if out_path.exists():
            out_path.unlink()


def test_smoke():
    """Smoke test running on the synthetic test fixture report."""
    repo_root = Path(__file__).resolve().parent.parent
    pdf_path = repo_root / "data" / "report.pdf"
    if not pdf_path.exists():
        from create_sample_report import generate_sample_pdf
        generate_sample_pdf(pdf_path)

    questions_path = repo_root / "data" / "sample_questions.jsonl"
    if not questions_path.exists():
        questions_path = repo_root / "data" / "questions_with_answers.jsonl"

    count = _run_predict_and_validate(pdf_path, questions_path)
    print(f"Smoke test passed! Verified {count} answers on synthetic report.")


def test_smoke_report_a():
    """Optional smoke test on proprietary report_A.pdf (skipped when absent)."""
    repo_root = Path(__file__).resolve().parent.parent
    pdf_path = repo_root / "data" / "report_A.pdf"
    if not pdf_path.exists():
        pytest.skip("Proprietary report_A.pdf not found in data/ directory; skipping.")

    questions_path = repo_root / "data" / "questions_with_answers.jsonl"
    if not questions_path.exists():
        pytest.skip("questions_with_answers.jsonl not found in data/ directory; skipping.")

    count = _run_predict_and_validate(pdf_path, questions_path)
    print(f"Smoke test passed! Verified {count} answers on report_A.pdf.")


if __name__ == "__main__":
    test_smoke()
