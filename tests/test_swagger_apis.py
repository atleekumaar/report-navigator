import sys
import json
import io
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient
import pymupdf as fitz

from api import app, set_active_pdf, get_active_pdf, reset_qa_engine
import config


@pytest.fixture(scope="function")
def client():
    return TestClient(app)


@pytest.fixture(scope="session")
def sample_pdf_path(tmp_path_factory) -> Path:
    """Generate a clean 2-page sample PDF with text and table for ingestion testing."""
    pdf_dir = config.DATA_DIR
    pdf_path = pdf_dir / "sample_company_report_2024.pdf"

    doc = fitz.open()

    # Page 1: Executive Summary
    p1 = doc.new_page(width=595, height=842)
    p1.insert_text((50, 72), "Annual Corporate Report 2024", fontsize=18)
    p1.insert_text((50, 110), "Executive Summary", fontsize=14)
    p1.insert_text(
        (50, 140),
        "In fiscal year 2024, our company achieved a total revenue of 450 million dollars. "
        "The overall customer satisfaction rating rose to 94.5 percent across all service divisions. "
        "The total employee count expanded to 1,250 members worldwide.",
        fontsize=11
    )

    # Page 2: Performance Metrics Table
    p2 = doc.new_page(width=595, height=842)
    p2.insert_text((50, 72), "Chapter 2: Financial Performance", fontsize=14)
    p2.insert_text(
        (50, 100),
        "Division | Revenue (M$) | Growth (%)\n"
        "Cloud Solutions | 210 | 18.4%\n"
        "Enterprise Software | 160 | 12.1%\n"
        "Consulting Services | 80 | 5.2%\n",
        fontsize=11
    )

    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


def test_swagger_ui_and_openapi_schema(client):
    """Test that /docs and /openapi.json are accessible and properly generated."""
    res_docs = client.get("/docs")
    assert res_docs.status_code == 200
    assert "swagger-ui" in res_docs.text.lower() or "html" in res_docs.headers.get("content-type", "")

    res_openapi = client.get("/openapi.json")
    assert res_openapi.status_code == 200
    schema = res_openapi.json()
    assert "paths" in schema
    assert "/api/health" in schema["paths"]
    assert "/api/doc" in schema["paths"]
    assert "/api/pdf" in schema["paths"]
    assert "/api/query" in schema["paths"]
    assert "/api/ask" in schema["paths"]
    assert "/api/chat" in schema["paths"]
    assert "/api/index" in schema["paths"]
    assert "/api/ingest" in schema["paths"]
    assert "/api/upload" in schema["paths"]
    assert "/api/documents" in schema["paths"]
    assert "/api/documents/select" in schema["paths"]


def test_health_endpoint(client):
    """Test GET /api/health."""
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "pdf_exists" in data
    assert "active_doc" in data


def test_document_metadata(client):
    """Test GET /api/doc."""
    res = client.get("/api/doc")
    assert res.status_code == 200
    data = res.json()
    assert "title" in data
    assert "page_count" in data
    assert "table_count" in data
    assert "starter_questions" in data
    assert len(data["starter_questions"]) >= 1


def test_list_and_select_documents(client):
    """Test GET /api/documents and POST /api/documents/select."""
    res = client.get("/api/documents")
    assert res.status_code == 200
    data = res.json()
    assert "documents" in data
    assert len(data["documents"]) >= 1

    # Select report_A.pdf if present
    res_sel = client.post("/api/documents/select", json={"filename": "report_A.pdf"})
    assert res_sel.status_code in (200, 404)
    if res_sel.status_code == 200:
        assert res_sel.json()["status"] == "success"


def test_stream_pdf(client):
    """Test GET /api/pdf."""
    res = client.get("/api/pdf")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert len(res.content) > 1000


def test_page_image_rendering(client):
    """Test GET /api/page/{page_number}/image."""
    # Valid page 1
    res = client.get("/api/page/1/image")
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/png"
    assert len(res.content) > 100

    # Out of bounds page
    res_err = client.get("/api/page/99999/image")
    assert res_err.status_code == 400
    assert "out of bounds" in res_err.json()["detail"].lower()


def test_page_rects(client):
    """Test GET /api/page/{page_number}/rects."""
    res = client.get("/api/page/1/rects")
    assert res.status_code == 200
    data = res.json()
    assert "page" in data
    assert "width" in data
    assert "height" in data
    assert "rects" in data

    # Out of bounds page
    res_err = client.get("/api/page/0/rects")
    assert res_err.status_code == 400


def test_direct_query_endpoints(client):
    """Test POST /api/query and POST /api/ask."""
    payload = {
        "query": "What was the number of road accident deaths in Pune city in 2023?",
        "history": [],
        "use_rerank": True
    }
    # /api/query
    res1 = client.post("/api/query", json=payload)
    assert res1.status_code == 200
    data1 = res1.json()
    assert "found" in data1
    assert "answer" in data1
    assert "citations" in data1

    # /api/ask alias
    res2 = client.post("/api/ask", json=payload)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["found"] == data1["found"]


def test_chat_sse_stream(client):
    """Test POST /api/chat (SSE stream)."""
    payload = {
        "query": "How many persons were killed in road accidents in Maharashtra in 2023?",
        "history": [],
        "use_rerank": True
    }
    with client.stream("POST", "/api/chat", json=payload) as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
        events = []
        for line in response.iter_lines():
            if line.startswith("event:"):
                events.append(line.split(":", 1)[1].strip())
        assert "answer" in events or len(events) >= 1


def test_ingest_new_pdf_and_query_flow(client, sample_pdf_path):
    """
    Test uploading and ingesting a NEW PDF on Swagger / API:
    1. Upload via POST /api/ingest (sync=True)
    2. Check GET /api/doc reflects new title and starter questions
    3. Query the newly ingested PDF via POST /api/query
    4. Verify page image and rects for the new PDF
    5. Switch back to report_A.pdf
    """
    with open(sample_pdf_path, "rb") as f:
        pdf_bytes = f.read()

    # Step 1: Upload and ingest synchronously
    files = {"file": ("sample_company_report_2024.pdf", pdf_bytes, "application/pdf")}
    res_upload = client.post("/api/ingest?sync=true", files=files)
    assert res_upload.status_code == 200, f"Upload failed: {res_upload.text}"
    upload_data = res_upload.json()
    assert upload_data["status"] == "complete"
    assert upload_data["filename"] == "sample_company_report_2024.pdf"

    # Step 2: Verify active document metadata
    res_doc = client.get("/api/doc")
    assert res_doc.status_code == 200
    doc_info = res_doc.json()
    assert doc_info["filename"] == "sample_company_report_2024.pdf"
    assert doc_info["page_count"] == 2

    # Step 3: Verify page 1 image on new PDF
    res_img = client.get("/api/page/1/image")
    assert res_img.status_code == 200
    assert len(res_img.content) > 100

    # Step 4: Query information from the newly ingested PDF
    query_payload = {
        "query": "What was the total revenue in fiscal year 2024?",
        "history": [],
        "use_rerank": True
    }
    res_query = client.post("/api/query", json=query_payload)
    assert res_query.status_code == 200
    ans_data = res_query.json()
    assert ans_data["found"] is True
    assert "450" in ans_data["answer"] or "revenue" in ans_data["answer"].lower()
    assert len(ans_data["citations"]) >= 1

    # Step 5: Switch back to report_A.pdf
    if (config.DATA_DIR / "report_A.pdf").exists():
        client.post("/api/documents/select", json={"filename": "report_A.pdf"})
        # Re-verify report_A is active
        res_back = client.get("/api/health")
        assert res_back.json()["active_doc"] == "report_A.pdf"


def test_security_headers(client):
    """Verify standard enterprise security headers are returned on all endpoints."""
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.headers.get("x-content-type-options") == "nosniff"
    assert res.headers.get("x-frame-options") == "DENY"
    assert res.headers.get("x-xss-protection") == "1; mode=block"
    assert res.headers.get("referrer-policy") == "strict-origin-when-cross-origin"


def test_path_traversal_protection(client):
    """Verify that path traversal attempts in document selection or streaming fail cleanly."""
    res_select = client.post("/api/documents/select", json={"filename": "../../etc/passwd.pdf"})
    assert res_select.status_code in (400, 404)

    res_stream = client.get("/api/pdf?filename=../../secret.pdf")
    assert res_stream.status_code in (400, 404)


def test_upload_magic_bytes_validation(client):
    """Verify uploading a file without valid %PDF magic bytes is rejected with 400."""
    fake_content = b"THIS IS NOT A VALID PDF FILE"
    files = {"file": ("malicious_payload.pdf", fake_content, "application/pdf")}
    res = client.post("/api/upload?sync=true", files=files)
    assert res.status_code == 400
    assert "pdf" in res.text.lower()


def test_feedback_endpoint(client):
    """Verify submitting positive and negative user feedback works and persists."""
    payload = {
        "query": "What is the unemployment rate?",
        "answer": "The overall unemployment rate is 4.8%.",
        "rating": "positive",
        "comment": "Accurate and verified against table."
    }
    res = client.post("/api/feedback", json=payload)
    assert res.status_code == 200
    assert res.json()["status"] == "success"
