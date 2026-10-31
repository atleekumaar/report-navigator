import json
import pickle
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple
import numpy as np
from rank_bm25 import BM25Okapi

import config


def expand_with_synonyms(tokens: List[str]) -> List[str]:
    """
    Expand a token list with synonyms from config.SYNONYMS.
    Works bidirectionally: if a token matches a key, add its values;
    if a token matches a value, add the key.
    """
    expanded = list(tokens)
    token_set = set(t.lower() for t in tokens)

    for key, values in config.SYNONYMS.items():
        key_lower = key.lower()
        # If any token matches the key, add value tokens
        if key_lower in token_set:
            for v in values:
                v_tokens = v.lower().split()
                for vt in v_tokens:
                    if vt not in token_set:
                        expanded.append(vt)
        # If any token matches a value, add the key
        for v in values:
            v_tokens = v.lower().split()
            if any(vt in token_set for vt in v_tokens):
                if key_lower not in token_set:
                    expanded.append(key_lower)
                break

    return expanded


def tokenize_for_bm25(text: str, use_synonyms: bool = False) -> List[str]:
    """
    Tokenizes text for BM25 with special preservation for:
    - Decimal numbers (e.g. 7.1, 14.3)
    - Comma-separated numbers (1,234 -> both '1,234' and '1234')
    - Alphanumeric codes and table identifiers
    - Optional synonym expansion for query-time boosting
    """
    tokens = []
    # Find words, numbers with decimals, or numbers with commas
    raw_tokens = re.findall(r'[a-zA-Z0-9_\.%]+(?:,[a-zA-Z0-9_\.%]+)*|\b\w+\b', text.lower())
    for t in raw_tokens:
        clean_t = t.strip('.,?!:;"\'()[]{}')
        if not clean_t:
            continue
        tokens.append(clean_t)
        # If token contains commas in numbers, also add the stripped version
        if ',' in clean_t and any(ch.isdigit() for ch in clean_t):
            tokens.append(clean_t.replace(',', ''))
        # If token contains % sign, also add bare number
        if '%' in clean_t:
            tokens.append(clean_t.replace('%', ''))

    if use_synonyms:
        tokens = expand_with_synonyms(tokens)

    return tokens


def build_contextual_text(chunk: Dict[str, Any]) -> str:
    """Prepend section, page, and chunk type to improve both BM25 and dense retrieval."""
    section = chunk.get("section") or "General"
    page = chunk.get("page")
    label = chunk.get("label", str(page))
    c_type = chunk.get("type", "text")
    body = chunk.get("text", "")
    caption = chunk.get("caption", "")

    parts = [f"[Section: {section}] [Page {label} (PDF p.{page})] [Type: {c_type}]"]
    if caption:
        parts.append(f"[Caption: {caption}]")
    parts.append(body)
    return "\n".join(parts)


class Indexer:
    def __init__(self):
        self.chunks: List[Dict[str, Any]] = []
        self.bm25: BM25Okapi = None
        self.embeddings: np.ndarray = None
        self.embed_model = None

    def load_chunks(self, chunks_file: Path = config.CHUNKS_FILE) -> List[Dict[str, Any]]:
        """Load chunks from chunks.jsonl."""
        chunks = []
        if not chunks_file.exists():
            raise FileNotFoundError(f"Chunks file {chunks_file} not found. Run ingest first.")
        with open(chunks_file, "r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, 1):
                if line.strip():
                    try:
                        chunks.append(json.loads(line))
                    except json.JSONDecodeError as e:
                        print(f"[Index] Warning: skipping malformed line {line_no} in {chunks_file}: {e}")
        self.chunks = chunks
        print(f"[Index] Loaded {len(chunks)} chunks from {chunks_file}")
        return chunks

    def build_bm25(self) -> BM25Okapi:
        """Build BM25 index over contextual chunk representations."""
        if not self.chunks:
            raise ValueError("[Index] No chunks loaded. Cannot build BM25 index.")
        print(f"[Index] Building BM25 index over {len(self.chunks)} chunks...")
        tokenized_corpus = []
        for chunk in self.chunks:
            ctx_text = build_contextual_text(chunk)
            tokenized_corpus.append(tokenize_for_bm25(ctx_text, use_synonyms=False))
        self.bm25 = BM25Okapi(tokenized_corpus)
        return self.bm25

    def build_dense_embeddings(self, model_name: str = config.EMBEDDING_MODEL_NAME) -> np.ndarray:
        """Build dense embeddings using sentence-transformers."""
        if not config.USE_DENSE:
            print("[Index] USE_DENSE is disabled. Skipping dense index.")
            return np.array([])

        if not self.chunks:
            raise ValueError("[Index] No chunks loaded. Cannot build embeddings.")

        print(f"[Index] Loading embedding model: {model_name}...")
        try:
            from sentence_transformers import SentenceTransformer
            self.embed_model = SentenceTransformer(model_name)
        except Exception as e:
            print(f"[Index] Notice: sentence-transformers not available ({e}). Skipping dense vectors; using BM25 index.")
            self.embeddings = np.array([])
            return self.embeddings

        corpus_texts = [build_contextual_text(c) for c in self.chunks]
        print(f"[Index] Encoding {len(corpus_texts)} chunks into dense vectors...")
        embeddings = self.embed_model.encode(
            corpus_texts,
            batch_size=32,
            show_progress_bar=True,
            normalize_embeddings=True
        )
        self.embeddings = np.array(embeddings, dtype=np.float32)
        return self.embeddings

    def save(self, index_dir: Path = config.INDEX_DIR):
        """Save BM25, embeddings, and metadata to disk."""
        index_dir.mkdir(parents=True, exist_ok=True)
        if self.bm25 is not None:
            with open(config.BM25_FILE, "wb") as f:
                pickle.dump(self.bm25, f)
            print(f"[Index] Saved BM25 to {config.BM25_FILE}")

        if self.embeddings is not None and len(self.embeddings) > 0:
            np.save(config.EMBEDDINGS_FILE, self.embeddings)
            print(f"[Index] Saved dense embeddings to {config.EMBEDDINGS_FILE}")

        # Compute stats for metadata
        text_count = sum(1 for c in self.chunks if c.get("type") == "text")
        table_count = sum(1 for c in self.chunks if c.get("type") == "table")
        unique_pages = len(set(c.get("page") for c in self.chunks))
        unique_tables = len(set(c.get("table_id") for c in self.chunks if c.get("table_id")))

        metadata = {
            "num_chunks": len(self.chunks),
            "text_chunks": text_count,
            "table_chunks": table_count,
            "unique_pages": unique_pages,
            "unique_tables": unique_tables,
            "has_bm25": self.bm25 is not None,
            "has_dense": self.embeddings is not None and len(self.embeddings) > 0,
            "embedding_model": config.EMBEDDING_MODEL_NAME,
            "embedding_dim": int(self.embeddings.shape[1]) if self.embeddings is not None and len(self.embeddings) > 0 else 0
        }
        with open(config.METADATA_FILE, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
        print(f"[Index] Saved index metadata to {config.METADATA_FILE}")

    def load(self, index_dir: Path = config.INDEX_DIR):
        """Load persisted index files into memory."""
        self.load_chunks(config.CHUNKS_FILE)
        if config.BM25_FILE.exists():
            with open(config.BM25_FILE, "rb") as f:
                self.bm25 = pickle.load(f)
            print(f"[Index] Loaded BM25 index with {len(self.chunks)} items.")
        else:
            print("[Index] Warning: BM25 file not found. Rebuilding...")
            self.build_bm25()

        if config.USE_DENSE and config.EMBEDDINGS_FILE.exists():
            self.embeddings = np.load(config.EMBEDDINGS_FILE)
            print(f"[Index] Loaded embeddings shape: {self.embeddings.shape}")
            # Validate embedding count matches chunk count
            if len(self.embeddings) != len(self.chunks):
                print(f"[Index] WARNING: Embedding count ({len(self.embeddings)}) != chunk count ({len(self.chunks)}). Rebuilding...")
                self.build_dense_embeddings()
                self.save()
        elif config.USE_DENSE:
            print("[Index] Warning: Embeddings file not found but USE_DENSE=1. Dense search will be unavailable.")


def build_index():
    indexer = Indexer()
    indexer.load_chunks()
    indexer.build_bm25()
    if config.USE_DENSE:
        indexer.build_dense_embeddings()
    indexer.save()

    # Print summary
    text_count = sum(1 for c in indexer.chunks if c.get("type") == "text")
    table_count = sum(1 for c in indexer.chunks if c.get("type") == "table")
    unique_tables = len(set(c.get("table_id") for c in indexer.chunks if c.get("table_id")))
    print(f"\n[Index] ==================== INDEX REPORT ====================")
    print(f"  Total chunks    : {len(indexer.chunks)}")
    print(f"  Text chunks     : {text_count}")
    print(f"  Table chunks    : {table_count}")
    print(f"  Unique tables   : {unique_tables}")
    print(f"  BM25 index      : {'Built' if indexer.bm25 else 'Skipped'}")
    print(f"  Dense embeddings: {'Built' if indexer.embeddings is not None and len(indexer.embeddings) > 0 else 'Skipped'}")
    print(f"[Index] ========================================================\n")


if __name__ == "__main__":
    build_index()
