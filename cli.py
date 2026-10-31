import sys
import os
import argparse
import json
from pathlib import Path

import config


def print_banner():
    print("=" * 68)
    print("           REPORT NAVIGATOR - ENTERPRISE HARDENED CLI")
    print("  Grounded Statistics QA with Verified Citations & Page Chips")
    print("=" * 68)
    print(f"Active Report PDF : {config.PDF_PATH}")
    print(f"Table Strategy    : {config.TABLE_STRATEGY}")
    print(f"OCR Enabled       : {'Yes' if config.OCR_ENABLED else 'No'}")
    print(f"Dense Retrieval   : {'Enabled' if config.USE_DENSE else 'Disabled (BM25 only)'}")
    print(f"Reranker          : {'Enabled' if config.USE_RERANK else 'Disabled'}")
    print(f"LLM Provider      : {config.LLM_PROVIDER}")
    print("=" * 68 + "\n")


def cmd_index(args):
    """Index a target PDF report with table extraction and diagnostic quality checks."""
    from ingest import ingest_pdf
    from index import build_index

    pdf_path = Path(args.pdf_path).resolve()
    if not pdf_path.exists():
        print(f"[Error] PDF file not found: {pdf_path}")
        sys.exit(1)

    print(f"\n[CLI] Starting Ingestion for: {pdf_path.name}")
    print(f"  Path: {pdf_path}")
    print(f"  Size: {pdf_path.stat().st_size / 1024:.1f} KB")

    # Override config options if provided on CLI
    if args.table_strategy:
        config.TABLE_STRATEGY = args.table_strategy
    if args.no_ocr:
        config.OCR_ENABLED = False

    chunks = ingest_pdf(pdf_path)

    # Analyze table extraction count
    table_chunks = [c for c in chunks if c.get("type") == "table"]
    unique_tables = set(c.get("table_id") for c in table_chunks if c.get("table_id"))
    unique_pages = set(c.get("page") for c in chunks)

    print(f"\n[CLI] Document Extraction Summary:")
    print(f"  Total chunks: {len(chunks)}")
    print(f"  Total pages covered: {len(unique_pages)}")
    print(f"  Unique tables extracted: {len(unique_tables)} ({len(table_chunks)} table chunks)")

    # Hardening recommendation from Phase A
    if len(unique_pages) >= 5 and len(unique_tables) <= 1 and config.TABLE_STRATEGY != "text":
        print("\n" + "!" * 68)
        print("  [RECOMMENDATION] Table count is low for this report.")
        print("  Many government reports have unruled borderless tables.")
        print("  If tables were missed, re-run with:")
        print(f"    python cli.py index \"{pdf_path}\" --table-strategy text")
        print("!" * 68 + "\n")

    print("\n[CLI] Building hybrid search indexes (BM25 + vectors)...")
    build_index()
    print("\n[CLI] Ingestion and indexing completed successfully! Document is ready for QA.")


def cmd_inspect(args):
    """Eyeball sample pages and tables from index store to audit extraction quality."""
    chunks_file = config.CHUNKS_FILE
    if not chunks_file.exists():
        print(f"[Error] Chunks file not found at {chunks_file}. Run 'python cli.py index <pdf>' first.")
        sys.exit(1)

    all_chunks = []
    with open(chunks_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                all_chunks.append(json.loads(line))

    text_chunks = [c for c in all_chunks if c.get("type") == "text"]
    table_chunks = [c for c in all_chunks if c.get("type") == "table"]

    num_pages_to_show = min(args.pages, len(text_chunks))
    num_tables_to_show = min(args.tables, len(table_chunks))

    print("\n" + "=" * 68)
    print(f"  INSPECTION: {num_pages_to_show} SAMPLE PAGES & {num_tables_to_show} SAMPLE TABLES")
    print("=" * 68)

    print(f"\n--- [1] Sample Pages / Text Chunks ({num_pages_to_show} shown) ---")
    seen_pages = set()
    shown_pages = 0
    for c in text_chunks:
        p = c.get("page")
        if p not in seen_pages:
            seen_pages.add(p)
            shown_pages += 1
            lbl = c.get("label", str(p))
            page_repr = f"p.{lbl} (PDF p.{p})" if str(lbl) != str(p) else f"p.{lbl}"
            sec = c.get("section", "General")
            sample_txt = c.get("text", "")[:180].replace("\n", " ")
            print(f"  [{shown_pages}] ID: {c.get('id')} | Page: {page_repr} | Section: {sec}")
            print(f"      Text: \"{sample_txt}...\"\n")
            if shown_pages >= num_pages_to_show:
                break

    print(f"\n--- [2] Sample Tables ({num_tables_to_show} shown) ---")
    if not table_chunks:
        print("  No tables found in extracted chunks.")
    else:
        for i, tc in enumerate(table_chunks[:num_tables_to_show], 1):
            p = tc.get("page")
            lbl = tc.get("label", str(p))
            page_repr = f"p.{lbl} (PDF p.{p})" if str(lbl) != str(p) else f"p.{lbl}"
            caption = tc.get("caption") or "No caption"
            print(f"  [{i}] Table ID: {tc.get('table_id')} | Part: {tc.get('part')} | Page: {page_repr}")
            print(f"      Caption: {caption}")
            rows = tc.get("text", "").splitlines()[:5]
            print("      Snippet:")
            for r in rows:
                print(f"        {r[:90]}")
            print()

    print("=" * 68)


def cmd_ask(args):
    """Answer a single query with retrieval trace, citation verification, and formula calculation."""
    from qa import QAEngine

    try:
        engine = QAEngine()
    except Exception as e:
        print(f"[Error] Failed to initialize QA engine: {e}")
        print("Ensure you have ingested and indexed a document first: python cli.py index <path_to_pdf>")
        sys.exit(1)

    query = args.query.strip()
    print(f"\n[Question] {query}\n")

    result = engine.answer(
        query=query,
        use_rerank=not args.no_rerank,
        on_status=lambda step, msg: print(f"  -> [{step.upper()}] {msg}")
    )

    print("\n" + "=" * 68)
    trace = result.get("retrieval_trace", {})
    standalone = trace.get("standalone_query")
    if standalone and standalone != query:
        print(f"Standalone Query   : {standalone}")
    keywords = trace.get("keywords", [])
    if keywords:
        print(f"Search Keywords    : {', '.join(keywords)}")
    print(f"Retrieved Passages : {trace.get('num_retrieved', 0)}")
    print("=" * 68)

    found = result.get("found", False)
    if not found:
        print("\nSTATUS: NOT FOUND IN REPORT (Correct Abstention)")
        print(f"Answer: {result.get('answer')}")
    else:
        print(f"\nSTATUS: FOUND (Confidence: {result.get('confidence', '').upper()})")
        if result.get("has_number_warning"):
            print("WARNING: [!] Some numbers in the answer could not be matched directly to sources.")
        print(f"\nANSWER:\n{result.get('answer')}")

    if result.get("calculation"):
        print(f"\nCALCULATION:\n{result.get('calculation')}")

    citations = result.get("citations", [])
    if citations:
        print(f"\nCITATIONS ({len(citations)}):")
        for c in citations:
            v_badge = "[VERIFIED]" if c.get("verified") else f"[UNVERIFIED - {c.get('reason', 'quote mismatch')}]"
            lbl = c.get("label", str(c.get("page")))
            pdf_p = c.get("page")
            p_str = f"p.{lbl} (PDF p.{pdf_p})" if str(lbl) != str(pdf_p) else f"p.{lbl}"
            print(f"  * Source {c.get('source_id')}: Page {p_str} | Type: {c.get('type')} {v_badge}")
            print(f"    Quote: \"{c.get('quote')}\"")

    print("\n" + "=" * 68)


def cmd_chat(args):
    """Run interactive conversation loop."""
    from qa import QAEngine

    print_banner()

    try:
        engine = QAEngine()
    except Exception as e:
        print(f"Error initializing QA engine: {e}")
        print("Ensure you have ingested and indexed a document first: python cli.py index <path_to_pdf>")
        sys.exit(1)

    history = []

    while True:
        try:
            query = input("\n[Question] > ").strip()
            if not query:
                continue
            if query.lower() in ("exit", "quit", "q"):
                print("Exiting Report Navigator CLI. Goodbye!")
                break

            print("\nSearching and reading...")
            result = engine.answer(
                query=query,
                history=history,
                use_rerank=config.USE_RERANK,
                on_status=lambda step, msg: print(f"  -> [{step.upper()}] {msg}")
            )

            print("\n" + "-" * 50)
            if not result.get("found"):
                print("STATUS: NOT FOUND IN REPORT")
                print(f"Answer: {result.get('answer')}")
            else:
                print(f"STATUS: FOUND (Confidence: {result.get('confidence', '').upper()})")
                if result.get("has_number_warning"):
                    print("WARNING: Check numerical values against cited pages.")
                print(f"\nANSWER:\n{result.get('answer')}")

            if result.get("calculation"):
                print(f"\nCALCULATION:\n{result.get('calculation')}")

            citations = result.get("citations", [])
            if citations:
                print(f"\nCITATIONS ({len(citations)}):")
                for c in citations:
                    v_str = "[VERIFIED]" if c.get("verified") else "[UNVERIFIED]"
                    lbl = c.get("label", str(c.get("page")))
                    pdf_p = c.get("page")
                    p_str = f"p.{lbl} (PDF p.{pdf_p})" if str(lbl) != str(pdf_p) else f"p.{lbl}"
                    print(f"  * Source {c.get('source_id')}: Page {p_str} {v_str}")
                    print(f"    Quote: \"{c.get('quote')}\"")

            print("-" * 50)

            history.append({"role": "user", "content": query})
            history.append({"role": "assistant", "content": result.get("answer", "")})

        except KeyboardInterrupt:
            print("\nInterrupted. Exiting...")
            break
        except Exception as ex:
            print(f"\nAn error occurred: {ex}")


def cmd_eval(args):
    """Run full evaluation suite."""
    from eval import run_evaluation
    eval_path = Path(args.questions)
    run_evaluation(eval_path)


def cmd_serve(args):
    """Start FastAPI server."""
    import uvicorn
    port = args.port or config.PORT
    host = args.host or config.HOST
    print(f"Starting Report Navigator server at http://{host}:{port} ...")
    uvicorn.run("api:app", host=host, port=port, reload=args.reload)


def main():
    parser = argparse.ArgumentParser(
        description="Report Navigator - Hardened Statistical Report QA Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", help="Subcommand to execute")

    # Index command
    p_index = subparsers.add_parser("index", help="Ingest and index a PDF report")
    p_index.add_argument("pdf_path", type=str, help="Path to PDF file to index")
    p_index.add_argument("--table-strategy", choices=["lines", "text"], default=None, help="Table extraction strategy ('lines' or 'text')")
    p_index.add_argument("--no-ocr", action="store_true", help="Disable OCR fallback")

    # Inspect command
    p_inspect = subparsers.add_parser("inspect", help="Eyeball sample pages and tables from index")
    p_inspect.add_argument("--pages", type=int, default=10, help="Number of pages to inspect")
    p_inspect.add_argument("--tables", type=int, default=5, help="Number of tables to inspect")

    # Ask command
    p_ask = subparsers.add_parser("ask", help="Query the report with full evidence trace")
    p_ask.add_argument("query", type=str, help="Question to ask")
    p_ask.add_argument("--no-rerank", action="store_true", help="Disable cross-encoder reranker")

    # Chat command
    subparsers.add_parser("chat", help="Start interactive multi-turn chat session")

    # Eval command
    p_eval = subparsers.add_parser("eval", help="Run evaluation suite on test questions")
    p_eval.add_argument("--questions", type=str, default="eval_questions.jsonl", help="Path to questions jsonl file")

    # Serve command
    p_serve = subparsers.add_parser("serve", help="Start the FastAPI backend server")
    p_serve.add_argument("--port", type=int, default=8000, help="Port to run on")
    p_serve.add_argument("--host", type=str, default="127.0.0.1", help="Host interface")
    p_serve.add_argument("--reload", action="store_true", help="Enable auto-reload")

    args = parser.parse_args()

    if args.command == "index":
        cmd_index(args)
    elif args.command == "inspect":
        cmd_inspect(args)
    elif args.command == "ask":
        cmd_ask(args)
    elif args.command == "chat":
        cmd_chat(args)
    elif args.command == "eval":
        cmd_eval(args)
    elif args.command == "serve":
        cmd_serve(args)
    else:
        # Default behavior with no arguments is interactive chat
        cmd_chat(args)


if __name__ == "__main__":
    main()
