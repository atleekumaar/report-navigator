import json
import re
import subprocess
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
try:
    import pymupdf as fitz
except ImportError:
    import fitz

import config


def clean_text(text: str) -> str:
    """Normalize whitespace and remove non-printable characters."""
    text = re.sub(r'[\r\f]+', '\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def detect_page_number_label(page: fitz.Page) -> str:
    """
    Attempt to extract the printed page number from header/footer areas.
    Falls back to str(page.number + 1) if not reliably detected.
    """
    rect = page.rect
    height = rect.height
    header_threshold = height * 0.08
    footer_threshold = height * 0.92

    blocks = page.get_text("blocks", sort=True)
    potential_labels = []

    for b in blocks:
        # b = (x0, y0, x1, y1, text, block_no, block_type)
        if b[6] != 0:  # text blocks only
            continue
        y0, y1, text = b[1], b[3], b[4].strip()
        if (y0 < header_threshold or y1 > footer_threshold) and text:
            # Check for solitary numbers or roman numerals
            cleaned = text.strip()
            if re.match(r'^(page\s+)?(\d{1,4}|[ivxlcdm]+)$', cleaned, re.IGNORECASE):
                num_part = re.sub(r'^[^\d]*', '', cleaned, flags=re.IGNORECASE)
                if num_part:
                    potential_labels.append(num_part)
                else:
                    potential_labels.append(cleaned)

    if potential_labels:
        return potential_labels[-1]  # Prefer footer
    return str(page.number + 1)


def is_header_footer(b: tuple, page_rect: fitz.Rect) -> bool:
    """Check if block falls completely inside header or footer margin."""
    y0, y1 = b[1], b[3]
    h = page_rect.height
    top_margin = h * config.HEADER_FOOTER_MARGIN_PERCENT
    bottom_margin = h * (1.0 - config.HEADER_FOOTER_MARGIN_PERCENT)
    # Must be entirely within top margin or entirely within bottom margin
    return y1 <= top_margin or y0 >= bottom_margin


def detect_heading(text: str) -> Optional[str]:
    """Detect if a block looks like a section or chapter heading."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines or len(lines) > 3:
        return None
    first_line = lines[0]
    # Check common chapter/section patterns
    if re.match(r'^(Chapter|Section|Part|Table of Contents|Executive Summary|Annexure|Appendix|\d+(\.\d+)*)\b', first_line, re.IGNORECASE):
        return " ".join(lines)
    # Check all caps short line
    if first_line.isupper() and 3 < len(first_line) < 60:
        return " ".join(lines)
    return None


def normalize_cell_text(cell_str: str) -> str:
    """Normalize cell text and fix PyMuPDF decimal splitting bugs (e.g. '71\\n.' -> '7.1')."""
    if not cell_str:
        return ""
    # Fix digits separated by newline and decimal dot: '71\n.' or '7\n.1' or '99\n.' -> reconstruct decimal
    s = cell_str.replace('\r', '').strip()
    s = re.sub(r'(\d+)\s*\n\s*\.\s*(\d*)', lambda m: f"{m.group(1)[:-1]}.{m.group(1)[-1]}{m.group(2)}" if len(m.group(1)) > 1 and not m.group(2) else f"{m.group(1)}.{m.group(2)}", s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s.replace("|", "/")


def ocr_page_text(page: fitz.Page, doc_path: Path) -> str:
    """
    OCR fallback for pages with very little extractable text.
    Tries PyMuPDF's built-in Tesseract integration first,
    then falls back to rendering the page as an image and calling Tesseract CLI.
    Returns the OCR'd text or empty string on failure.
    """
    # Method 1: PyMuPDF built-in OCR (requires Tesseract installed)
    try:
        tp = page.get_textpage_ocr(flags=fitz.TEXT_PRESERVE_WHITESPACE, full=True)
        ocr_text = page.get_text("text", textpage=tp).strip()
        if len(ocr_text) > config.OCR_MIN_CHARS:
            return ocr_text
    except Exception:
        pass  # Tesseract not available via PyMuPDF binding

    # Method 2: Render page to image and call Tesseract CLI
    if shutil.which("tesseract"):
        try:
            import tempfile
            mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better OCR
            pix = page.get_pixmap(matrix=mat, alpha=False)
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_img:
                pix.save(tmp_img.name)
                tmp_img_path = tmp_img.name

            result = subprocess.run(
                ["tesseract", tmp_img_path, "stdout", "-l", "eng", "--psm", "6"],
                capture_output=True, text=True, timeout=30
            )
            Path(tmp_img_path).unlink(missing_ok=True)
            ocr_text = result.stdout.strip()
            if len(ocr_text) > config.OCR_MIN_CHARS:
                return ocr_text
        except Exception as e:
            print(f"[Ingest] OCR CLI fallback failed: {e}")

    return ""


def process_table(
    page: fitz.Page,
    tab,
    table_index: int,
    current_section: str,
    page_label: str,
    doc_name: str,
    preceding_text_blocks: List[tuple]
) -> Tuple[List[Dict[str, Any]], fitz.Rect]:
    """
    Extract table structure, caption, headers, and split into row-chunk parts.
    Returns (chunks, table_bounding_box).
    """
    table_rect = tab.bbox
    t_rect = fitz.Rect(table_rect)

    # Find caption from preceding blocks close to table top
    caption = ""
    for b in reversed(preceding_text_blocks):
        b_rect = fitz.Rect(b[:4])
        # If block is above the table within 70 points
        if 0 < (t_rect.y0 - b_rect.y1) < 70:
            candidate = b[4].strip()
            if re.match(r'^(Table|Statement|Chart|Box|Exhibit|Annexure)\b', candidate, re.IGNORECASE) or len(candidate) < 120:
                caption = candidate.replace('\n', ' ')
                break

    # Extract raw cell grid
    try:
        raw_cells = tab.extract()
    except Exception as e:
        print(f"[Ingest] Table extraction failed on page {page.number + 1}, table {table_index}: {e}")
        return [], t_rect

    if not raw_cells or len(raw_cells) < 1:
        return [], t_rect

    # Multi-row header detection: absorb up to 3 initial rows that contain words but no digits
    header_rows_count = 1
    num_rows = len(raw_cells)
    for r_idx in range(1, min(3, num_rows)):
        row = raw_cells[r_idx]
        has_digit = any(any(ch.isdigit() for ch in str(c or '')) for c in row)
        if not has_digit:
            header_rows_count += 1
        else:
            break

    num_cols = len(raw_cells[0])
    # Guard against jagged rows
    for row in raw_cells:
        if len(row) > num_cols:
            num_cols = len(row)

    combined_headers = []
    for c_idx in range(num_cols):
        col_parts = []
        for r_idx in range(header_rows_count):
            if c_idx < len(raw_cells[r_idx]):
                val = str(raw_cells[r_idx][c_idx] or '').strip()
            else:
                val = ''
            if val and (not col_parts or col_parts[-1] != val):
                col_parts.append(val)
        hdr_text = " - ".join(col_parts).strip() or f"Col_{c_idx+1}"
        hdr_text = hdr_text.replace("|", "/")
        combined_headers.append(hdr_text)

    data_rows = raw_cells[header_rows_count:]
    if not data_rows:
        # Table was only headers
        data_rows = [["" for _ in range(num_cols)]]

    table_id = f"p{page.number + 1}-t{table_index}"
    chunks = []
    
    # Split large tables into chunks of ~TABLE_MAX_ROWS_PER_PART rows
    chunk_size = config.TABLE_MAX_ROWS_PER_PART
    for part_idx, i in enumerate(range(0, len(data_rows), chunk_size)):
        subset_rows = data_rows[i:i + chunk_size]
        
        md_lines = []
        if caption:
            md_lines.append(f"Table: {caption}")
        else:
            md_lines.append(f"Table: {table_id}")

        md_lines.append("| " + " | ".join(combined_headers) + " |")
        md_lines.append("| " + " | ".join(["---"] * num_cols) + " |")

        for row in subset_rows:
            formatted_cells = []
            for c_idx in range(num_cols):
                if c_idx < len(row):
                    cell_str = normalize_cell_text(str(row[c_idx] or ''))
                else:
                    cell_str = ''
                formatted_cells.append(cell_str)
            md_lines.append("| " + " | ".join(formatted_cells) + " |")

        table_md = "\n".join(md_lines)

        # Skip empty tables (only header, no real data)
        non_empty_cells = sum(1 for row in subset_rows for c in row if str(c or '').strip())
        if non_empty_cells == 0 and part_idx > 0:
            continue

        chunk_dict = {
            "id": f"p{page.number + 1:04d}-t{table_index:02d}-part{part_idx}",
            "doc": doc_name,
            "page": page.number + 1,
            "label": page_label,
            "type": "table",
            "section": current_section,
            "text": table_md,
            "rects": [[t_rect.x0, t_rect.y0, t_rect.x1, t_rect.y1]],
            "table_id": table_id,
            "part": part_idx,
            "caption": caption
        }
        chunks.append(chunk_dict)

    return chunks, t_rect


def ingest_pdf(pdf_path: Path, output_file: Path = config.CHUNKS_FILE) -> List[Dict[str, Any]]:
    """
    Ingest a PDF file into clean structured chunks adhering strictly to the chunk schema.
    Handles:
      - Text extraction with sentence-level chunking
      - Table extraction with configurable strategy (lines / text)
      - OCR fallback for scanned / image pages
      - Printed page label detection
      - Section heading tracking
    """
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found at: {pdf_path}")

    doc = fitz.open(str(pdf_path))
    doc_name = pdf_path.name
    all_chunks: List[Dict[str, Any]] = []
    current_section = "General / Introduction"
    table_strategy = config.TABLE_STRATEGY

    stats = {
        "total_pages": len(doc),
        "text_chunks": 0,
        "table_chunks": 0,
        "ocr_pages": 0,
        "empty_pages": 0,
        "tables_found": 0,
    }

    print(f"[Ingest] Ingesting {doc_name} ({len(doc)} pages, table_strategy={table_strategy})...")

    for page_idx in range(len(doc)):
        page = doc[page_idx]
        page_num = page_idx + 1
        page_label = detect_page_number_label(page)
        page_rect = page.rect

        raw_text = page.get_text("text").strip()

        # OCR fallback for pages with very little text (scanned / image pages)
        used_ocr = False
        if config.OCR_ENABLED and len(raw_text) < config.OCR_MIN_CHARS:
            ocr_text = ocr_page_text(page, pdf_path)
            if ocr_text:
                used_ocr = True
                stats["ocr_pages"] += 1
                print(f"[Ingest] Page {page_num}: OCR extracted {len(ocr_text)} chars")
                # For OCR pages, create a single text chunk (no table detection)
                chunk_text = clean_text(ocr_text)
                if chunk_text and len(chunk_text) >= config.MIN_CHUNK_CHARS:
                    all_chunks.append({
                        "id": f"p{page_num:04d}-ocr001",
                        "doc": doc_name,
                        "page": page_num,
                        "label": page_label,
                        "type": "text",
                        "section": current_section,
                        "text": chunk_text,
                        "rects": [[page_rect.x0, page_rect.y0, page_rect.x1, page_rect.y1]],
                        "table_id": None,
                        "part": None,
                        "ocr": True
                    })
                    stats["text_chunks"] += 1
                continue  # Skip normal processing for OCR pages

        if len(raw_text) < 5 and not used_ocr:
            stats["empty_pages"] += 1
            continue

        raw_blocks = page.get_text("blocks", sort=True)

        # Pre-scan blocks for section headings on this page so tables inherit the right section
        for b in raw_blocks:
            if b[6] == 0:
                h_candidate = detect_heading(b[4].strip())
                if h_candidate:
                    current_section = h_candidate
                    break

        # 1. Detect tables
        table_chunks: List[Dict[str, Any]] = []
        table_rects: List[fitz.Rect] = []

        try:
            strategy_kwarg = {}
            if table_strategy == "text":
                strategy_kwarg = {"strategy": "text"}

            tabs = page.find_tables(**strategy_kwarg)
            if tabs and tabs.tables:
                stats["tables_found"] += len(tabs.tables)
                for t_idx, tab in enumerate(tabs.tables):
                    t_chunks, t_bbox = process_table(
                        page=page,
                        tab=tab,
                        table_index=t_idx,
                        current_section=current_section,
                        page_label=page_label,
                        doc_name=doc_name,
                        preceding_text_blocks=raw_blocks
                    )
                    table_chunks.extend(t_chunks)
                    table_rects.append(t_bbox)
        except Exception as e:
            print(f"[Ingest] Table extraction warning on page {page_num}: {e}")
            # If strategy="lines" fails, try "text" as automatic fallback
            if table_strategy != "text":
                try:
                    tabs = page.find_tables(strategy="text")
                    if tabs and tabs.tables:
                        stats["tables_found"] += len(tabs.tables)
                        print(f"[Ingest] Page {page_num}: fallback to strategy='text' found {len(tabs.tables)} tables")
                        for t_idx, tab in enumerate(tabs.tables):
                            t_chunks, t_bbox = process_table(
                                page=page,
                                tab=tab,
                                table_index=t_idx,
                                current_section=current_section,
                                page_label=page_label,
                                doc_name=doc_name,
                                preceding_text_blocks=raw_blocks
                            )
                            table_chunks.extend(t_chunks)
                            table_rects.append(t_bbox)
                except Exception as e2:
                    print(f"[Ingest] Table fallback also failed on page {page_num}: {e2}")

        # 2. Extract and chunk text blocks (excluding table areas and headers/footers)
        blocks = raw_blocks
        text_accumulator = []
        rect_accumulator = []
        current_char_count = 0
        text_chunk_counter = 0

        for b in blocks:
            # b: (x0, y0, x1, y1, text, block_no, block_type)
            if b[6] != 0:
                continue
            b_rect = fitz.Rect(b[:4])
            raw_b_text = b[4].strip()
            if not raw_b_text:
                continue

            # Skip header/footer margin blocks
            if is_header_footer(b, page_rect):
                continue

            # Skip blocks that overlap significantly with table interior (> 35% of block area)
            overlaps_table = any(
                (b_rect & tr).get_area() > (0.35 * max(1.0, b_rect.get_area()))
                for tr in table_rects
            )
            if overlaps_table:
                continue

            # Check if this block is a section heading
            heading = detect_heading(raw_b_text)
            if heading:
                current_section = heading

            # Split overlong blocks on sentences
            sentences = re.split(r'(?<=[.!?])\s+', raw_b_text)
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue

                if current_char_count + len(sentence) > config.TARGET_CHUNK_CHARS and current_char_count >= config.MIN_CHUNK_CHARS:
                    # Flush accumulated chunk
                    chunk_text = clean_text(" ".join(text_accumulator))
                    if chunk_text:
                        text_chunk_counter += 1
                        all_chunks.append({
                            "id": f"p{page_num:04d}-txt{text_chunk_counter:03d}",
                            "doc": doc_name,
                            "page": page_num,
                            "label": page_label,
                            "type": "text",
                            "section": current_section,
                            "text": chunk_text,
                            "rects": rect_accumulator,
                            "table_id": None,
                            "part": None
                        })
                        stats["text_chunks"] += 1
                    text_accumulator = [sentence]
                    rect_accumulator = [[b_rect.x0, b_rect.y0, b_rect.x1, b_rect.y1]]
                    current_char_count = len(sentence)
                else:
                    text_accumulator.append(sentence)
                    rect_accumulator.append([b_rect.x0, b_rect.y0, b_rect.x1, b_rect.y1])
                    current_char_count += len(sentence)

        # Flush any remaining text for the page
        if text_accumulator:
            chunk_text = clean_text(" ".join(text_accumulator))
            if chunk_text:
                text_chunk_counter += 1
                all_chunks.append({
                    "id": f"p{page_num:04d}-txt{text_chunk_counter:03d}",
                    "doc": doc_name,
                    "page": page_num,
                    "label": page_label,
                    "type": "text",
                    "section": current_section,
                    "text": chunk_text,
                    "rects": rect_accumulator,
                    "table_id": None,
                    "part": None
                })
                stats["text_chunks"] += 1

        # Append table chunks for this page
        all_chunks.extend(table_chunks)
        stats["table_chunks"] += len(table_chunks)

    # Write output to jsonl
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        for chunk in all_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    doc.close()

    print(f"\n[Ingest] ==================== INGESTION REPORT ====================")
    print(f"  Document     : {doc_name}")
    print(f"  Total pages  : {stats['total_pages']}")
    print(f"  Empty pages  : {stats['empty_pages']}")
    print(f"  OCR pages    : {stats['ocr_pages']}")
    print(f"  Tables found : {stats['tables_found']}")
    print(f"  Text chunks  : {stats['text_chunks']}")
    print(f"  Table chunks : {stats['table_chunks']}")
    print(f"  TOTAL chunks : {len(all_chunks)}")
    print(f"  Output file  : {output_file}")
    print(f"  Strategy     : table_strategy={config.TABLE_STRATEGY}")
    print(f"[Ingest] =============================================================\n")

    return all_chunks


if __name__ == "__main__":
    import sys
    target_pdf = Path(sys.argv[1]) if len(sys.argv) > 1 else config.PDF_PATH
    ingest_pdf(target_pdf)
