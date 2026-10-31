import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from pathlib import Path
from fastapi.testclient import TestClient

import config
from ingest import clean_text, detect_heading, normalize_cell_text
from index import Indexer, tokenize_for_bm25, expand_with_synonyms
from qa import clean_for_quote_matching, extract_numbers, verify_citations, QAEngine
from highlight import clean_quote_for_search, get_normalized_page_rects, render_highlighted_page_png
from api import app


def test_clean_text():
    raw = "  This is   a \r\n test   with   spaces. \n\n\n\n End. "
    cleaned = clean_text(raw)
    assert "  " not in cleaned
    assert "\r" not in cleaned


def test_synonym_expansion():
    tokens = ["unemployment", "youth"]
    expanded = expand_with_synonyms(tokens)
    assert "jobless" in expanded or "joblessness" in expanded
    assert "young" in expanded or "15-29" in expanded


def test_tokenize_preserves_decimals_and_commas():
    text = "In 2024, rate was 9.9% and total was 1,234 persons."
    tokens = tokenize_for_bm25(text)
    assert "9.9" in tokens
    assert "1,234" in tokens or "1234" in tokens


def test_citation_verification_valid():
    source_map = {
        "S1": {
            "chunk": {
                "page": 3,
                "label": "43",
                "text": "In Kerala, the total unemployment rate for the calendar year 2024 was recorded at 9.9 per cent."
            }
        }
    }
    citations = [
        {"source_id": "S1", "quote": "unemployment rate for the calendar year 2024 was recorded at 9.9 per cent"}
    ]
    verified, any_v, num_warn = verify_citations(
        citations=citations,
        source_map=source_map,
        answer_text="Kerala's rate was 9.9% in 2024 [S1].",
        calculation=""
    )
    assert any_v is True
    assert verified[0]["verified"] is True
    assert num_warn is False


def test_citation_verification_hallucinated_number():
    source_map = {
        "S1": {
            "chunk": {
                "page": 3,
                "label": "43",
                "text": "In Kerala, the total unemployment rate for the calendar year 2024 was recorded at 9.9 per cent."
            }
        }
    }
    citations = [
        {"source_id": "S1", "quote": "unemployment rate was recorded at 15.5 per cent"}
    ]
    verified, any_v, num_warn = verify_citations(
        citations=citations,
        source_map=source_map,
        answer_text="Rate was 15.5% [S1].",
        calculation=""
    )
    assert verified[0]["verified"] is False
    assert "Number 15.5 not found" in verified[0]["reason"]


def test_qa_unanswerable_refusal():
    engine = QAEngine()
    result = engine.answer("What was the consumer inflation in Paris during 1980?")
    assert result["found"] is False
    assert "not found in the report" in result["answer"].lower()
    assert result["confidence"] in ("high", "medium")


def test_highlighting_rects():
    pdf_path = config.PDF_PATH
    if pdf_path.exists():
        data = get_normalized_page_rects(
            pdf_path=pdf_path,
            page_number=3,
            quote="Kerala",
            chunk_rects=None,
            is_table=False
        )
        assert data["page"] == 3
        assert data["width"] > 0
        assert data["height"] > 0


def _can_use_testclient() -> bool:
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.listen(1)
        s.settimeout(0.1)
        c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        c.settimeout(0.1)
        c.connect(("127.0.0.1", port))
        s.close()
        c.close()
        return True
    except Exception:
        return False


def test_api_health():
    routes = [r.path for r in app.routes]
    assert "/api/health" in routes

    if _can_use_testclient():
        client = TestClient(app)
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
    else:
        from api import health_check
        resp = health_check()
        assert resp["status"] == "ok"


def test_api_doc():
    routes = [r.path for r in app.routes]
    assert "/api/doc" in routes

    if _can_use_testclient():
        client = TestClient(app)
        resp = client.get("/api/doc")
        assert resp.status_code == 200
        data = resp.json()
        assert "page_count" in data
        assert "table_count" in data
    else:
        from api import get_document_metadata
        data = get_document_metadata()
        assert "page_count" in data
        assert "table_count" in data
