# Report Navigator 🧭

> **Grounded Statistics QA with Page Citations & Document Evidence Highlighting**
> Built for long government statistical bulletins and multi-hundred-page economic reports.

Report Navigator is an evidence-grounded RAG (Retrieval-Augmented Generation) system specifically engineered for statistical and economic reports. It answers numerical and factual queries, cites the exact page number, highlights the verbatim quote or table row on the original PDF page, and features an **in-code verification layer** to prevent hallucinations.

---

## 🌟 Differentiators & Judge Checklist

| Requirement | How Report Navigator Achieves It |
|---|---|
| **Pinpoint Precision** | Hybrid search (BM25 with decimal & comma normalization + BGE dense embeddings) merged via Reciprocal Rank Fusion (RRF). |
| **Cross-Encoder Reranker** | MiniLM cross-encoder reranks top candidates with automatic **sibling table part expansion** so table headers are never lost. |
| **Exact Page Citations** | Every chunk is strictly bounded to a single page; displays both printed page and PDF index (e.g. `p.43 (PDF p.45)`). |
| **Verbatim Quote Verification** | In-code anti-hallucination layer checks that every cited quote and number exists in the source chunk before presenting it to the user. |
| **Forced Abstention ("Not Found")** | Overrides speculative model responses if citations fail verification or if data is absent. |
| **PDF Evidence Highlighting** | Backend renders 1.6x zoom page PNGs with warm yellow highlighting burned into the cited text or table row band. |
| **3-Zone Interactive Web UI** | Modern dark-first Next.js UI with live streaming pipeline stepper, interactive table viewer, retrieval trace, and page minimap. |

---

## 📐 Architecture Pipeline

```
              OFFLINE PIPELINE (Run once per report)
 ┌────────────┐   ┌────────────────────────┐   ┌────────────────────────┐
 │ Report PDF │──►│ 1. INGEST              │──►│ 2. INDEX               │
 └────────────┘   │ Text + Tables + BBoxes │   │ BM25 + BGE Dense Vecs  │
                  └────────────────────────┘   └────────────────────────┘

              ONLINE PIPELINE (Per question / follow-up)
 ┌──────────┐  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐  ┌───────────┐  ┌──────────────┐
 │ Question │─►│ 3. REWRITE  │─►│ 4. HYBRID    │─►│ 5. RERANK   │─►│ 6. LLM    │─►│ 7. VERIFY    │
 │ + History│  │ Standalone  │  │ BM25 + Dense │  │ Cross-Enc   │  │ Grounded  │  │ Quotes &     │
 └──────────┘  │ + Keywords  │  │ + RRF Fusion │  │ Top 8 + Sib │  │ Response  │  │ Numbers      │
               └─────────────┘  └──────────────┘  └─────────────┘  └───────────┘  └──────┬───────┘
                                                                                         │
                                                ┌────────────────────────────────────────┴───────┐
                                                │ 8. MODERN WEB UI & EVIDENCE VIEWER             │
                                                │ Answer + [p.43] chips + Highlighted PDF viewer │
                                                └────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### 1. Prerequisites
- **Python 3.11 or 3.12**
- **Node.js 18+ & npm**
- Anthropic API Key (or OpenAI / Gemini key)

### 2. Backend Setup
```bash
# Clone the repository
git clone <repo-url>
cd "Report Navigator"

# Activate Python virtual environment
py -3.12 -m venv venv
.\venv\Scripts\activate   # Windows (or: source venv/bin/activate on Linux/Mac)

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and enter your ANTHROPIC_API_KEY
```

### 3. Generate Sample Report & Build Index
```bash
# Generate the sample 2024 statistical report
python create_sample_report.py

# Ingest and create chunks
python ingest.py

# Build BM25 and dense embedding indexes
python index.py
```

### 4. Start the Backend API Server
```bash
python -m uvicorn api:app --host 127.0.0.1 --port 8000 --reload
```
The FastAPI server will be available at `http://127.0.0.1:8000`. You can inspect the interactive OpenAPI documentation at `http://127.0.0.1:8000/docs`.

### 5. Start the Next.js Frontend
In a new terminal window:
```bash
cd web
npm install
npm run dev
```
Open `http://localhost:3000` in your browser.

---

## 🖥️ Command Line Interface (Emergency Backup)
If you need to query the report directly from the terminal without launching the web server:
```bash
python cli.py
```

---

## 📊 Evaluation & Metrics
Run the evaluation suite against ground-truth statistical questions:
```bash
python eval.py
```
This tests:
1. **Retrieval Hit@8**: Is the ground-truth page retrieved in the top candidates?
2. **Citation Page Accuracy**: Is the correct page cited in the final answer?
3. **Answer Correctness**: Are all expected values and percentages present?
4. **Abstention Accuracy**: Does the system abstain ("not found") on unanswerable questions instead of hallucinating?

---

## 📁 Repository Structure
```
├── config.py              # Central settings and hyperparameters
├── ingest.py              # PDF block parser, table extractor & bbox tracker
├── index.py               # BM25 and Dense vector indexer
├── retriever.py           # Hybrid search, RRF fusion, page pinning & reranker
├── qa.py                  # Query rewrite, prompt contract & verification engine
├── highlight.py           # PyMuPDF page highlighter & image renderer
├── api.py                 # FastAPI backend with Server-Sent Events (SSE)
├── cli.py                 # Terminal interactive QA interface
├── eval.py                # Automated accuracy benchmark
├── eval_questions.jsonl   # Ground truth test dataset
├── create_sample_report.py# Generates test government statistics PDF
├── requirements.txt       # Python dependencies
├── .env.example           # Environment template
├── data/                  # Source PDF documents
├── index_store/           # Cached chunks, BM25 index & vector embeddings
└── web/                   # Next.js 14 Web Application
    ├── app/               # App Router pages and layout
    ├── components/
    │   ├── chat/          # AnswerCard, CitationChip, PipelineStatus, Composer
    │   ├── evidence/      # EvidencePanel, TableEvidence, TraceTimeline, Minimap
    │   └── sidebar/       # Sidebar, Document Card & Upload Trigger
    └── lib/               # Types and SSE API client
```

