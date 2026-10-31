import asyncio
import json
import os
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
try:
    import pymupdf as fitz
except ImportError:
    import fitz

import config
from ingest import ingest_pdf
from index import build_index, Indexer
from retriever import HybridRetriever
from qa import QAEngine
from highlight import render_highlighted_page_png, get_normalized_page_rects

app = FastAPI(
    title="Report Navigator API",
    description=(
        "Comprehensive Backend API for the Report Navigator RAG System.\n\n"
        "Capabilities:\n"
        "- Ingest and index arbitrary statistical PDF reports.\n"
        "- Grounded question answering with anti-hallucination verification.\n"
        "- Exact page citations and pinpoint highlighted PDF page rendering.\n"
        "- Synchronous and streaming SSE chat endpoints.\n"
    ),
    version="1.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for Next.js frontend and external clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global engine and indexing state
_qa_engine: Optional[QAEngine] = None
_index_status: Dict[str, Any] = {
    "status": "idle",
    "progress": 0,
    "message": "Ready",
    "active_doc": str(config.PDF_PATH.name) if config.PDF_PATH.exists() else "None"
}


def get_active_pdf() -> Path:
    """Retrieve the currently active PDF path, respecting active_doc.json if present."""
    state_file = config.DATA_DIR / "active_doc.json"
    if state_file.exists():
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                candidate = Path(data.get("active_pdf", ""))
                if candidate.exists():
                    config.PDF_PATH = candidate
                    return candidate
        except Exception:
            pass
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


class ChatMessage(BaseModel):
    role: str = Field(..., description="Role: 'user' or 'assistant'")
    content: str = Field(..., description="Message text")


class ChatRequest(BaseModel):
    query: str = Field(..., description="The user query or question about the report", json_schema_extra={"example": "What was the number of road accident deaths in Pune city in 2023?"})
    history: Optional[List[ChatMessage]] = Field(default=[], description="Prior conversation messages")
    use_rerank: Optional[bool] = Field(default=True, description="Enable cross-encoder / heuristic reranking")


class DocumentSelectRequest(BaseModel):
    filename: str = Field(..., description="The filename of an existing PDF in the data directory to set active", json_schema_extra={"example": "report_A.pdf"})


# ---------------------------------------------------------------------------
# System Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/health", tags=["System"])
def health_check():
    """Health check endpoint indicating server status and active PDF availability."""
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
        "chunks_indexed": chunk_count
    }


# ---------------------------------------------------------------------------
# Document Management Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/doc", tags=["Document"])
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


@app.get("/api/documents", tags=["Document"])
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


@app.post("/api/documents/select", tags=["Document"])
def select_document(req: DocumentSelectRequest):
    """Switch active report to an existing PDF in the data directory and reset QA engine."""
    target_path = config.DATA_DIR / req.filename
    if not target_path.exists():
        raise HTTPException(status_code=404, detail=f"PDF file '{req.filename}' not found in data directory.")

    set_active_pdf(target_path)
    reset_qa_engine()
    return {
        "status": "success",
        "message": f"Active report switched to '{req.filename}'.",
        "active_document": req.filename
    }


@app.get("/api/pdf", tags=["Document"])
def stream_pdf(filename: Optional[str] = Query(None, description="Optional filename to stream; defaults to active PDF")):
    """Stream PDF bytes for in-browser viewer or direct download."""
    if filename:
        target = config.DATA_DIR / filename
    else:
        target = get_active_pdf()

    if not target.exists():
        raise HTTPException(status_code=404, detail="Requested PDF not found on server")

    return FileResponse(
        str(target),
        media_type="application/pdf",
        filename=target.name
    )


# ---------------------------------------------------------------------------
# Evidence & Page Rendering Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/page/{page_number}/image", tags=["Evidence & Pages"])
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


@app.get("/api/page/{page_number}/rects", tags=["Evidence & Pages"])
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


# ---------------------------------------------------------------------------
# Question Answering Endpoints
# ---------------------------------------------------------------------------

@app.post("/api/query", tags=["Question Answering"], summary="Direct JSON QA query (ideal for Swagger UI)")
@app.post("/api/ask", tags=["Question Answering"], summary="Direct JSON QA query alias")
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
        answer_payload = engine.answer(
            query=req.query,
            history=history_dicts,
            use_rerank=req.use_rerank if req.use_rerank is not None else True
        )
        return answer_payload
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"QA pipeline error: {str(e)}")


@app.post("/api/chat", tags=["Question Answering"], summary="Streaming SSE QA chat endpoint")
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
                answer_payload = await loop.run_in_executor(
                    None,
                    lambda: engine.answer(
                        query=req.query,
                        history=history_dicts,
                        use_rerank=req.use_rerank if req.use_rerank is not None else True,
                        on_status=sync_status_callback
                    )
                )
                await queue.put({"event": "answer", "data": answer_payload})
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


# ---------------------------------------------------------------------------
# Ingestion & Indexing Endpoints
# ---------------------------------------------------------------------------

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
    
    - Ingests text blocks and structured tables with bounding boxes.
    - Builds BM25 search index and dense embeddings.
    - Sets the uploaded document as the active report.
    - If `sync=True`: processes immediately and returns full stats.
    - If `sync=False` (default): launches background indexing; track progress via `/api/index/status`.
    """
    global _index_status
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files (.pdf) are supported.")

    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    dest_path = config.DATA_DIR / file.filename

    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    set_active_pdf(dest_path)

    if sync:
        try:
            stats = run_indexing_task(dest_path)
            return {
                "status": "complete",
                "message": f"Uploaded and indexed {file.filename} successfully.",
                "filename": file.filename,
                "stats": stats
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}")
    else:
        _index_status = {
            "status": "starting",
            "progress": 5,
            "message": f"Analysis queued for {file.filename}...",
            "active_doc": file.filename
        }
        background_tasks.add_task(run_indexing_task, dest_path)
        return {
            "status": "starting",
            "message": f"Uploaded {file.filename}. Indexing initiated in background.",
            "filename": file.filename,
            "check_status_url": "/api/index/status"
        }


@app.get("/api/index/status", tags=["Ingestion & Indexing"])
def get_indexing_status():
    """Returns the current status, progress percentage, and message of the document indexing pipeline."""
    return _index_status


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host=config.HOST, port=config.PORT, reload=True)
