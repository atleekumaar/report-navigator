# Report Navigator: Full Architecture and Build Plan

A RAG system that answers questions about a long government statistics report, cites the page every answer comes from, and shows the evidence on the original page.

---

## 1. What we are actually building

**Input:** one long statistics PDF (hundreds of pages: text, tables, charts), provided on hack day.
**Output:** for any question, an answer + page references + the exact passage/table row highlighted.

**What judges will check (design everything around this):**

| Requirement | How we satisfy it |
|---|---|
| Finds the right part of the report | Hybrid search (keyword + semantic) + reranking |
| Writes a correct answer | LLM answers only from retrieved passages |
| Cites the page | Every chunk belongs to exactly one page, so every citation is exact |
| Simple interface | Modern web app (Next.js chat + split PDF evidence viewer), CLI as backup |
| Bonus: numbers from tables | Tables extracted as their own structured chunks |
| Bonus: "not found" instead of guessing | Model abstains + code verifies quotes |
| Bonus: highlight exact passage/table | Render the PDF page with the quote highlighted |

**Core design principle:** *trust over fluency.* A wrong number without a source is worse than "not found in the report". Every layer is built to reduce hallucination.

---

## 2. High-level architecture

```
                  OFFLINE PIPELINE (run once per report)
 ┌────────────┐   ┌─────────────────────┐   ┌──────────────────────┐
 │  Report    │──►│  1. INGEST          │──►│  2. INDEX            │
 │  PDF       │   │  text + tables +    │   │  BM25 (keyword)      │
 └────────────┘   │  page + bbox +      │   │  Dense embeddings    │
                  │  section headings   │   │  chunks.jsonl store  │
                  └─────────────────────┘   └──────────────────────┘

                  ONLINE PIPELINE (per question)
 ┌──────────┐  ┌───────────┐  ┌────────────┐  ┌──────────┐  ┌────────────┐  ┌──────────┐  ┌──────────┐
 │ Question │─►│ 3.REWRITE │─►│ 4.HYBRID   │─►│ 5.RERANK │─►│ 6.GROUNDED │─►│ 7.VERIFY │─►│ 8.UI     │
 │ (+chat   │  │ standalone│  │ RETRIEVE   │  │ cross-   │  │ ANSWER     │  │ quotes + │  │ answer + │
 │ history) │  │ + keyword │  │ BM25+dense │  │ encoder  │  │ (LLM, forced│  │ numbers  │  │ page refs│
 └──────────┘  │ variants  │  │ + RRF      │  │ top 8    │  │ JSON/tool) │  │ checked  │  │ +highlight│
               └───────────┘  └────────────┘  └──────────┘  └────────────┘  └──────────┘  └──────────┘
```

---

## 3. Tech stack

| Layer | Choice | Why |
|---|---|---|
| PDF parsing | PyMuPDF | Fast; gives text blocks, table detection, **bounding boxes** (needed for highlighting) |
| Scanned pages | Tesseract OCR via PyMuPDF (fallback only) | Some gov PDFs have image pages |
| Keyword search | `rank-bm25` | Exact matching for years, state names, table numbers |
| Embeddings | `BAAI/bge-small-en-v1.5` (upgrade: `bge-m3` for Hindi) | Small, fast, good quality, runs on CPU |
| Fusion | Reciprocal Rank Fusion (RRF) | Merges two rankings with no score calibration |
| Reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Large precision boost on the final top 8 |
| LLM (answer) | Claude Sonnet | Strong grounded reasoning over tables |
| LLM (rewrite) | Claude Haiku | Cheap and fast for query rewriting |
| Backend API | FastAPI + Server-Sent Events | Async, streams pipeline progress live, serves PDF and page images |
| Frontend | Next.js (App Router) + TypeScript + Tailwind CSS + shadcn/ui | Modern, fast to build, polished components out of the box |
| Motion | Framer Motion | Smooth transitions and the highlight pulse |
| PDF viewer | `react-pdf` (pdf.js) | Real zoomable page view with highlight overlay on the cited passage |
| Fonts / icons | Inter + JetBrains Mono (numbers), Lucide icons | Clean reading, tabular numbers look right in stats answers |
| Storage | Local files (JSONL + npy + pickle) | No DB setup needed; fine for one report |

No vector database is needed. One report means a few thousand chunks; NumPy handles it instantly.

---

## 4. Stage-by-stage design

### Stage 1: Ingestion (the most important stage)

Everything downstream depends on chunk quality. Spend the most hack-day time here.

**Rules:**
1. **A chunk never crosses a page.** This makes page citation exact.
2. **Tables are separate chunks** in markdown, not flattened text.
3. **Header/footer furniture is removed** (running titles, page numbers) but the printed page number is captured first.
4. **Each chunk knows its section** (nearest heading above it).
5. **Each chunk stores its bounding boxes** for highlighting later.

**Chunk schema:**

```json
{
  "id": "p0003-t00003",
  "doc": "report.pdf",
  "page": 45,
  "label": "43",
  "type": "text | table",
  "section": "Chapter 3: Unemployment",
  "text": "...",
  "rects": [[x0, y0, x1, y1]],
  "table_id": "p45-t0",
  "part": 0
}
```

`page` = PDF index, `label` = printed page number. They often differ (cover pages, roman numerals). **Show both** in the UI: `p.43 (PDF p.45)`.

**Text chunking:**
- Walk text blocks in reading order.
- Pack blocks into chunks of about 1100 characters.
- Split over-long blocks on sentence boundaries.
- Never merge across pages.

**Table handling (key for the bonus):**
- Detect with `page.find_tables()`.
- Build cell text from words inside each cell bounding box (more reliable than the built-in `extract()`, which mangled decimals like `7.1` in testing).
- **Multi-row headers:** keep absorbing rows that contain text but no numbers (max 3), then merge them into one header per column.
- Capture the **caption** (closest short text block above the table, e.g. "Table 3.1: ...").
- Render as markdown:

```
Table: Table 3.1: Unemployment rate by state, 2024 (per cent)
| State | Male | Female | Total |
| --- | --- | --- | --- |
| Kerala | 7.1 | 14.3 | 9.9 |
```

- Large tables are split into parts of about 14 rows, **repeating the header in every part**, and sharing a `table_id` so siblings can be pulled together at query time.
- Remove table text from the normal text chunks so content is not duplicated.

**Edge cases to check on the real PDF in the first 30 minutes:**

| Check | If it fails |
|---|---|
| Are tables detected? | Try `find_tables(strategy="text")` for tables without ruling lines |
| Is it scanned? | Install Tesseract; OCR fallback triggers on pages with under 30 characters |
| Two-column layout? | Reading order from `sort=True`; verify visually on 3 pages |
| Printed vs PDF page numbers differ? | Already stored both; decide which to show first |
| Charts holding key numbers? | Use vision fallback (Section 9) |
| Hindi or mixed language? | Switch to multilingual embedder |

---

### Stage 2: Indexing

- **BM25:** tokenise each chunk's `section | page | type + text`. The tokenizer keeps decimals and also adds comma-stripped versions of numbers (`1,234` also indexed as `1234`).
- **Dense:** embed the same contextual text, normalised, saved as a `.npy` matrix.
- Prepending the section and page into the indexed text helps both retrievers (a query like "unemployment" matches chunks under the Unemployment chapter).

---

### Stage 3: Query rewriting

Handles chat follow-ups ("and for 2023?", "what about women?").

Input: latest question + last 6 messages. Output (JSON):

```json
{"standalone": "What was the female unemployment rate in Kerala in 2023?",
 "keywords": ["Kerala female unemployment rate 2023 table", "joblessness women Kerala 2023"]}
```

The standalone question goes to the final LLM; all three strings go to retrieval. If the rewrite fails, fall back to the raw question.

---

### Stage 4: Hybrid retrieval

For each query string:
1. BM25 top 30
2. Dense top 30
3. **RRF fusion:** score = sum of 1/(60 + rank) over all rankings

Extras:
- **Page pinning:** if the question says "page 45", boost that page's chunks.
- Candidate pool: top 30 fused chunks.

Why both retrievers: stats questions contain exact tokens (years, state names, "per cent") where BM25 wins, but users also paraphrase ("jobless rate" versus "unemployment rate") where embeddings win.

---

### Stage 5: Reranking

- A cross-encoder scores (question, chunk) pairs, and the top 8 go to the LLM.
- **Sibling expansion:** if a retrieved chunk is a table part, add other parts of the same table (max 3 extra) so the header and neighbouring rows are not lost.
- Make rerank toggleable (UI checkbox) so you can compare with and without during tuning.

---

### Stage 6: Grounded answer generation

Each source is labelled for the model:

```
[S3] (p.43 (PDF p.45) | table | section: Chapter 3: Unemployment)
Table: Table 3.1 ...
```

The model **must** respond through a forced tool call `submit_answer`:

```json
{
  "found": true,
  "answer": "Kerala's total unemployment rate in 2024 was 9.9 per cent [S3].",
  "calculation": "",
  "confidence": "high",
  "citations": [{"source_id": "S3", "quote": "| Kerala | 7.1 | 14.3 | 9.9 |"}]
}
```

**System prompt rules (the contract):**
1. Use only the numbered sources; cite `[S#]` after every claim.
2. Copy numbers exactly with unit and period; never round or convert unless asked.
3. Any arithmetic goes in `calculation` with inputs and formula.
4. For tables, confirm row label, column header, unit and period before reading a value; check footnotes.
5. If the sources do not contain the answer, return `found=false`. Never guess or use outside knowledge. For partial answers, say what is missing.
6. Each citation needs a **verbatim** quote (max 200 characters); for tables, copy the whole row.
7. If sources conflict (revised figures), report both with pages.
8. Lead with the answer, then at most one line of context.

---

### Stage 7: Verification (anti-hallucination layer)

Runs in code, after the LLM, before anything is shown:

| Check | Action on failure |
|---|---|
| Is each cited quote actually inside the cited chunk? (whitespace and table-pipe tolerant; all numbers in the quote must also be in the chunk) | Mark citation unverified |
| Is there at least one verified citation? | If not: override answer to "Not found in the report" |
| Do numbers in the answer appear anywhere in the retrieved sources? (skipped when a `calculation` is given) | Show a red "check these numbers" warning |

This is what makes the "not found" bonus real and not just a prompt instruction.

---

### Stage 8: API layer + modern web UI

#### 8.1 Backend API (FastAPI)

| Endpoint | Purpose |
|---|---|
| `POST /api/chat` (SSE stream) | Runs the pipeline; streams events `status` (rewriting, searching, reranking, reading, verifying) then one `answer` event with the final JSON |
| `GET /api/doc` | Report metadata: title, page count, table count, suggested starter questions |
| `GET /api/pdf` | Streams the PDF for the in-browser viewer |
| `GET /api/page/{n}/image?chunk=...&quote=...` | PNG of page n with the passage highlighted (v1, fastest to ship) |
| `GET /api/page/{n}/rects?quote=...` | Highlight rectangles as normalised coordinates for a crisp overlay on the pdf.js canvas (v2) |
| `POST /api/index` + `GET /api/index/status` | Upload a PDF, run ingest + index as a background job, poll progress |

The retrieval/QA code stays unchanged; `api.py` is a thin wrapper around `qa.answer()`.
Streaming note: the answer arrives as one structured JSON (forced tool call), so the UI streams **pipeline progress** live and plays a typewriter animation on the answer text.

#### 8.2 Layout (three zones)

```
┌──────────┬───────────────────────────────────┬─────────────────────────────┐
│ Sidebar  │            Chat                   │   Evidence panel            │
│          │                                   │                             │
│ Logo     │  Empty state: doc stats +         │  Tabs: Page | Passage |     │
│ Report   │  4 starter-question chips         │        Trace                │
│ card     │                                   │                             │
│ Chat     │  User bubble                      │  PDF page viewer, jumps to  │
│ history  │  Answer card:                     │  the cited page, highlight  │
│ Settings │   text + [p.43] citation chips    │  pulses; prev/next citation │
│ Theme    │   verified / confidence badges    │  Zoom, open full PDF        │
│          │   calculation block               │                             │
│          │  Composer (⌘K to focus)           │  Page minimap strip         │
└──────────┴───────────────────────────────────┴─────────────────────────────┘
Mobile: sidebar becomes a drawer, evidence panel becomes a bottom sheet.
```

#### 8.3 Key components

1. **Answer card:** answer text with inline **citation chips** (`p.43`); clicking a chip opens the evidence panel on that page; hovering shows a preview card with the quoted snippet.
2. **Badges:** green "Verified" (quote found in source), confidence (high/medium/low), amber "Check numbers" when the number check fires.
3. **Table evidence:** render the cited table as a real HTML table with the cited row highlighted (plus the highlighted page image/overlay), so numbers are readable and copyable.
4. **Calculation block:** monospace, shows inputs and formula for derived numbers.
5. **Not-found state:** distinct card (muted amber, search-off icon): "Not found in the report", what was searched, and a "Nearest pages" list the user can open.
6. **Live pipeline status:** animated step list while waiting (Understanding question, Searching report, Reranking, Reading pages, Verifying citations); doubles as a skeleton loader and shows the system is doing real work.
7. **Retrieval trace tab:** timeline of the stages with timings, rewritten queries, and the top retrieved chunks (page, type, score).
8. **Page minimap:** thin vertical strip representing the whole report with ticks on retrieved pages and bright ticks on cited pages; click to jump. Shows judges the "needle in a haystack" being found.
9. **Composer:** auto-growing input, send on Enter, starter chips, follow-up suggestions after each answer.
10. **Utilities:** copy answer with citations, thumbs up/down (log to a JSON file for the eval set), light/dark toggle, export chat as Markdown.

#### 8.4 Design system

| Token | Value |
|---|---|
| Theme | Dark-first with a clean light mode |
| Background / surface | `#0B0D12` / `#12151C` with 1px borders at about 8% white |
| Accent | Indigo-violet (`#6366F1` to `#8B5CF6` gradient, used sparingly) |
| Semantic colours | Verified green `#22C55E`, warning amber `#F59E0B`, error red `#EF4444` |
| Highlight colour | Warm yellow at 35-40% opacity (matches the page highlight) |
| Type | Inter for UI, JetBrains Mono (tabular numerals) for numbers and calculations |
| Shape | 12-16px radius, soft shadows, subtle glass blur on the evidence panel header |
| Motion | 150-250ms ease-out; staggered step reveal; highlight pulse on arrival; respects `prefers-reduced-motion` |
| Accessibility | Full keyboard navigation, visible focus rings, AA contrast, aria-live for streamed status |

Style references to aim for: the clean density of Linear, the answer-with-sources pattern of Perplexity, the split document view of NotebookLM.

#### 8.5 Highlight strategy (two levels)

- **v1 (ship first):** backend renders the page PNG with the highlight burned in; frontend shows the image. Zero coordinate maths.
- **v2 (upgrade):** backend returns rectangles; frontend overlays them on the pdf.js canvas (convert PyMuPDF top-left origin to the viewer's coordinates, scale with zoom) and animates a pulse. Crisper, zoomable, searchable text.

#### 8.6 Per-answer content (data contract)

Per answer, show:
1. The answer, with `[S3]` converted to `[p.43 (PDF p.45)]`.
2. Confidence and any calculation.
3. **Evidence cards** (one per citation): the page image with highlighted passage, the quoted text, the full source chunk, and a verified/unverified badge.
4. A collapsible **retrieval trace**: rewritten queries, top retrieved chunks with page and score. This is great for debugging and for convincing judges.
5. A clear warning box when the answer is "not found".

**Highlighting method:**
- Text: search the quote on the page; fall back to 8-word windows if line breaks break the match; final fallback is the chunk's stored bounding boxes.
- Table: find the first cell (row label) inside the table area, draw a band across the full row, and outline the matched cells and table.
- Render the page to PNG at 1.6x zoom.

---

## 5. Project structure

```
report-navigator/
├── config.py          # all settings, env-overridable
├── ingest.py          # PDF -> chunks.jsonl
├── index.py           # BM25 tokens + embeddings
├── retriever.py       # hybrid search + RRF + rerank
├── qa.py              # rewrite + LLM + verification
├── highlight.py       # page rendering with highlight
├── api.py             # FastAPI: /api/chat (SSE), /api/doc, /api/pdf, /api/page/...
├── cli.py             # terminal interface (backup)
├── web/               # Next.js frontend
│   ├── app/
│   │   ├── layout.tsx            # theme, fonts
│   │   └── page.tsx              # 3-zone layout
│   ├── components/
│   │   ├── chat/                 # Composer, MessageList, AnswerCard, CitationChip,
│   │   │                         #   PipelineStatus, NotFoundCard, StarterChips
│   │   ├── evidence/             # EvidencePanel, PdfViewer, TableEvidence,
│   │   │                         #   TraceTimeline, PageMinimap
│   │   └── ui/                   # shadcn/ui primitives
│   ├── lib/
│   │   ├── api.ts                # fetch + SSE client, typed responses
│   │   └── types.ts              # Answer, Citation, Source types
│   └── tailwind.config.ts
├── eval.py            # metrics on a question set
├── eval_questions.jsonl
├── requirements.txt
├── .env               # ANTHROPIC_API_KEY
├── data/              # the PDF
└── index_store/       # generated chunks + indexes
```

---

## 6. Step-by-step build plan

### Phase 0: Setup (15 min)
- Create the project folder, virtualenv, install: `pymupdf sentence-transformers rank-bm25 numpy anthropic streamlit python-dotenv`.
- Add the API key to `.env`.
- Pre-download the embedding and rerank models now (hackathon Wi-Fi is unreliable).

### Phase 1: Understand the document (30 min)
Open the PDF and answer:
- Page count? Scanned? Printed page numbers vs PDF index?
- Table style: ruled lines or just aligned text? Multi-row headers? Footnotes?
- Charts with numbers that exist nowhere else?
- Language(s)?
- Write 5 sample questions you expect from judges (text, table, comparison, trend).

### Phase 2: Ingestion (60-75 min)
1. Page loop: blocks, labels, headings, header/footer removal.
2. Text chunking (page-bounded).
3. Table detection and markdown conversion.
4. Write `chunks.jsonl`.
5. **Inspect the output by eye** (open the JSONL, check 10 random pages, 5 tables). Fix problems now; do not move on until tables look right.

### Phase 3: Indexing and retrieval (45 min)
1. Build BM25 and embeddings.
2. Implement hybrid search + RRF.
3. Add the reranker.
4. Test retrieval alone with a script: for 10 questions, print the top 5 chunks' pages. Is the right page in the top 5? Fix here before touching the LLM.

### Phase 4: Answer layer (45 min)
1. Source formatting + system prompt + forced tool call.
2. Quote verification and the "not found" override.
3. Number check.
4. Query rewrite for follow-ups.
5. Test with 10 questions, including 3 that are not answerable.

### Phase 5: API + modern web UI (about 90 min, UI owner can start earlier on a mocked API)
1. **Contract first (10 min):** freeze the `answer` JSON and SSE event shapes (`web/lib/types.ts` + `api.py` models). Frontend builds against a mock server returning a canned answer, so UI work does not wait for the backend.
2. **`api.py` (25 min):** FastAPI endpoints wrapping `qa.answer()`; SSE status events between pipeline stages; `/api/pdf`, `/api/page/{n}/image`; CORS for localhost.
3. **Scaffold (10 min):** `create-next-app` (TypeScript, Tailwind), `shadcn init`, add button/card/badge/tabs/sheet/tooltip; set fonts and design tokens.
4. **Chat core (25 min):** composer, message list, pipeline status animation, answer card with citation chips, not-found card.
5. **Evidence panel (25 min):** page image viewer that jumps to the cited page, quote and full-chunk tabs, table rendered as HTML with the cited row highlighted, verified badge.
6. **Polish (15 min):** retrieval trace tab, page minimap, empty state with starter questions, dark/light toggle, mobile bottom sheet.
7. **Upgrade only if time remains:** pdf.js overlay (v2 highlight), thumbs feedback logging, export chat.
8. Keep the CLI working as an emergency fallback.

### Phase 6: Evaluation and tuning (60 min)
1. Build 15-25 questions with expected pages and expected answer substrings (Section 7).
2. Run the eval, then fix failures **by category**:
   - Retrieval miss: chunking, `CANDIDATES`, keyword variants, rerank.
   - Right chunk but wrong answer: prompt, table formatting.
   - False "found": tighten the prompt and verification.
   - False "not found": raise `TOP_K_CONTEXT`.

### Phase 7: Polish and demo prep (45 min)
- Pick 3-4 demo questions that show off each bonus.
- Record a backup screen capture.
- Pre-warm the app (run one query so models are loaded).
- Write the 60-second pitch.

---

## 7. Evaluation plan

Create `eval_questions.jsonl` (one JSON per line):

```json
{"question": "...", "answerable": true, "expected_pages": [45], "expected_contains": ["9.9"]}
{"question": "...", "answerable": false}
```

**Question mix (about 20):**

| Type | Count | Example |
|---|---|---|
| Single text fact | 4 | "What was the LFPR in 2024?" |
| Single table cell | 5 | "Unemployment rate for Kerala, 2024?" |
| Comparison across rows | 3 | "Which state had the lowest rate?" |
| Trend / two periods | 2 | "How did female LFPR change from 2023 to 2024?" |
| Calculation | 2 | "Difference between male and female rate in Punjab?" |
| Follow-up (chat) | 2 | "And for Bihar?" |
| Unanswerable | 3-4 | Something not in the report |

**Metrics to track:**
1. Retrieval hit@8 (is an expected page in the retrieved set?)
2. Citation page accuracy (is an expected page actually cited?)
3. Answer correctness (expected strings present)
4. Abstention accuracy (unanswerable questions correctly return "not found")

Track these after every change so you know whether a tweak helped.

---

## 8. Hack-day timeline (about 6 hours)

| Time | Task | Done when |
|---|---|---|
| 0:00-0:30 | Setup + understand the PDF | Environment works; document notes written |
| 0:30-1:45 | Ingestion | Chunks and tables look right by eye |
| 1:45-2:30 | Index + retrieval | Right page in top 5 for 80% of test questions |
| 2:30-3:15 | Answer + verification | Grounded, cited, "not found" works |
| 3:15-4:15 | API + web UI integration (UI owner has been building on a mock API since about 1:00) | Chat, citation chips, evidence panel with highlight, live status |
| 4:15-5:00 | Eval + tuning | Metrics improving; known failures understood |
| 5:00-5:45 | UI polish + backup demo | Trace tab, minimap, dark/light, recorded video, pitch ready |
| 5:45-6:00 | Buffer | Do not add features |

**Rule:** if behind schedule, cut in this order: query rewrite, reranker, vision fallback. Never cut verification or highlighting; they are the differentiators.

---

## 9. Advanced upgrades (only if ahead of schedule)

1. **Vision fallback for charts and messy tables:** render the cited page to an image and send it to Claude together with the question for charts and tables the parser cannot read.
2. **Table-aware routing:** classify the question as "number lookup" and boost table chunks.
3. **Neighbour-chunk expansion:** include the previous and next chunk of the top hits when answers span chunk boundaries.
4. **Multilingual:** use `bge-m3` and let users ask in Hindi; answer in the user's language while quoting the report as-is.
5. **Answer caching** for repeated questions; **prompt caching** for the system prompt.
6. **Structured table store:** also load tables into a pandas DataFrame or SQLite so aggregate questions ("average across states") can be answered by code instead of the LLM. Use a text-to-pandas step with verification.
7. **Sentence-level highlighting** from verified quotes.
8. **Export:** a "Copy answer with citation" button.

---

## 10. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Table detection fails on the real PDF | Try text-based strategy; vision fallback; manually test the 5 most important tables |
| Wrong page cited | Chunks are page-bounded, quotes verified in the cited chunk |
| LLM reads the wrong column or row | Header repeated in every table part; prompt forces row/column/unit check; highlight shows the row for human check |
| Hallucinated numbers | Quote verification + number check + forced "not found" |
| Model downloads fail on venue network | Pre-download models; `USE_DENSE=0 USE_RERANK=0` BM25-only fallback still works |
| API outage or rate limit | Retry once; keep a recorded backup demo |
| Custom web UI eats the hack-day clock | Freeze the API contract in the first 15 minutes, build the UI against a mock server in parallel, ship PNG highlighting (v1) before any pdf.js overlay work, keep the CLI as a fallback |
| Frontend and backend integration bugs late | Typed shared contract, one end-to-end smoke test (ask, answer, open evidence) run after every merge |
| Very large PDF = slow indexing | Index once, cache to disk, never re-index during the demo |
| Printed vs PDF page confusion | Always display both numbers |
| Judges ask about something the report only implies | The system should say what is found and what is missing, never infer |

---

## 11. Demo script (3 minutes)

1. **Hook (15 s):** "Finding one number in a 300-page report takes minutes, and an unsourced answer cannot be trusted."
2. **Text question (30 s):** show answer, page reference, highlighted passage.
3. **Table question (40 s):** exact cell value, highlighted **row** on the original table.
4. **Follow-up (20 s):** "And for 2023?" shows conversation memory.
5. **Calculation (20 s):** difference or percent change with visible inputs and formula.
6. **Not-found question (30 s):** ask something absent; show "Not found in the report", no guessing.
7. **Trust layer (20 s):** open the retrieval trace and point out quote verification.
8. **Close (15 s):** "Every answer is checkable in one click."

---

## 12. Team split (if more than one person)

| Person | Owns |
|---|---|
| A | Ingestion + tables (hardest, start immediately) |
| B | Index, retrieval, reranking, retrieval testing |
| C | LLM prompt, verification, evaluation set |
| D | Next.js frontend (chat, evidence panel, design system), starting on a mock API, plus demo script and video |
| C (second task) | `api.py` wrapper and SSE events once the answer layer is stable |

Agree on the **chunk schema** (Section 4) in the first 15 minutes so everyone can work in parallel.

---

## 13. Pre-flight checklist

- [ ] API key works; one test call succeeds
- [ ] Models downloaded locally
- [ ] Index built and cached; app starts in under 10 seconds
- [ ] 3 demo questions rehearsed, including one unanswerable
- [ ] Highlighting verified on a text page and a table page
- [ ] Backup recording saved
- [ ] BM25-only fallback tested (`USE_DENSE=0 USE_RERANK=0 USE_REWRITE=0`)
- [ ] README with run instructions
