import os
from pathlib import Path
from dotenv import load_dotenv

# Enforce offline HuggingFace behavior for strict offline evaluation and instant loading
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

# Data & Storage Paths
DATA_DIR = BASE_DIR / "data"
INDEX_DIR = BASE_DIR / os.getenv("INDEX_DIR", "index_store")
INDEX_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_PDF_PATH = DATA_DIR / "report_A.pdf" if (DATA_DIR / "report_A.pdf").exists() else DATA_DIR / "report.pdf"
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

# Table extraction strategy: "lines" (default, ruled tables) or "text" (unruled tables)
# Switch to "text" if find_tables() misses tables in the real PDF
TABLE_STRATEGY = os.getenv("TABLE_STRATEGY", "lines")

# OCR fallback: trigger on pages with fewer than this many characters
OCR_MIN_CHARS = int(os.getenv("OCR_MIN_CHARS", "30"))
OCR_ENABLED = os.getenv("OCR_ENABLED", "1").lower() in ("1", "true", "yes")

# Embedding & Rerank Models
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
RERANK_MODEL_NAME = os.getenv("RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")

# Retrieval Hyperparameters
BM25_TOP_K = 30
DENSE_TOP_K = 30
FUSED_POOL_SIZE = 30
FINAL_TOP_K = 8
RRF_K = 60

# Retrieval quality gates — minimum coverage scores below which we flag low confidence
MIN_COVERAGE_BM25 = float(os.getenv("MIN_COVERAGE_BM25", "0.5"))
MIN_COVERAGE_RERANK = float(os.getenv("MIN_COVERAGE_RERANK", "0.3"))

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

# Gemini model names (used when LLM_PROVIDER=gemini)
GEMINI_MODEL_ANSWER = os.getenv("GEMINI_MODEL_ANSWER", "gemini-2.5-flash")
GEMINI_MODEL_REWRITE = os.getenv("GEMINI_MODEL_REWRITE", "gemini-2.5-flash")

# API Server
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))

# ---------------------------------------------------------------------------
# Synonym dictionary for query expansion in BM25 search
# Maps common alternative phrasings to canonical terms found in statistical reports.
# Both directions are expanded at search time.
# ---------------------------------------------------------------------------
SYNONYMS = {
    # Employment / Labour
    "unemployment": ["joblessness", "jobless", "unemployed", "without work", "out of work"],
    "employment": ["employed", "jobs", "job", "working", "workforce participation"],
    "lfpr": ["labour force participation rate", "labor force participation rate", "work participation"],
    "labour": ["labor"],
    "workforce": ["work force", "labor force", "labour force"],

    # Demographics
    "female": ["women", "woman", "girls", "girl"],
    "male": ["men", "man", "boys", "boy"],
    "youth": ["young", "young people", "adolescent", "15-29", "15-24"],
    "rural": ["village", "villages", "countryside"],
    "urban": ["city", "cities", "town", "towns", "metropolitan"],

    # Statistics
    "rate": ["percentage", "percent", "per cent", "ratio", "proportion"],
    "average": ["mean", "avg"],
    "highest": ["maximum", "max", "top", "most", "largest", "greatest"],
    "lowest": ["minimum", "min", "bottom", "least", "smallest"],
    "increase": ["rise", "grew", "growth", "risen", "increased", "up"],
    "decrease": ["fall", "fell", "decline", "declined", "dropped", "down", "reduced"],
    "compare": ["comparison", "versus", "vs", "difference", "gap"],

    # Geography (Indian states — extend for specific report)
    "india": ["nation", "national", "country", "all india", "nationwide"],

    # Road Safety & Traffic Metrics
    "killed": ["deaths", "died", "dead", "fatalities", "fatal", "death"],
    "accidents": ["crashes", "collisions", "incidents", "mishaps", "road accidents"],
    "injured": ["injuries", "grievously injured", "wounded", "hurt", "minor injuries"],

    # Road User & Vehicle Categories
    "two-wheeler": ["two wheeler", "2-wheeler", "motorcycle", "bike", "scooter", "moped"],
    "pedestrian": ["pedestrians", "walking", "walker", "on foot"],
    "bicycle": ["bicycles", "cycle", "cyclist", "cycles"],
    "auto": ["auto-rickshaw", "auto rickshaw", "three-wheeler", "3-wheeler", "autorickshaw"],
    "car": ["cars", "taxi", "taxis", "van", "vans", "lmv", "lmvs", "light motor vehicle"],
    "truck": ["trucks", "lorry", "heavy goods vehicle", "hgv", "goods carrier"],
    "bus": ["buses", "coach", "mini bus", "heavy passenger vehicle"],

    # Traffic Violations & Causative Factors
    "over-speeding": ["overspeeding", "speeding", "excessive speed", "speed violation"],
    "drunken driving": ["drunk driving", "alcohol", "drugs", "drunken", "drink driving", "under influence"],
    "red light": ["jumping red light", "red light jumping", "traffic light", "signal jumping", "signal violation"],
    "mobile phone": ["use of mobile phone", "cell phone", "phone usage", "talking on phone"],
    "wrong side": ["wrong-side", "wrong-side driving", "driving on wrong side", "one-way violation", "wrong way"],
    "wrong-side": ["wrong side", "wrong-side driving", "driving on wrong side", "one-way violation", "wrong way"],

    # Collision Types
    "collision": ["run off road", "hit and run", "head on", "rear end", "side impact"],

    # Report structure
    "table": ["statement", "tabulation", "exhibit"],
    "chapter": ["section", "part"],
    "figure": ["chart", "graph", "diagram"],
    "annexure": ["appendix", "annex"],
}
