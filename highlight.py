import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
try:
    import pymupdf as fitz
except ImportError:
    import fitz
from PIL import Image
import io

import config

HIGHLIGHT_COLOR = (1.0, 0.9, 0.2)  # Warm yellow (RGB 0-1)
TABLE_ROW_COLOR = (1.0, 0.85, 0.25)

def clean_quote_for_search(quote: str) -> str:
    """Clean markdown table syntax or formatting for search."""
    cleaned = quote.replace("|", " ").replace("---", " ")
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

def find_text_rects_on_page(page: fitz.Page, quote: str, fallback_rects: Optional[List[List[float]]] = None) -> List[fitz.Rect]:
    """
    Search for quote rectangles on the page.
    1. Try exact search.
    2. Try searching by sliding windows of 6-8 words.
    3. Fall back to stored chunk bounding boxes if provided.
    """
    cleaned = clean_quote_for_search(quote)
    if not cleaned:
        if fallback_rects:
            return [fitz.Rect(r) for r in fallback_rects]
        return []

    # 1. Direct search
    rects = page.search_for(cleaned)
    if rects:
        return rects

    # 2. Windowed search (handle hyphenation or line breaks)
    words = cleaned.split()
    if len(words) > 5:
        window_size = 5
        matched_rects = []
        for i in range(0, len(words) - window_size + 1, window_size):
            window_str = " ".join(words[i:i + window_size])
            sub_rects = page.search_for(window_str)
            if sub_rects:
                matched_rects.extend(sub_rects)
        if matched_rects:
            return matched_rects

    # 3. Fallback to individual key phrases or stored chunk rects
    if fallback_rects:
        return [fitz.Rect(r) for r in fallback_rects]

    # Try matching first 3 words
    if len(words) >= 3:
        prefix = " ".join(words[:3])
        sub_rects = page.search_for(prefix)
        if sub_rects:
            return sub_rects

    return []

def find_table_row_rects(page: fitz.Page, quote: str, table_bbox: Optional[List[float]] = None) -> List[fitz.Rect]:
    """
    Detect row of table matching quote row items and span across table width.
    """
    cells = [c.strip() for c in quote.split("|") if c.strip() and "---" not in c]
    if not cells:
        return []

    # Find the primary cell (usually first column identifier e.g. state or metric)
    first_cell = cells[0]
    cell_rects = page.search_for(first_cell)
    
    if table_bbox:
        t_rect = fitz.Rect(table_bbox)
        # Filter rects that fall within table bbox
        cell_rects = [r for r in cell_rects if t_rect.contains(r) or t_rect.intersects(r)]

    if not cell_rects:
        return []

    target_cell = cell_rects[0]
    # Expand horizontally across table width if table_bbox exists
    if table_bbox:
        t_rect = fitz.Rect(table_bbox)
        row_band = fitz.Rect(t_rect.x0, target_cell.y0 - 2, t_rect.x1, target_cell.y1 + 2)
        return [row_band]
    else:
        # Expand across reasonable page width margin
        page_rect = page.rect
        row_band = fitz.Rect(page_rect.x0 + 36, target_cell.y0 - 2, page_rect.x1 - 36, target_cell.y1 + 2)
        return [row_band]

def render_highlighted_page_png(
    pdf_path: Path,
    page_number: int,
    quote: Optional[str] = None,
    chunk_rects: Optional[List[List[float]]] = None,
    is_table: bool = False,
    zoom: float = 1.6
) -> bytes:
    """
    Render page to PNG with warm yellow highlight burned into the cited passage/table row.
    Returns raw PNG bytes.
    """
    doc = fitz.open(str(pdf_path))
    if page_number < 1 or page_number > len(doc):
        raise ValueError(f"Page number {page_number} out of range (1..{len(doc)})")

    page = doc[page_number - 1]
    
    rects_to_highlight: List[fitz.Rect] = []

    if quote:
        if is_table:
            tb_box = chunk_rects[0] if (chunk_rects and len(chunk_rects) > 0) else None
            rects_to_highlight = find_table_row_rects(page, quote, tb_box)
            if not rects_to_highlight:
                rects_to_highlight = find_text_rects_on_page(page, quote, chunk_rects)
        else:
            rects_to_highlight = find_text_rects_on_page(page, quote, chunk_rects)
    elif chunk_rects:
        rects_to_highlight = [fitz.Rect(r) for r in chunk_rects]

    # Draw highlights onto page
    for r in rects_to_highlight:
        # Add highlight annot
        annot = page.add_highlight_annot(r)
        annot.set_colors(stroke=HIGHLIGHT_COLOR)
        annot.update()

    # Render at zoom
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    png_bytes = pix.tobytes(output="png")
    doc.close()
    return png_bytes

def get_normalized_page_rects(
    pdf_path: Path,
    page_number: int,
    quote: Optional[str] = None,
    chunk_rects: Optional[List[List[float]]] = None,
    is_table: bool = False
) -> Dict[str, Any]:
    """
    Return normalized [0..1] coordinates for v2 client-side PDF canvas highlighting.
    """
    doc = fitz.open(str(pdf_path))
    if page_number < 1 or page_number > len(doc):
        raise ValueError(f"Page number {page_number} out of range")

    page = doc[page_number - 1]
    page_w = page.rect.width
    page_h = page.rect.height

    rects_to_highlight: List[fitz.Rect] = []
    if quote:
        if is_table:
            tb_box = chunk_rects[0] if (chunk_rects and len(chunk_rects) > 0) else None
            rects_to_highlight = find_table_row_rects(page, quote, tb_box)
            if not rects_to_highlight:
                rects_to_highlight = find_text_rects_on_page(page, quote, chunk_rects)
        else:
            rects_to_highlight = find_text_rects_on_page(page, quote, chunk_rects)
    elif chunk_rects:
        rects_to_highlight = [fitz.Rect(r) for r in chunk_rects]

    normalized = []
    for r in rects_to_highlight:
        normalized.append({
            "x0": round(r.x0 / page_w, 4),
            "y0": round(r.y0 / page_h, 4),
            "x1": round(r.x1 / page_w, 4),
            "y1": round(r.y1 / page_h, 4)
        })

    doc.close()
    return {
        "page": page_number,
        "width": page_w,
        "height": page_h,
        "rects": normalized
    }

