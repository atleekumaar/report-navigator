"""
text_engine.py — Extract page text, build BM25 index, optional OCR fallback.

For scanned pages with no text layer, we render the page as an image and run
Tesseract OCR (if available).  If Tesseract is not installed we simply skip
those pages — the table engine often still finds the answer.
"""

from __future__ import annotations

import re
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Set

import pymupdf as fitz

try:
    from rank_bm25 import BM25Okapi
except ImportError:
    BM25Okapi = None  # type: ignore


# ---------------------------------------------------------------------------
# OCR helper
# ---------------------------------------------------------------------------

_TESSERACT_AVAILABLE: Optional[bool] = None


def _has_tesseract() -> bool:
    global _TESSERACT_AVAILABLE
    if _TESSERACT_AVAILABLE is None:
        try:
            subprocess.run(
                ["tesseract", "--version"],
                capture_output=True,
                timeout=5,
            )
            _TESSERACT_AVAILABLE = True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            _TESSERACT_AVAILABLE = False
    return _TESSERACT_AVAILABLE


def ocr_page(doc: fitz.Document, page_idx: int, dpi: int = 300) -> str:
    """Render *page_idx* and run Tesseract OCR.  Returns '' on failure."""
    if not _has_tesseract():
        return ""
    try:
        page = doc[page_idx]
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csGRAY)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            pix.save(tmp.name)
            tmp_path = tmp.name
        result = subprocess.run(
            ["tesseract", tmp_path, "-", "--psm", "6"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        os.unlink(tmp_path)
        return result.stdout.strip()
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Page text index
# ---------------------------------------------------------------------------

class PageTextIndex:
    """Text content for every page, plus a BM25 index over pages."""

    def __init__(self, pdf_path: str | Path, use_ocr: bool = True):
        doc = fitz.open(str(pdf_path))
        self.page_count = len(doc)
        self.pages: List[str] = []       # 0-indexed text per page
        self.scanned: Set[int] = set()   # 0-indexed scanned page indices

        for i in range(self.page_count):
            text = doc[i].get_text()
            if len(text.strip()) < 30:
                # Likely a scanned page
                self.scanned.add(i)
                if use_ocr:
                    text = ocr_page(doc, i)
            self.pages.append(text)

        doc.close()

        # Build BM25 over pages
        self._tokens: List[List[str]] = [
            self._tokenise(p) for p in self.pages
        ]
        if BM25Okapi is not None and self._tokens:
            self.bm25 = BM25Okapi(self._tokens)
        else:
            self.bm25 = None

        print(f"[TextEngine] Indexed {self.page_count} pages "
              f"({len(self.scanned)} scanned, OCR={'on' if use_ocr else 'off'}).")

    # ---- tokenisation ----

    @staticmethod
    def _tokenise(text: str) -> List[str]:
        return re.findall(r'[a-zA-Z0-9]+', text.lower())

    # ---- search ----

    def search_pages(self, query: str, top_k: int = 10) -> List[int]:
        """Return 1-based page numbers ranked by BM25 relevance."""
        if self.bm25 is None:
            return []
        tokens = self._tokenise(query)
        if not tokens:
            return []
        scores = self.bm25.get_scores(tokens)
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        return [i + 1 for i in ranked[:top_k]]

    def pages_containing(self, term: str) -> List[int]:
        """Return 1-based page numbers whose text contains *term*."""
        t = term.lower()
        return [i + 1 for i, p in enumerate(self.pages) if t in p.lower()]

    def page_text(self, page_num: int) -> str:
        """Return text for 1-based page number."""
        if 1 <= page_num <= self.page_count:
            return self.pages[page_num - 1]
        return ""

    def entity_cooccurrence_search(
        self,
        terms: List[str],
        top_k: int = 5,
    ) -> List[int]:
        """Score pages by IDF-weighted co-occurrence of *terms*.

        Returns 1-based page numbers.
        """
        scores = [0.0] * self.page_count
        for term in terms:
            t = term.lower()
            matching = [i for i, p in enumerate(self.pages) if t in p.lower()]
            if not matching:
                continue
            idf = 1.0 / (len(matching) + 1)
            for idx in matching:
                scores[idx] += idf
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        return [i + 1 for i in ranked[:top_k]]

