import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import fitz  # PyMuPDF

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
    """Check if block falls inside header or footer margin."""
    y0, y1 = b[1], b[3]
    h = page_rect.height
    return y0 < (h * config.HEADER_FOOTER_MARGIN_PERCENT) or y1 > (h * (1.0 - config.HEADER_FOOTER_MARGIN_PERCENT))

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

def extract_cell_text_from_words(page: fitz.Page, cell_rect: fitz.Rect) -> str:
    """Extract and sort words within a cell bounding box to preserve decimals and order."""
    words = page.get_text("words", clip=cell_rect)
    if not words:
        return ""
    # word: (x0, y0, x1, y1, word_str, block_no, line_no, word_no)
    words_sorted = sorted(words, key=lambda w: (w[1], w[0]))
    return " ".join(w[4] for w in words_sorted).strip()

def process_table(
    page: fitz.Page,
    tab: fitz.table.Table,
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
            if re.match(r'^(Table|Statement|Chart|Box)\b', candidate, re.IGNORECASE) or len(candidate) < 120:
                caption = candidate.replace('\n', ' ')
                break

    # Extract raw cell grid
    raw_cells = tab.extract()
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
    combined_headers = []
    for c_idx in range(num_cols):
        col_parts = []
        for r_idx in range(header_rows_count):
            val = str(raw_cells[r_idx][c_idx] or '').strip()
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
            for c in row:
                cell_str = str(c or '').strip().replace("|", "/")
                formatted_cells.append(cell_str)
            md_lines.append("| " + " | ".join(formatted_cells) + " |")

        table_md = "\n".join(md_lines)
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
    """
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found at: {pdf_path}")

    doc = fitz.open(str(pdf_path))
    doc_name = pdf_path.name
    all_chunks: List[Dict[str, Any]] = []
    current_section = "General / Introduction"

    print(f"[Ingest] Ingesting {doc_name} ({len(doc)} pages)...")

    for page_idx in range(len(doc)):
        page = doc[page_idx]
        page_num = page_idx + 1
        page_label = detect_page_number_label(page)
        page_rect = page.rect

        # 1. Detect tables
        table_chunks: List[Dict[str, Any]] = []
        table_rects: List[fitz.Rect] = []

        try:
            tabs = page.find_tables()
            if tabs and tabs.tables:
                raw_blocks = page.get_text("blocks", sort=True)
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

        # 2. Extract and chunk text blocks (excluding table areas and headers/footers)
        blocks = page.get_text("blocks", sort=True)
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

            # Skip blocks that overlap significantly with tables
            overlaps_table = any(b_rect.intersects(tr) for tr in table_rects)
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

        # Append table chunks for this page
        all_chunks.extend(table_chunks)

    # Write output to jsonl
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        for chunk in all_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    print(f"[Ingest] Successfully ingested {len(all_chunks)} chunks into {output_file}")
    return all_chunks

if __name__ == "__main__":
    import sys
    target_pdf = Path(sys.argv[1]) if len(sys.argv) > 1 else config.PDF_PATH
    ingest_pdf(target_pdf)
