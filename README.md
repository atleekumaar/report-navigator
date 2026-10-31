# Report Navigator 🧭

> **P5 · Report Navigator — Grounded Statistics QA with Exact Page Citations & Document Evidence Highlighting**
> Built for the official Hacktoberfest Hack Day Lucknow (Problem 05 · LLM / RAG).

---

## Problem Understanding
In official government statistical reports, policy researchers, journalists, and district administrators frequently need exact figures from dense multi-hundred-page documents. Generic chatbots and naive RAG systems often hallucinate plausible numbers, confuse rows and columns across multi-page tables, and fail to provide verifiable citations. Report Navigator was designed to address this challenge by delivering the exact integer answer as printed, citing the precise 1-based PDF page index supporting the evidence, and honestly abstaining with `NOT_FOUND` when the report does not contain the requested information. This guarantees zero hallucinations, verifiable audits, and trustworthy decision-making.

---

## Research Foundation

Report Navigator is based on the research and evaluation described in **“Beyond Retrieval Metrics: A Reproducible Framework for End-to-End RAG Optimization”** by Atul Shukla. The paper presents a reproducible RAG evaluation framework and studies BM25 and dense retrieval, hybrid fusion, Reciprocal Rank Fusion (RRF), cross-encoder reranking, filtering, and end-to-end answer quality.

The research paper was selected for the AI conference **Advances in Foundational and Applied Artificial Intelligence** at **IIT Roorkee**. The paper is included in this repository:

[`docs/CARE_2026_Extended_Abstract.pdf`](docs/CARE_2026_Extended_Abstract.pdf)

The project applies the paper's retrieval and evaluation principles to grounded question answering over statistical PDF reports, with a focus on evidence-backed answers, page citations, and abstention when evidence is insufficient.

---

## Architecture

Report Navigator is a Python/FastAPI backend paired with a Next.js web client. The backend owns PDF ingestion, indexing, retrieval, answer generation, citation verification, and evidence rendering. The client presents the active report, streamed answers, citations, and page-level evidence.

```text
┌─────────────────────────────────────┐
│ Next.js web client                  │
│ Chat UI · citations · evidence view │
└──────────────────┬──────────────────┘
                   │ REST + Server-Sent Events
┌──────────────────▼──────────────────┐
│ FastAPI (api.py)                    │
│ document · chat · indexing · pages  │
└───────┬─────────────────────┬───────┘
        │                     │
        ▼                     ▼
┌──────────────────┐  ┌──────────────────────────┐
│ Ingestion/index  │  │ QA and evidence pipeline │
│ ingest.py        │  │ qa.py · retriever.py     │
│ index.py         │  │ highlight.py             │
└────────┬─────────┘  └─────────────▲────────────┘
         │                          │
         ▼                          │
┌───────────────────────────────────┴┐
│ PDF pages · extracted chunks ·      │
│ BM25 index · optional embeddings   │
│ data/ · index_store/               │
└────────────────────────────────────┘
```

### PDF-to-answer pipeline

1. **Upload/select a report:** The PDF is stored under `data/` and becomes the active document; the web client can also stream indexing progress.
2. **Extract evidence:** `ingest.py` extracts page text, detects headings and tables, applies OCR when configured, and records page numbers and bounding rectangles with each chunk.
3. **Build search indexes:** `index.py` writes chunk data and builds a BM25 index, plus dense embeddings when dense retrieval is enabled.
4. **Understand and retrieve:** `qa.py` prepares the question (and optional conversation history). `retriever.py` searches lexical and dense indexes, combines candidates using rank fusion, and can apply cross-encoder reranking.
5. **Answer from context:** The QA engine generates an evidence-grounded answer using the configured LLM provider, with an evidence-based local fallback when a provider is unavailable.
6. **Verify and cite:** Retrieved source material is used to validate citations and answer support; the response includes citations and retrieval trace data.
7. **Inspect evidence:** The API serves PDF pages and rendered/normalized citation rectangles so users can verify a cited passage in the original document.

### Main components

| Component | Responsibility |
| :--- | :--- |
| `api.py` | FastAPI routes for health, document metadata/PDF, chat, PDF indexing, index status, and page evidence. Swagger UI is available at `/docs`. |
| `ingest.py` | PDF text/table extraction, OCR fallback, chunking, and source-page geometry. |
| `index.py` | BM25 and optional dense index construction and persistence. |
| `retriever.py` | Hybrid lexical/dense retrieval, fusion, table context expansion, and optional reranking. |
| `qa.py` | Query handling, LLM/fallback answer generation, and citation verification. |
| `highlight.py` | Citation and chunk geometry lookup and highlighted-page rendering. |
| `src/` | Dynamic report solver, question parsing, text/table extraction helpers used by the competition workflow. |
| `web/` | Next.js chat interface, document sidebar, citations, pipeline status, and evidence panel. |

---

## Repository File Structure

This tree lists the repository's source, configuration, fixtures, and documentation. Generated environments and caches such as `.git/`, `venv/`, `web/node_modules/`, `web/.next/`, and Python cache directories are intentionally omitted.

```text
Report Navigator/
├── .github/
│   └── workflows/
│       └── ci.yml
├── data/
│   ├── .gitkeep
│   ├── active_doc.json
│   ├── questions_with_answers.jsonl
│   ├── report.pdf
│   ├── sample_answers.jsonl
│   └── sample_questions.jsonl
├── docs/
│   ├── CARE_2026_Extended_Abstract.pdf
│   ├── decisions.md
│   └── error_analysis.md
├── index_store/
│   ├── .gitkeep
│   └── metadata.json
├── models/
│   └── validated.json
├── scripts/
│   ├── build.ps1
│   ├── install.ps1
│   ├── lint.ps1
│   ├── run.ps1
│   ├── test.ps1
│   └── type-check.ps1
├── src/
│   ├── __init__.py
│   ├── question_parser.py
│   ├── solver.py
│   ├── table_engine.py
│   └── text_engine.py
├── tests/
│   ├── test_smoke.py
│   ├── test_solver.py
│   ├── test_swagger_apis.py
│   └── test_system.py
├── web/
│   ├── app/
│   │   ├── globals.css
│   │   ├── layout.tsx
│   │   ├── not-found.tsx
│   │   └── page.tsx
│   ├── components/
│   │   ├── chat/
│   │   │   ├── AnswerCard.tsx
│   │   │   ├── CitationChip.tsx
│   │   │   ├── Composer.tsx
│   │   │   ├── NotFoundCard.tsx
│   │   │   ├── PipelineStatus.tsx
│   │   │   └── StarterChips.tsx
│   │   ├── evidence/
│   │   │   ├── EvidencePanel.tsx
│   │   │   ├── PageMinimap.tsx
│   │   │   ├── TableEvidence.tsx
│   │   │   └── TraceTimeline.tsx
│   │   ├── sidebar/
│   │   │   └── Sidebar.tsx
│   │   └── ui/
│   │       └── Illustrations.tsx
│   ├── lib/
│   │   ├── api.ts
│   │   └── types.ts
│   ├── public/
│   │   └── bg-wave.jpg
│   ├── .env.example
│   ├── .eslintrc.json
│   ├── next-env.d.ts
│   ├── next.config.mjs
│   ├── package-lock.json
│   ├── package.json
│   ├── postcss.config.mjs
│   ├── tailwind.config.ts
│   └── tsconfig.json
├── .env.example
├── .gitignore
├── Makefile
├── README.md
├── Report-Navigator-Plan (1).md
├── api.py
├── cli.py
├── config.py
├── create_sample_report.py
├── eval.py
├── eval_questions.jsonl
├── highlight.py
├── index.py
├── ingest.py
├── predict.py
├── pytest.ini
├── qa.py
├── requirements.txt
├── retriever.py
├── submission.yaml
└── train.py
```

`data/report.pdf` is the tracked synthetic fixture. The optional `data/report_A.pdf`, uploaded PDFs, and generated index chunks/embeddings are local runtime data and are not included in the tree above.

---

## Quickstart (Fresh Clone)

### Prerequisites
- Python 3.11 or 3.12
- Node.js 18+ or 20+ and npm

### 1. Install Everything (Python + Web + Synthetic Fixture)
**Using Make:**
```bash
make install
```
**Using PowerShell (Windows):**
```powershell
.\scripts\install.ps1
```
**Manual Setup:**
```bash
# Python setup
python -m venv venv
# On Windows: .\venv\Scripts\activate | On Linux/Mac: source venv/bin/activate
pip install -r requirements.txt
python create_sample_report.py

# Frontend setup
cd web
npm install
cd ..
```

---

## Developer Commands

| Task | Make Command | Windows PowerShell Script | Description |
| :--- | :--- | :--- | :--- |
| **Install** | `make install` | `.\scripts\install.ps1` | Installs Python & Web dependencies, generates synthetic PDF fixture |
| **Test** | `make test` | `.\scripts\test.ps1` | Runs full pytest suite (18 unit + smoke tests) |
| **Lint** | `make lint` | `.\scripts\lint.ps1` | Runs Next.js ESLint (`next lint`) |
| **Type Check** | `make type-check` | `.\scripts\type-check.ps1` | Runs TypeScript compiler check (`tsc --noEmit`) |
| **Build** | `make build` | `.\scripts\build.ps1` | Compiles optimized Next.js production bundle |
| **Run API** | `make run-api` | `.\scripts\run.ps1 -Target api` | Starts FastAPI backend on `http://127.0.0.1:8000` |
| **Run Web** | `make run-web` | `.\scripts\run.ps1 -Target web` | Starts Next.js development server on `http://127.0.0.1:3000` |

---

## Synthetic Fixture PDF & Test Isolation
Tests do not require the proprietary `report_A.pdf` to run:
- A self-contained 5-page synthetic statistical report with 2 tables and prose sections is generated automatically by `create_sample_report.py` at `data/report.pdf`.
- Tests targeting `report_A.pdf` use `@pytest.mark.skipif` and cleanly skip when `report_A.pdf` is not present in `data/`.
- The configuration cleanly defaults to `data/report.pdf` whenever `report_A.pdf` is absent.

---

## Configuration & Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Key settings:
- `PDF_PATH`: Path to active PDF report (defaults to `data/report.pdf`)
- `NEXT_PUBLIC_API_URL`: Backend API base URL (defaults to `http://127.0.0.1:8000`)
- `LLM_PROVIDER`: `anthropic`, `openai`, or `gemini`
- `USE_DENSE`: `1` (enabled) or `0` (disabled, uses BM25 only)
- `USE_RERANK`: `1` (enabled) or `0` (disabled)

---

## Validation & Competition CLI

### Run Validation (train.py)
```bash
python train.py --data-dir data --out models/
```

### Run Prediction (predict.py)
```bash
python predict.py --pdf data/report.pdf --questions data/sample_questions.jsonl --output data/predicted_answers.jsonl
```

### Run Automated Evaluator (eval.py)
```bash
python eval.py --gold data/sample_questions.jsonl --pred data/predicted_answers.jsonl -v
```

---

## Data & Licences
- **Challenge Dataset**: `report_A.pdf` (Ministry of Road Transport and Highways, Government of India, "Road Accidents in India 2023", Open Government Data Licence - India).
- **Synthetic Test Dataset**: Generated via `create_sample_report.py` (Public Domain / CC0).
- **Software Dependencies**: PyMuPDF (GNU AGPL v3 / Commercial), rank-bm25 (Apache-2.0), FastAPI (MIT), Next.js (MIT), Tailwind CSS (MIT).
- **Licensing Notice**: PyMuPDF is licensed under GNU AGPL v3. For proprietary commercial distribution without open-sourcing backend code, obtain a commercial PyMuPDF licence or replace with an Apache/MIT PDF extractor (e.g. `pypdf` or `pdfplumber`).
- **Codebase Licence**: Released under the MIT Licence in the Hacktoberfest spirit.

---

## Team
- **Atul Kumar** — Team Lead, Architecture Design, RAG Pipeline & Web UI Development.
- **Report Navigator Team** — Data Analysis, Error Analysis, Benchmark Evaluation & Quality Assurance.
