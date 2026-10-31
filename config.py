import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

# Data & Storage Paths
DATA_DIR = BASE_DIR / "data"
INDEX_DIR = BASE_DIR / os.getenv("INDEX_DIR", "index_store")
INDEX_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_PDF_PATH = DATA_DIR / "report.pdf"
PDF_PATH = Path(os.getenv("PDF_PATH", str(DEFAULT_PDF_PATH)))

CHUNKS_FILE = INDEX_DIR / "chunks.jsonl"
BM25_FILE = INDEX_DIR / "bm25.pkl"
EMBEDDINGS_FILE = INDEX_DIR / "embeddings.npy"
METADATA_FILE = INDEX_DIR / "metadata.json"

# Ingestion Settings
TARGET_CHUNK_CHARS = 1100
MIN_CHUNK_CHARS = 100
TABLE_MAX_ROWS_PER_PART = 14
HEADER_FOOTER_MARGIN_PERCENT = 0.06  # top/bottom 6% of page considered header/footer

# Embedding & Rerank Models
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
RERANK_MODEL_NAME = os.getenv("RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")

# Retrieval Hyperparameters
BM25_TOP_K = 30
DENSE_TOP_K = 30
FUSED_POOL_SIZE = 30
FINAL_TOP_K = 8
RRF_K = 60

# Feature Toggles
USE_DENSE = os.getenv("USE_DENSE", "1").lower() in ("1", "true", "yes")
USE_RERANK = os.getenv("USE_RERANK", "1").lower() in ("1", "true", "yes")
USE_REWRITE = os.getenv("USE_REWRITE", "1").lower() in ("1", "true", "yes")

# LLM Providers & Keys
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "anthropic").lower()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

LLM_MODEL_ANSWER = os.getenv("LLM_MODEL_ANSWER", "claude-3-5-sonnet-20241022")
LLM_MODEL_REWRITE = os.getenv("LLM_MODEL_REWRITE", "claude-3-5-haiku-20241022")

# API Server
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))

