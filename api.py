import asyncio
import json
import os
import shutil
import time
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException, Query, Response, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
try:
    import pymupdf as fitz
except ImportError:
    import fitz

import config
import database as db
from ingest import ingest_pdf
from index import build_index, Indexer
from retriever import HybridRetriever
from qa import QAEngine
from highlight import render_highlighted_page_png, get_normalized_page_rects

# ===========================================================================
# OpenAPI Tags & Metadata
# ===========================================================================

tags_metadata = [
    {
        "name": "System",
        "description": "System health diagnostics, index inspection, and user feedback submission."
    },
    {
        "name": "Document",
        "description": "Active PDF metadata, multi-document cataloging, document selection, and raw PDF streaming."
    },
    {
        "name": "Evidence & Pages",
        "description": "High-fidelity page rendering with burned-in verbatim highlights and normalized coordinate extraction for client-side bounding boxes."
    },
    {
        "name": "Question Answering",
        "description": "Grounded question answering endpoints: direct synchronous QA (/api/query, /api/ask) and real-time streaming SSE QA (/api/chat) with full anti-hallucination citation verification."
    },
    {
        "name": "Ingestion & Indexing",
        "description": "Upload new statistical PDF reports, run table/text extraction, build BM25 + dense indexes, and monitor pipeline progress."
    }
]

app = FastAPI(
    title="Report Navigator API",
    description=(
        "## Production Grounded Statistics QA & Document Navigator API\n\n"
        "Welcome to the **Report Navigator API**, an advanced Retrieval-Augmented Generation (RAG) platform "
        "tailored for high-precision extraction and statistical question answering on tabular and textual PDF reports.\n\n"
        "### Core Engineering Highlights:\n"
        "- **Table-First Grounding**: Forward-fills merged table headers, extracts row-level contexts, and reconstructs multi-level categories.\n"
        "- **Anti-Hallucination Citation Verification**: Every answer strictly derives from verbatim quotes and verified table cells.\n"
        "- **Visual Evidence Highlight**: Renders pinpoint page images with highlights directly burned into cited text and tables.\n"
        "- **Streaming SSE Chat**: Real-time pipeline events (`rewriting`, `searching`, `reading`, `verifying`) followed by final answer payload.\n"
        "- **Cloud & Serverless Ready**: Deployable on Render / Neon Serverless Postgres / Vercel."
    ),
    version="1.2.0",
    openapi_tags=tags_metadata,
    docs_url="/docs",
    redoc_url="/redoc",
    swagger_ui_parameters={"docExpansion": "list", "deepLinking": True, "filter": True}
)

# ===========================================================================
# Security Middleware & CORS
# ===========================================================================

@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Enforce standard enterprise HTTP security headers."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# Configure CORS
origins = list(config.CORS_ORIGINS)
if "https://reposync-ivory.vercel.app" not in origins:
    origins.append("https://reposync-ivory.vercel.app")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===========================================================================
# Rate Limiting & Global Engine State
# ===========================================================================

_request_timestamps: Dict[str, List[float]] = {}
_rate_limit_lock = asyncio.Lock()


async def check_rate_limit(request: Request):
    """Sliding-window IP-based rate limiter to protect downstream LLM & compute resources."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    now = time.time()
    async with _rate_limit_lock:
        timestamps = _request_timestamps.setdefault(client_ip, [])
        cutoff = now - 60.0
        # Retain only timestamps from the last 60 seconds
        _request_timestamps[client_ip] = [t for t in timestamps if t > cutoff]
        if len(_request_timestamps[client_ip]) >= config.RATE_LIMIT_PER_MINUTE:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded: maximum {config.RATE_LIMIT_PER_MINUTE} requests per minute."
            )
        _request_timestamps[client_ip].append(now)


_qa_engine: Optional[QAEngine] = None
_index_status: Dict[str, Any] = {
    "status": "idle",
    "progress": 0,
    "message": "Ready",
    "active_doc": str(config.PDF_PATH.name) if config.PDF_PATH.exists() else "None"
}


def get_active_pdf() -> Path:
    """Retrieve the currently active PDF path, respecting active_doc.json if present across OSes."""
    state_file = config.DATA_DIR / "active_doc.json"
    if state_file.exists():
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                filename = data.get("filename")
                if filename:
                    candidate = config.DATA_DIR / filename
                    if candidate.exists():
                        config.PDF_PATH = candidate
                        return candidate
                candidate = Path(data.get("active_pdf", ""))
                if candidate.exists():
                    config.PDF_PATH = candidate
                    return candidate
        except Exception:
            pass
    for fname in ["report_A.pdf", "report.pdf"]:
        candidate = config.DATA_DIR / fname
        if candidate.exists():
            config.PDF_PATH = candidate
            return candidate
    return config.PDF_PATH


def set_active_pdf(pdf_path: Path):
    """Set the active PDF path and persist it across server reloads."""
    config.PDF_PATH = pdf_path.resolve()
    try:
        config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(config.DATA_DIR / "active_doc.json", "w", encoding="utf-8") as f:
            json.dump({"active_pdf": str(pdf_path.resolve()), "filename": pdf_path.name}, f, indent=2)
    except Exception as e:
        print(f"[API] Warning persisting active doc: {e}")


def sanitize_pdf_filename(filename: str) -> Path:
    """Sanitize filename to prevent path traversal vulnerabilities and ensure it resolves in DATA_DIR."""
    safe_name = Path(filename).name
    if not safe_name.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Invalid filename: only .pdf files are accepted.")
    target_path = (config.DATA_DIR / safe_name).resolve()
    try:
        target_path.relative_to(config.DATA_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Path traversal attempt rejected.")
    return target_path


def get_qa_engine() -> QAEngine:
    """Lazy-initializes or returns the cached QAEngine with loaded BM25/dense retriever."""
    global _qa_engine
    if _qa_engine is None:
        try:
            indexer = Indexer()
            if config.CHUNKS_FILE.exists():
                indexer.load()
            retriever = HybridRetriever(indexer=indexer)
            _qa_engine = QAEngine(retriever=retriever)
        except Exception as e:
            print(f"[API] Warning initializing QA Engine: {e}")
            _qa_engine = QAEngine()
    return _qa_engine


def reset_qa_engine():
    """Reset the global QAEngine instance so the next query reloads the index from disk."""
    global _qa_engine
    _qa_engine = None
    try:
        from qa import reset_solver
        reset_solver()
    except Exception:
        pass


# ===========================================================================
# Pydantic Schemas
# ===========================================================================

class ChatMessage(BaseModel):
    role: str = Field(..., max_length=50, description="Message sender role: 'user' or 'assistant'")
    content: str = Field(..., max_length=4000, description="Message text content")


class ChatRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        max_length=config.MAX_QUERY_LENGTH,
        description="The statistical or factual question about the report",
        json_schema_extra={"example": "What was the number of road accident deaths in Pune city in 2023?"}
    )
    history: Optional[List[ChatMessage]] = Field(
        default=[],
        max_length=config.MAX_HISTORY_MESSAGES,
        description="Prior conversation history for context-aware rewriting"
    )
    use_rerank: Optional[bool] = Field(
        default=True,
        description="Enable cross-encoder or heuristic reranking"
    )


class DocumentSelectRequest(BaseModel):
    filename: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="The filename of an existing PDF in the data directory to set active",
        json_schema_extra={"example": "report_A.pdf"}
    )


class FeedbackRequest(BaseModel):
    query: str = Field(..., max_length=1000, description="The user question that was answered")
    answer: str = Field(..., max_length=4000, description="The answer that was provided")
    rating: str = Field(..., description="User rating: 'positive' or 'negative'")
    comment: Optional[str] = Field(None, max_length=1000, description="Optional user commentary")


# ===========================================================================
# System Endpoints
# ===========================================================================

@app.get("/api/health", tags=["System"], summary="Health check and status diagnostics")
def health_check():
    """Health check endpoint indicating server status, active document, page count, and indexed chunk count."""
    active_pdf = get_active_pdf()
    exists = active_pdf.exists()
    page_count = 0
    if exists:
        try:
            doc = fitz.open(str(active_pdf))
            page_count = len(doc)
            doc.close()
        except Exception:
            pass

    chunk_count = 0
    if config.CHUNKS_FILE.exists():
        try:
            with open(config.CHUNKS_FILE, "r", encoding="utf-8") as f:
                chunk_count = sum(1 for _ in f)
        except Exception:
            pass

    return {
        "status": "ok",
        "pdf_exists": exists,
        "active_doc": active_pdf.name if exists else None,
        "page_count": page_count,
        "chunks_indexed": chunk_count,
        "database": db.check_health()
    }


@app.post("/api/feedback", tags=["System"], summary="Submit user feedback on answer quality")
def submit_feedback(req: FeedbackRequest):
    """Persists user thumbs up / down feedback and optional comments for continuous QA evaluation."""
    feedback_file = config.DATA_DIR / "feedback.jsonl"
    record = {
        "timestamp": time.time(),
        "query": req.query,
        "answer": req.answer,
        "rating": req.rating,
        "comment": req.comment
    }
    try:
        with open(feedback_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except Exception as e:
        print(f"[API] Error saving feedback: {e}")
    # Persist to Neon database (non-blocking, best-effort)
    db.log_feedback(query=req.query, answer=req.answer, rating=req.rating, comment=req.comment)
    return {"status": "success", "message": "Feedback recorded successfully."}


# ===========================================================================
# Document Management Endpoints
# ===========================================================================

@app.get("/api/doc", tags=["Document"], summary="Active report metadata and starter questions")
def get_document_metadata():
    """
    Returns metadata about the active report:
    title, filename, total pages, table count, and tailored starter questions.
    """
    active_pdf = get_active_pdf()
    if not active_pdf.exists():
        return {
            "title": "No Report Loaded",
            "filename": "",
            "page_count": 0,
            "table_count": 0,
            "starter_questions": [
                "What are the main findings in this report?",
                "What key statistical metrics are highlighted?",
                "Summarize the executive summary.",
                "Compare the primary metrics between latest periods."
            ]
        }

    try:
        doc = fitz.open(str(active_pdf))
        page_count = len(doc)
        title = doc.metadata.get("title") or active_pdf.stem.replace("_", " ").title()
        doc.close()
    except Exception:
        page_count = 0
        title = active_pdf.stem

    table_count = 0
    detected_sections: List[str] = []
    if config.CHUNKS_FILE.exists():
        try:
            with open(config.CHUNKS_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    if '"type": "table"' in line:
                        table_count += 1
                    if len(detected_sections) < 5 and '"section":' in line:
                        try:
                            ch_data = json.loads(line)
                            sec = ch_data.get("section")
                            if sec and sec != "General" and sec not in detected_sections:
                                detected_sections.append(sec)
                        except Exception:
                            pass
        except Exception:
            pass

    # Provide tailored starter questions
    if active_pdf.name == "report_A.pdf":
        starter_questions = [
            "What was the number of road accident deaths in Pune city in 2023?",
            "How many persons were killed in road accidents in Maharashtra in 2023?",
            "How many two-wheeler riders were killed in road accidents in Allahabad (Prayagraj) in 2023?",
            "How many road accident deaths in Hyderabad in 2023 were attributed to over-speeding?",
            "How many road accidents were reported in Bareilly city in 2023?"
        ]
    elif detected_sections:
        starter_questions = [
            f"What are the key statistics reported in {detected_sections[0]}?",
            f"What does the report state regarding {detected_sections[-1]}?",
            "What are the overall findings and national totals in the report?",
            "Summarize the highest and lowest figures recorded across categories."
        ]
    else:
        starter_questions = [
            f"What are the primary findings in {title}?",
            "What are the key statistical highlights in this report?",
            "Summarize the main table statistics.",
            "What conclusions or trends are discussed?"
        ]

    return {
        "title": title,
        "filename": active_pdf.name,
        "page_count": page_count,
        "table_count": table_count,
        "starter_questions": starter_questions
    }


@app.get("/api/documents", tags=["Document"], summary="List available PDF documents")
def list_documents():
    """List all PDF files available in the data directory and indicate which is active."""
    active_pdf = get_active_pdf()
    docs = []
    if config.DATA_DIR.exists():
        for f in config.DATA_DIR.glob("*.pdf"):
            size_mb = round(f.stat().st_size / (1024 * 1024), 2)
            pages = 0
            try:
                d = fitz.open(str(f))
                pages = len(d)
                d.close()
            except Exception:
                pass
            docs.append({
                "filename": f.name,
                "size_mb": size_mb,
                "page_count": pages,
                "is_active": (f.resolve() == active_pdf.resolve())
            })
    return {"documents": docs, "active_document": active_pdf.name if active_pdf.exists() else None}


@app.post("/api/documents/select", tags=["Document"], summary="Select active PDF document")
def select_document(req: DocumentSelectRequest):
    """Switch active report to an existing PDF in the data directory and reset QA engine."""
    target_path = sanitize_pdf_filename(req.filename)
    if not target_path.exists():
        raise HTTPException(status_code=404, detail=f"PDF file '{req.filename}' not found in data directory.")

    set_active_pdf(target_path)
    reset_qa_engine()
    return {
        "status": "success",
        "message": f"Active report switched to '{req.filename}'.",
        "active_document": req.filename
    }


@app.get("/api/pdf", tags=["Document"], summary="Stream raw PDF bytes")
def stream_pdf(filename: Optional[str] = Query(None, description="Optional filename to stream; defaults to active PDF")):
    """Stream PDF bytes for in-browser viewer or direct download."""
    if filename:
        target = sanitize_pdf_filename(filename)
    else:
        target = get_active_pdf()

    if not target.exists():
        raise HTTPException(status_code=404, detail="Requested PDF not found on server")

    return FileResponse(
        str(target),
        media_type="application/pdf",
        filename=target.name
    )


# ===========================================================================
# Evidence & Page Rendering Endpoints
# ===========================================================================

@app.get("/api/page/{page_number}/image", tags=["Evidence & Pages"], summary="Render highlighted PDF page image")
def get_page_image(
    page_number: int,
    quote: Optional[str] = Query(None, description="Exact verbatim quote or table row to highlight on the page"),
    is_table: Optional[bool] = Query(False, description="Whether the cited passage belongs to a tabular row"),
    zoom: Optional[float] = Query(1.6, description="Render scale multiplier (default: 1.6)"),
    chunk_id: Optional[str] = Query(None, alias="chunk", description="Optional chunk id for bounding box fallback")
):
    """
    Renders requested PDF page to PNG with warm yellow highlight burned into the cited text or table row.
    """
    active_pdf = get_active_pdf()
    if not active_pdf.exists():
        raise HTTPException(status_code=404, detail="No active PDF document found")

    try:
        doc = fitz.open(str(active_pdf))
        total_pages = len(doc)
        doc.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to inspect PDF: {e}")

    if page_number < 1 or page_number > total_pages:
        raise HTTPException(
            status_code=400,
            detail=f"Page number {page_number} is out of bounds for document '{active_pdf.name}' (1..{total_pages})"
        )

    chunk_rects = None
    if chunk_id:
        engine = get_qa_engine()
        for ch in engine.retriever.indexer.chunks:
            if ch.get("id") == chunk_id:
                chunk_rects = ch.get("rects")
                break

    try:
        png_bytes = render_highlighted_page_png(
            pdf_path=active_pdf,
            page_number=page_number,
            quote=quote,
            chunk_rects=chunk_rects,
            is_table=is_table or False,
            zoom=zoom or 1.6
        )
        return Response(content=png_bytes, media_type="image/png")
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/page/{page_number}/rects", tags=["Evidence & Pages"], summary="Extract bounding box coordinates")
def get_page_rects(
    page_number: int,
    quote: Optional[str] = Query(None, description="Quote to find coordinates for"),
    is_table: Optional[bool] = Query(False, description="Whether target is a table row"),
    chunk_id: Optional[str] = Query(None, alias="chunk", description="Optional chunk id")
):
    """
    Returns normalized bounding box coordinates [0..1] for client-side canvas highlighting.
    """
    active_pdf = get_active_pdf()
    if not active_pdf.exists():
        raise HTTPException(status_code=404, detail="No active PDF document found")

    try:
        doc = fitz.open(str(active_pdf))
        total_pages = len(doc)
        doc.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to inspect PDF: {e}")

    if page_number < 1 or page_number > total_pages:
        raise HTTPException(
            status_code=400,
            detail=f"Page number {page_number} is out of bounds for document '{active_pdf.name}' (1..{total_pages})"
        )

    chunk_rects = None
    if chunk_id:
        engine = get_qa_engine()
        for ch in engine.retriever.indexer.chunks:
            if ch.get("id") == chunk_id:
                chunk_rects = ch.get("rects")
                break

    try:
        data = get_normalized_page_rects(
            pdf_path=active_pdf,
            page_number=page_number,
            quote=quote,
            chunk_rects=chunk_rects,
            is_table=is_table or False
        )
        return data
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================================================
# Question Answering Endpoints
# ===========================================================================

@app.post(
    "/api/query",
    tags=["Question Answering"],
    summary="Direct synchronous QA query",
    dependencies=[Depends(check_rate_limit)]
)
@app.post(
    "/api/ask",
    tags=["Question Answering"],
    summary="Direct synchronous QA query alias",
    dependencies=[Depends(check_rate_limit)]
)
def direct_query_endpoint(req: ChatRequest):
    """
    Synchronous direct JSON QA endpoint. Ideal for testing queries in Swagger UI.
    
    Executes the complete RAG pipeline:
    1. Query understanding & synonym expansion
    2. Hybrid BM25 + dense retrieval
    3. Reranking & quality gating
    4. Grounded answer extraction
    5. Anti-hallucination citation verification & page chips
    
    Returns complete response with answer, verified citations, and retrieval trace.
    """
    engine = get_qa_engine()
    history_dicts = [{"role": m.role, "content": m.content} for m in req.history] if req.history else []
    try:
        t0 = time.time()
        answer_payload = engine.answer(
            query=req.query,
            history=history_dicts,
            use_rerank=req.use_rerank if req.use_rerank is not None else True
        )
        latency_ms = int((time.time() - t0) * 1000)
        # Log to Neon (best-effort, non-blocking)
        active_pdf = get_active_pdf()
        db.log_query(
            document_id=active_pdf.stem if active_pdf.exists() else None,
            query=req.query,
            answer=answer_payload.get("answer", ""),
            confidence=answer_payload.get("confidence"),
            citations=answer_payload.get("citations"),
            latency_ms=latency_ms,
        )
        return answer_payload
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"QA pipeline error: {str(e)}")


@app.post(
    "/api/chat",
    tags=["Question Answering"],
    summary="Streaming SSE QA chat endpoint",
    dependencies=[Depends(check_rate_limit)]
)
async def chat_sse_stream(req: ChatRequest):
    """
    Server-Sent Events (SSE) stream for interactive chat.
    Streams status updates during pipeline execution ('rewriting', 'searching', 'reading', 'verifying'),
    followed by the final grounded answer payload with citations.
    """
    engine = get_qa_engine()
    queue = asyncio.Queue()

    def sync_status_callback(step: str, message: str):
        queue.put_nowait({"event": "status", "data": {"step": step, "message": message}})

    async def event_generator():
        async def run_pipeline():
            try:
                history_dicts = [{"role": m.role, "content": m.content} for m in req.history] if req.history else []
                loop = asyncio.get_running_loop()
                t0 = time.time()
                answer_payload = await loop.run_in_executor(
                    None,
                    lambda: engine.answer(
                        query=req.query,
                        history=history_dicts,
                        use_rerank=req.use_rerank if req.use_rerank is not None else True,
                        on_status=sync_status_callback
                    )
                )
                latency_ms = int((time.time() - t0) * 1000)
                # Deliver answer payload to client stream FIRST with zero delay
                await queue.put({"event": "answer", "data": answer_payload})

                # Best-effort query log to Neon in background
                try:
                    active_pdf = get_active_pdf()
                    db.log_query(
                        document_id=active_pdf.stem if active_pdf.exists() else None,
                        query=req.query,
                        answer=answer_payload.get("answer", ""),
                        confidence=answer_payload.get("confidence"),
                        citations=answer_payload.get("citations"),
                        latency_ms=latency_ms,
                    )
                except Exception as log_err:
                    print(f"[API] Best-effort DB query log failed: {log_err}")
            except Exception as e:
                print(f"[API] Error during chat processing: {e}")
                await queue.put({
                    "event": "error",
                    "data": {"detail": str(e) or "An error occurred during query execution."}
                })
            finally:
                await queue.put(None)  # Guaranteed sentinel to close stream

        asyncio.create_task(run_pipeline())

        while True:
            item = await queue.get()
            if item is None:
                break
            event_type = item["event"]
            json_data = json.dumps(item["data"])
            yield f"event: {event_type}\ndata: {json_data}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ===========================================================================
# Ingestion & Indexing Endpoints
# ===========================================================================

def run_indexing_task(file_path: Path) -> Dict[str, Any]:
    """Execute ingestion and index construction for the given PDF file."""
    global _index_status
    try:
        _index_status = {
            "status": "ingesting",
            "progress": 25,
            "message": f"Parsing text, tables, and bounding boxes for {file_path.name}...",
            "active_doc": file_path.name
        }
        chunks = ingest_pdf(file_path)

        _index_status = {
            "status": "indexing",
            "progress": 65,
            "message": "Building BM25 and dense embeddings...",
            "active_doc": file_path.name
        }
        build_index()

        reset_qa_engine()

        text_chunks = sum(1 for c in chunks if c.get("type") == "text")
        table_chunks = sum(1 for c in chunks if c.get("type") == "table")

        stats = {
            "total_chunks": len(chunks),
            "text_chunks": text_chunks,
            "table_chunks": table_chunks,
            "filename": file_path.name
        }

        # Register document in Neon (best-effort)
        try:
            import hashlib
            doc_id = hashlib.md5(file_path.name.encode()).hexdigest()[:16]
            file_size = file_path.stat().st_size if file_path.exists() else 0
            try:
                import pymupdf as fitz_mod
            except ImportError:
                import fitz as fitz_mod
            d = fitz_mod.open(str(file_path))
            pg_count = len(d)
            d.close()
            db.register_document(
                doc_id=doc_id,
                filename=file_path.name,
                title=file_path.stem.replace("_", " ").title(),
                page_count=pg_count,
                table_count=table_chunks,
                file_size=file_size,
            )
        except Exception as reg_err:
            print(f"[API] Document registration to Neon skipped: {reg_err}")

        _index_status = {
            "status": "complete",
            "progress": 100,
            "message": f"Indexing complete for {file_path.name}! Ready to query.",
            "active_doc": file_path.name,
            "stats": stats
        }
        return stats
    except Exception as e:
        _index_status = {
            "status": "error",
            "progress": 0,
            "message": f"Indexing failed: {str(e)}",
            "active_doc": file_path.name
        }
        raise e


@app.post("/api/index", tags=["Ingestion & Indexing"], summary="Upload & index a PDF report")
@app.post("/api/ingest", tags=["Ingestion & Indexing"], summary="Upload & index alias")
@app.post("/api/upload", tags=["Ingestion & Indexing"], summary="Upload & index alias")
async def upload_and_index(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="PDF report file to upload and index"),
    sync: Optional[bool] = Query(False, description="If True, process synchronously and return full ingestion stats directly")
):
    """
    Upload a new PDF report to the server and trigger ingestion & index construction.
    
    Security & Validation:
    - Path traversal prevention: sanitizes file basename.
    - Magic-byte verification: checks for valid `%PDF` file header.
    - Size cap: enforces `MAX_UPLOAD_SIZE_BYTES` (default 50MB).
    - Sets uploaded document as active report upon successful ingestion.
    """
    global _index_status
    safe_name = Path(file.filename).name
    if not safe_name.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files (.pdf) are supported.")

    # Validate PDF magic bytes (%PDF)
    head = await file.read(4)
    if head != b"%PDF":
        raise HTTPException(
            status_code=400,
            detail="Invalid file: uploaded file does not begin with standard %PDF signature."
        )

    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    dest_path = (config.DATA_DIR / safe_name).resolve()

    # Stream to disk with size cap enforcement
    bytes_written = 4
    with open(dest_path, "wb") as buffer:
        buffer.write(head)
        while chunk := await file.read(1024 * 1024):
            bytes_written += len(chunk)
            if bytes_written > config.MAX_UPLOAD_SIZE_BYTES:
                buffer.close()
                dest_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=413,
                    detail=f"File exceeds maximum allowed upload size of {config.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)} MB."
                )
            buffer.write(chunk)

    set_active_pdf(dest_path)

    if sync:
        try:
            stats = run_indexing_task(dest_path)
            return {
                "status": "complete",
                "message": f"Uploaded and indexed {safe_name} successfully.",
                "filename": safe_name,
                "stats": stats
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}")
    else:
        _index_status = {
            "status": "starting",
            "progress": 5,
            "message": f"Analysis queued for {safe_name}...",
            "active_doc": safe_name
        }
        background_tasks.add_task(run_indexing_task, dest_path)
        return {
            "status": "starting",
            "message": f"Uploaded {safe_name}. Indexing initiated in background.",
            "filename": safe_name,
            "check_status_url": "/api/index/status"
        }


@app.get("/api/index/status", tags=["Ingestion & Indexing"], summary="Get indexing progress status")
def get_indexing_status():
    """Returns the current status, progress percentage, and message of the document indexing pipeline."""
    return _index_status



@app.on_event("startup")
def startup_event():
    """Ensure active document index and solver are pre-warmed and ready on boot."""
    active_pdf = get_active_pdf()
    if not config.CHUNKS_FILE.exists() or config.CHUNKS_FILE.stat().st_size < 100:
        if active_pdf.exists():
            print(f"[Startup] Building missing index for {active_pdf.name}...")
            try:
                run_indexing_task(active_pdf)
            except Exception as e:
                print(f"[Startup] Index build error: {e}")
    try:
        get_qa_engine()
        if active_pdf.exists():
            from qa import get_solver
            get_solver(str(active_pdf))
            print(f"[Startup] QA Engine & Solver pre-warmed for {active_pdf.name}")
    except Exception as e:
        print(f"[Startup] Pre-warm notice: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host=config.HOST, port=config.PORT, reload=True)
