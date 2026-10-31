import sys
import os
from pathlib import Path
import config
from qa import QAEngine

def print_banner():
    print("=" * 65)
    print("           REPORT NAVIGATOR - INTERACTIVE CLI")
    print("  Grounded Statistics QA with Page Citations & Verification")
    print("=" * 65)
    print(f"Active Report PDF : {config.PDF_PATH}")
    print(f"Dense Retrieval   : {'Enabled' if config.USE_DENSE else 'Disabled'}")
    print(f"Reranker          : {'Enabled' if config.USE_RERANK else 'Disabled'}")
    print(f"LLM Provider      : {config.LLM_PROVIDER}")
    print("Type your question and press Enter. Type 'exit' or 'quit' to stop.\n")

def main():
    print_banner()

    try:
        engine = QAEngine()
    except Exception as e:
        print(f"Error initializing QA engine: {e}")
        print("Ensure you have ingested and indexed a document first: python ingest.py && python index.py")
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
                    print(f"  • Source {c.get('source_id')}: Page {c.get('label')} (PDF p.{c.get('page')}) {v_str}")
                    print(f"    Quote: \"{c.get('quote')}\"")

            print("-" * 50)

            history.append({"role": "user", "content": query})
            history.append({"role": "assistant", "content": result.get("answer", "")})

        except KeyboardInterrupt:
            print("\nInterrupted. Exiting...")
            break
        except Exception as ex:
            print(f"\nAn error occurred: {ex}")

if __name__ == "__main__":
    main()

