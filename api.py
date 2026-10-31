import asyncio
import json
import os
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
import fitz

import config
from ingest import ingest_pdf
from index import build_index, Indexer
from retriever import HybridRetriever
from qa import QAEngine
from highlight import render_highlighted_page_png, get_normalized_page_rects

app = FastAPI(
    title="Report Navigator API",
    description="Backend API for Report Navigator RAG System",
    version="1.0.0"
)

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global engine instances
_qa_engine: Optional[QAEngine] = None
_index_status = {"status": "idle", "progress": 0, "message": "Ready"}

def get_qa_engine() -> QAEngine:
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

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    query: str
    history: Optional[List[ChatMessage]] = []
    use_rerank: Optional[bool] = True

@app.get("/api/health")
def health_check():
    return {"status": "ok", "pdf_exists": config.PDF_PATH.exists()}

@app.get("/api/doc")
def get_document_metadata():
    """Returns metadata about the active report: title, page count, table count, starter questions."""
    pdf_path = config.PDF_PATH
    if not pdf_path.exists():
        return {
            "title": "No Report Loaded",
            "filename": "",
            "page_count": 0,
            "table_count": 0,
            "starter_questions": [
                "What is the overall unemployment rate in the latest period?",
                "Which state recorded the highest female labour force participation?",
                "What are the key findings in Chapter 3?",
                "Compare the youth unemployment rate between 2023 and 2024."
            ]
        }

    try:
        doc = fitz.open(str(pdf_path))
        page_count = len(doc)
        title = doc.metadata.get("title") or pdf_path.stem.replace("_", " ").title()
        doc.close()
    except Exception:
        page_count = 0
        title = pdf_path.stem

    table_count = 0
    if config.CHUNKS_FILE.exists():
        with open(config.CHUNKS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if '"type": "table"' in line:
                    table_count += 1

    return {
        "title": title,
        "filename": pdf_path.name,
        "page_count": page_count,
        "table_count": table_count,
        "starter_questions": [
            "What was the overall unemployment rate in 2024?",
            "Which state has the highest female labour force participation?",
            "Compare male vs female unemployment in Kerala.",
            "What was the LFPR for youth in 2023?"
        ]
    }

@app.get("/api/pdf")
def get_pdf():
    """Stream original PDF for in-browser PDF viewer."""
    if not config.PDF_PATH.exists():
        raise HTTPException(status_code=404, detail="PDF not found on server")
    return FileResponse(
        str(config.PDF_PATH),
        media_type="application/pdf",
        filename=config.PDF_PATH.name
    )

@app.get("/api/page/{page_number}/image")
def get_page_image(
    page_number: int,
    quote: Optional[str] = Query(None),
    is_table: Optional[bool] = Query(False),
    zoom: Optional[float] = Query(1.6),
    chunk_id: Optional[str] = Query(None, alias="chunk")
):
    """
    Returns PNG image of the requested page with the cited passage/table row highlighted.
    """
    if not config.PDF_PATH.exists():
        raise HTTPException(status_code=404, detail="PDF not found")

    chunk_rects = None
    if chunk_id:
        engine = get_qa_engine()
        for ch in engine.retriever.indexer.chunks:
            if ch.get("id") == chunk_id:
                chunk_rects = ch.get("rects")
                break

    try:
        png_bytes = render_highlighted_page_png(
            pdf_path=config.PDF_PATH,
            page_number=page_number,
            quote=quote,
            chunk_rects=chunk_rects,
            is_table=is_table,
            zoom=zoom
        )
        return Response(content=png_bytes, media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/page/{page_number}/rects")
def get_page_rects(
    page_number: int,
    quote: Optional[str] = Query(None),
    is_table: Optional[bool] = Query(False),
    chunk_id: Optional[str] = Query(None, alias="chunk")
):
    """
    Returns normalized bounding box coordinates for client-side canvas highlighting.
    """
    if not config.PDF_PATH.exists():
        raise HTTPException(status_code=404, detail="PDF not found")

    chunk_rects = None
    if chunk_id:
        engine = get_qa_engine()
        for ch in engine.retriever.indexer.chunks:
            if ch.get("id") == chunk_id:
                chunk_rects = ch.get("rects")
                break

    try:
        data = get_normalized_page_rects(
            pdf_path=config.PDF_PATH,
            page_number=page_number,
            quote=quote,
            chunk_rects=chunk_rects,
            is_table=is_table
        )
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
async def chat_sse_stream(req: ChatRequest):
    """
    Server-Sent Events stream for interactive chat.
    Streams status updates during pipeline execution, followed by the final answer JSON.
    """
    engine = get_qa_engine()
    queue = asyncio.Queue()

    def sync_status_callback(step: str, message: str):
        queue.put_nowait({"event": "status", "data": {"step": step, "message": message}})

    async def event_generator():
        # Task runner for QA answer execution with guaranteed completion
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

def run_background_indexing(file_path: Path):
    global _index_status, _qa_engine
    try:
        _index_status = {"status": "ingesting", "progress": 25, "message": "Parsing text, tables, and bounding boxes..."}
        ingest_pdf(file_path)

        _index_status = {"status": "indexing", "progress": 60, "message": "Building BM25 and dense embeddings..."}
        build_index()

        _index_status = {"status": "complete", "progress": 100, "message": "Indexing complete and ready to query!"}
        _qa_engine = None  # Reload engine on next query
    except Exception as e:
        _index_status = {"status": "error", "progress": 0, "message": f"Indexing failed: {str(e)}"}

@app.post("/api/index")
async def upload_and_index(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Upload a new PDF report and trigger background ingestion & indexing."""
    global _index_status
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    dest_path = config.DATA_DIR / file.filename
    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    config.PDF_PATH = dest_path
    _index_status = {"status": "starting", "progress": 5, "message": "Starting document analysis..."}
    background_tasks.add_task(run_background_indexing, dest_path)
    return {"message": f"Uploaded {file.filename}. Indexing initiated.", "status": "starting"}

@app.get("/api/index/status")
def get_indexing_status():
    return _index_status

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host=config.HOST, port=config.PORT, reload=True)

