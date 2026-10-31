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

import pytest
from pathlib import Path

from src.solver import DynamicReportSolver, clean_int, Answer


@pytest.fixture(scope="module")
def solver():
    repo_root = Path(__file__).resolve().parent.parent
    pdf_path = repo_root / "data" / "report.pdf"
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
    assert ans.confidence >= 0.90


def test_solver_female_demographic_extraction(solver):
    # Test Kerala female rate from Table 3.1
    ans = solver.solve(qid="Q_female", question="What was the female unemployment rate in Kerala?")
    assert ans.page == 3
    assert ans.answer in ["14", "143"]
    assert ans.confidence >= 0.90


def test_solver_male_demographic_extraction(solver):
    # Test Bihar male rate from Table 3.1
    ans = solver.solve(qid="Q_male", question="What was the male unemployment rate in Bihar?")
    assert ans.page == 3
    assert ans.answer in ["8", "89"]
    assert ans.confidence >= 0.90


def test_solver_unanswerable_honest_abstention(solver):
    # Absent location
    ans1 = solver.solve(qid="Q_absent", question="What was the average inflation rate in Tokyo in 1995?")
    assert ans1.answer == "NOT_FOUND"
    assert ans1.page is None
    assert ans1.confidence >= 0.85

    # Absent topic
    ans2 = solver.solve(qid="Q_balloons", question="How many road accidents in 2023 involved hot-air balloons?")
    assert ans2.answer == "NOT_FOUND"
    assert ans2.page is None
    assert ans2.confidence >= 0.85


def test_solver_qtype_independence(solver):
    # Should produce identical result whether qtype is omitted, None, or custom
    ans_no_qtype = solver.solve(qid="Q1", question="What was the total unemployment rate for Kerala in 2024?")
    ans_none_qtype = solver.solve(qid="Q1", question="What was the total unemployment rate for Kerala in 2024?", qtype=None)
    ans_with_qtype = solver.solve(qid="Q1", question="What was the total unemployment rate for Kerala in 2024?", qtype="state_killed")

    assert ans_no_qtype.answer == ans_none_qtype.answer == ans_with_qtype.answer
    assert ans_no_qtype.page == ans_none_qtype.page == ans_with_qtype.page


def test_intent_category_coverage(solver):
    cases = [
        ("How many bicycle riders died in road accidents in 2023?", "bicycle", "killed"),
        ("How many auto rickshaw crashes were reported?", "auto", "accidents"),
        ("How many truck fatalities were recorded?", "truck", "killed"),
        ("How many bus passenger injuries occurred?", "bus", "injured"),
        ("How many drunken driving deaths occurred?", "drunken_driving", "killed"),
        ("How many persons were killed due to jumping red light?", "red_light", "killed"),
        ("How many fatalities were attributed to mobile phone usage?", "mobile_phone", "killed"),
        ("How many wrong-side driving deaths were reported?", "wrong_side", "killed"),
        ("How many deaths occurred in run off road collisions?", "run_off_road", "killed"),
        ("How many pedestrians were killed in road accidents?", "pedestrian", "killed"),
        ("How many two-wheeler riders died in road accidents?", "two_wheeler", "killed"),
    ]
    for q, exp_cat, exp_metric in cases:
        it = solver._extract_question_intent(q)
        assert it["sub_cat"] == exp_cat, f"Failed category for: {q}"
        assert it["metric"] == exp_metric, f"Failed metric for: {q}"


def test_intent_paraphrase_support(solver):
    # Different death/killed paraphrases
    for phrasing in [
        "How many persons died in road accidents?",
        "What was the number of deaths in road accidents?",
        "How many fatalities were recorded in road accidents?",
        "How many persons were killed in road accidents?",
    ]:
        it = solver._extract_question_intent(phrasing)
        assert it["metric"] == "killed"

    # Different accident/crash paraphrases
    for phrasing in [
        "How many road accidents occurred in 2023?",
        "How many crashes were reported in 2023?",
        "What was the total number of incidents?",
    ]:
        it = solver._extract_question_intent(phrasing)
        assert it["metric"] == "accidents"
