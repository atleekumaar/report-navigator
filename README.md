# Report Navigator 🧭

> **P5 · Report Navigator — Grounded Statistics QA with Exact Page Citations & Document Evidence Highlighting**
> Built for the official Hacktoberfest Hack Day Lucknow (Problem 05 · LLM / RAG).

---

## Problem Understanding
In official government statistical reports, policy researchers, journalists, and district administrators frequently need exact figures from dense multi-hundred-page documents. Generic chatbots and naive RAG systems often hallucinate plausible numbers, confuse rows and columns across multi-page tables, and fail to provide verifiable citations. Report Navigator was designed to address this challenge by delivering the exact integer answer as printed, citing the precise 1-based PDF page index supporting the evidence, and honestly abstaining with `NOT_FOUND` when the report does not contain the requested information. This guarantees zero hallucinations, verifiable audits, and trustworthy decision-making.

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
