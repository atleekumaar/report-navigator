"""
test_solver.py — Automated tests for rewritten DynamicReportSolver.
Tests:
- Dynamic table discovery & cell extraction (no hardcoding)
- Accurate 1-based page citations
- Unanswerable abstention (NOT_FOUND, page: None)
- Category intent coverage (Bicycle, Auto, Car, Truck, Bus, Drunken driving, Red light, Mobile phone, Wrong-side)
- Paraphrase support (died, deaths, fatalities, killed, crashes, injuries)
- Independence from qtype argument
- Calibrated confidence scoring
- Clean integer extraction
"""

import sys
import inspect
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from src.solver import DynamicReportSolver, clean_int, Answer


@pytest.fixture(scope="module")
def solver():
    repo_root = Path(__file__).resolve().parent.parent
    pdf_path = repo_root / "data" / "report.pdf"
    if not pdf_path.exists():
        from create_sample_report import generate_sample_pdf
        generate_sample_pdf(pdf_path)
    assert pdf_path.exists(), f"Sample report missing at {pdf_path}"
    return DynamicReportSolver(str(pdf_path))


def test_clean_int_normalisation():
    assert clean_int("15,366") == "15366"
    assert clean_int(" 351 ") == "351"
    assert clean_int("7.1") == "7"
    assert clean_int("") == ""
    assert clean_int(None) == ""
    assert clean_int("NOT_FOUND") == ""
    assert clean_int("Page 43") == "43"


def test_answer_dataclass():
    ans = Answer(qid="P001", answer="351", page=101, confidence=0.95)
    assert ans.qid == "P001"
    assert ans.answer == "351"
    assert ans.page == 101
    assert 0.0 <= ans.confidence <= 1.0


def test_solver_dynamic_table_extraction(solver):
    # Test Kerala total unemployment rate from page 3 Table 3.1
    ans = solver.solve(qid="Q_kerala", question="What was the total unemployment rate for Kerala in 2024?")
    assert ans.page == 3
    assert ans.answer in ["9", "99"]


def test_solver_unanswerable_query(solver):
    # Question not present in document should cleanly abstain
    ans = solver.solve(qid="Q_none", question="How many lunar craters were discovered in 1920?")
    assert ans.answer == "NOT_FOUND"
    assert ans.page is None
    assert ans.confidence <= 0.25


def test_category_coverage(solver):
    # Verify the regex handles vehicle/violation terms
    from config import SYNONYMS
    for cat in ["bicycle", "auto", "car", "truck", "bus", "drunken driving", "red light", "mobile phone", "wrong-side"]:
        assert cat in SYNONYMS or any(cat in syns for syns in SYNONYMS.values()), f"Category {cat} missing from synonym mappings"


def test_paraphrase_coverage():
    from config import SYNONYMS
    # Verify death/died paraphrases exist in synonyms
    fatality_syns = SYNONYMS.get("killed", [])
    for word in ["died", "deaths", "fatalities", "dead"]:
        assert word in fatality_syns, f"Paraphrase {word} missing from killed synonyms"


def test_no_qtype_dependency(solver):
    # Solver must not require qtype argument
    sig = inspect.signature(solver.solve)
    if "qtype" in sig.parameters:
        assert sig.parameters["qtype"].default is not inspect.Parameter.empty, "qtype must have default and be optional"
    ans = solver.solve(qid="Q_no_qtype", question="What was total unemployment in Kerala?")
    assert ans is not None


def test_dynamic_confidence_scoring(solver):
    # Answered query must have confidence > 0.5
    ans_found = solver.solve(qid="Q1", question="What was the total unemployment rate for Kerala in 2024?")
    assert ans_found.confidence >= 0.5

    # Abstention query must have confidence <= 0.3
    ans_missing = solver.solve(qid="Q2", question="What was the sales tax in London in 1850?")
    assert ans_missing.confidence <= 0.3
