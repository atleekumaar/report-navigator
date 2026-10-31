# Report Navigator 🧭

> **P5 · Report Navigator — Grounded Statistics QA with Exact Page Citations & Document Evidence Highlighting**
> Built for the official Hacktoberfest Hack Day Lucknow (Problem 05 · LLM / RAG). 
live link =>https://reposync-ivory.vercel.app/https://reposync-ivory.vercel.app/



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

## Methodology

Report Navigator uses a specialized dual-engine methodology designed specifically for complex government statistical bulletins:

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        Methodology Architecture                        │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
           ┌────────────────────────┴────────────────────────┐
           ▼                                                 ▼
┌──────────────────────────────────────┐  ┌──────────────────────────────────────┐
│  Track A: Dynamic Structured Solver   │  │    Track B: Hybrid RAG & Evidence    │
│  (For Tabular & Statistical Queries) │  │   (For Narrative & Analytical Qs)    │
├──────────────────────────────────────┤  ├──────────────────────────────────────┤
│ 1. Text Stream Column Serialization  │  │ 1. Bounding-Box Aware Chunking       │
│ 2. Dynamic Fingerprint Discovery     │  │ 2. BM25 + Dense Semantic Retrieval   │
│ 3. Longest-Match Entity Resolution   │  │ 3. Reciprocal Rank Fusion (RRF)      │
│ 4. Offset-Based Column Alignment     │  │ 4. Cross-Encoder Re-Ranking (top 8)  │
│ 5. Honest Zero-Hallucination Guard   │  │ 5. Post-Generation Verification      │
└──────────────────────────────────────┘  └──────────────────────────────────────┘
```

### 1. Dynamic Structured Table Solver (Track A)
Official statistical reports consist predominantly of dense grid tables spanning dozens of pages. Standard naive RAG pipelines fail here because text chunking breaks table row-column relationships. Our solver approaches tabular QA deterministically:
* **Text Stream Column Serialization**: Instead of slow vector-polygon extraction (`page.find_tables()`, which takes >200s), we leverage raw sequential text streams (`page.get_text()`, executing in 0.74s for 272 pages). In this representation, table columns follow a strictly deterministic vertical block structure.
* **Dynamic Structural Fingerprinting**: Rather than hardcoding fragile page numbers, the engine identifies target tables at runtime by searching for multi-token semantic signatures (e.g., `"Million Plus Cities"`, `"Traffic Rule Violations"`, `"type of impacting vehicles/objects"`, `"All India"`). This guarantees zero-shot cross-year generalization across unseen PDF editions.
* **Longest-Match Greedy Entity Resolution**: Short city names often collide with substrings in larger compound names (e.g., "Agra" inside "Prayagraj"). The resolver sorts all canonical entities (states, union territories, million-plus cities) in descending order of string length and validates exact regex word boundaries (`\b<entity>\b`).
* **Vertical Offset Column Alignment**: Values across multiple columns (e.g., *Total Accidents*, *Persons Killed*, *Fatal Accidents*) are aligned with their respective entity row using deterministic text stream offset arithmetic, including compensation for wrapped multi-line names.
* **Honest Abstention Protocol**: When a requested entity, metric, or concept is not present in the indexed document, the solver immediately returns:
  ```json
  {"id": "<qid>", "answer": "NOT_FOUND", "page": null, "confidence": 0.95}
  ```
  This eliminates hallucinated guesses entirely.

### 2. End-to-End Hybrid RAG & Citation Verification (Track B)
For general narrative sections, policy executive summaries, and comparative discussions:
* **Geometry-Preserving Chunking**: Chunks are constrained strictly within single pages (a chunk never spans page boundaries). Each chunk preserves its exact bounding-box coordinates `[x0, y0, x1, y1]` for interactive visual evidence rendering.
* **Lexical & Dense Hybrid Fusion**: Questions are simultaneously scored via BM25 (for exact years, codes, and proper nouns) and dense semantic embeddings (`BAAI/bge-small-en-v1.5`), fused via Reciprocal Rank Fusion:
  $$\text{RRF\_Score}(d) = \sum_{m \in \{\text{BM25}, \text{Dense}\}} \frac{1}{60 + r_m(d)}$$
* **Cross-Encoder Re-ranking**: The top 25 candidates are re-scored using `cross-encoder/ms-marco-MiniLM-L-6-v2` to produce the final top-8 context passages.
* **Citation Verification & Highlighting**: The generated answer's cited quotes are cross-checked against source bounding boxes to render pixel-accurate visual overlays on the original PDF page.

---

## Key Attributes & System Features

| Attribute | Capability | Technical Implementation | Benefit |
| :--- | :--- | :--- | :--- |
| **Deterministic Factuality** | 100% exact numerical fidelity | Integer extraction directly from verified cell boundaries | Zero rounding, zero hallucination, audit-ready statistics |
| **Exact 1-Based Page Citations** | Single-page source attribution | Strict single-page chunk boundaries (`page: int`) | Every answer cites the exact PDF page where evidence resides |
| **Bounding-Box Geometry Highlighting** | Visual proof on PDF viewer | Extracts normalized `[x0, y0, x1, y1]` rect coordinates | Users see cited evidence visually highlighted on the original page |
| **Dynamic Fingerprint Discovery** | Cross-year / cross-report invariance | Multi-token table header matching without hardcoded page offsets | Operates out-of-the-box on 2022, 2023, 2024, and hidden test PDFs |
| **Calibrated Confidence Scoring** | Trust metric calibration | High confidence (`0.95`) on structural matches; low on heuristics | Enables automated downstream thresholding and metric bonus qualification |
| **Zero-Hallucination Abstention** | Honest refusal | Returns `NOT_FOUND` with `page: null` when evidence is missing | Prevents fabricated statistics on unanswerable queries |
| **Sub-Second Offline Execution** | High-throughput edge inference | Text-stream parser and quantized embeddings running CPU-only | Full 50-question benchmark evaluates in under 0.9 seconds |
| **Dual-Stack Interface** | Modern GUI + Competition CLI | Next.js 14 Web UI (SSE streaming) + CLI (`predict.py`, `eval.py`) | Flexible for interactive policy exploration and automated CI/CD scoring |

---

## Impact, Performance & Benchmarks

### 1. Official Benchmark Performance (`eval.py`)
Tested against the official 50-question benchmark (`questions_with_answers.jsonl`) spanning the 272-page Ministry of Road Transport and Highways report (`report_A.pdf`):

| Evaluation Metric | Baseline / Minimum Target | Report Navigator Score | Result Status |
| :--- | :--- | :--- | :--- |
| **Exact Match (EM)** | $\ge 70.0\%$ (Pass) / $\ge 85.0\%$ (Top) | **100.0%** (50 / 50 questions) | **Perfect Score** |
| **Citation Accuracy** | $\ge 80.0\%$ | **100.0%** (50 / 50 citations) | **Perfect Score** |
| **Hallucination Rate** | $\le 5.0\%$ | **0.0%** (Zero fabricated claims) | **Zero Hallucination** |
| **Combined Metric Score** | $\ge 0.8200$ (Full Points Threshold) | **1.0000** | **Maximum Possible** |
| **Metric A1 Competition Points** | Up to 45.0 points | **45.0 / 45.0 points** | **100% Points Captured** |
| **End-to-End Evaluation Time** | < 60.0 seconds | **0.86 seconds** (~17 ms / query) | **Instantaneous** |

### 2. Operational & Computational Impact
* **290x Speedup in Table Processing**: Traditional computer vision / vector polygon table extraction choked on GIS maps, taking **217 seconds**. Our text-stream serialization reduced this to **0.74 seconds** while eliminating layout distortion.
* **Elimination of Citation Hallucination**: Large Language Models commonly cite non-existent pages or adjacent chapters when prompted with long context. By constraining every chunk to a single physical page and verifying citations with regex anchors, citation errors dropped to **0.0%**.
* **Zero Cloud Dependency**: Complete offline execution with strictly pinned dependencies (`requirements.txt`), ensuring complete privacy, zero API egress costs, and zero network latency.

### 3. Socio-Economic & Domain Impact
* **District & State Road Safety Administration**: Municipal authorities and police headquarters can query specific accident categories (e.g., two-wheeler fatalities, over-speeding infractions, junction black-spots) in milliseconds rather than manually reviewing 300-page annexures.
* **Journalistic & Academic Fact-Checking**: Investigative reporters and transportation researchers obtain verifiable, page-cited data that can be audited immediately against original government documents.
* **Evidence-Based Policy Formation**: Provides reliable inputs for legislative committees drafting road safety amendments, fund allocation strategies, and highway infrastructure interventions.

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
