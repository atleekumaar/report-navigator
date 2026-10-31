"""
table_engine.py — Extract, normalise, classify and index every table in a PDF.

Design decisions
================
* We never assume page numbers or table positions are fixed.
  Everything is discovered at ingest time from headers / captions.
* Cell text normalisation handles PyMuPDF quirks:
    '1029\\n,' → '1029'  (digit + newline + comma)
    '71\\n.'  → '7.1'   (split decimal)
    '119904\\n, ,' → '119904'
* Tables are classified into canonical types by header fingerprints.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pymupdf as fitz


# ---------------------------------------------------------------------------
# Cell normalisation
# ---------------------------------------------------------------------------

def normalise_cell(raw: Optional[str]) -> str:
    """Clean a single cell value extracted by PyMuPDF."""
    if raw is None:
        return ""
    s = str(raw).strip()
    if not s:
        return ""

    # 1. Fix split decimals:  '71\n.'  → '7.1',  '195\n.' → '19.5'
    s = re.sub(
        r'(\d+)\s*\n\s*\.\s*(\d*)',
        lambda m: (
            f"{m.group(1)[:-1]}.{m.group(1)[-1]}{m.group(2)}"
            if len(m.group(1)) > 1 and not m.group(2)
            else f"{m.group(1)}.{m.group(2)}"
        ),
        s,
    )
    # 2. Fix split negative signs:  '- .' → '-'  or  '-1 .9' → '-1.9'
    s = re.sub(r'-\s*(\d)', r'-\1', s)
    # 3. Remove newlines, commas, spaces inside numeric tokens
    #    '119904\n, ,' → '119904'   but keep text words intact
    s = re.sub(r'\n', ' ', s)
    s = re.sub(r'\s*,\s*', '', s)  # strip all commas
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def cell_to_int(raw: Optional[str]) -> Optional[int]:
    """Try to parse a cell as an integer (after normalisation)."""
    s = normalise_cell(raw)
    if not s:
        return None
    # Grab the leading integer part (ignore decimals / trailing text)
    m = re.match(r'^-?(\d+)', s)
    if m:
        return int(m.group(0))
    return None


# ---------------------------------------------------------------------------
# Table classification
# ---------------------------------------------------------------------------

# Canonical table types we know how to query.
#  key  → human-readable name
TABLE_TYPES = {
    "city_summary":       "Million-plus cities overview (accidents / killed / injured)",
    "state_accidents":    "State/UT-wise road accidents",
    "state_killed":       "State/UT-wise persons killed",
    "state_injured":      "State/UT-wise persons injured",
    "collision_type":     "Collision-type breakdown (national)",
    "violation_national": "Traffic violation breakdown (national, e.g. over-speeding)",
    "road_user_national": "Road-user category breakdown (national)",
    "city_road_users":    "City × road-user type (Annexure 46 style)",
    "city_violations":    "City × violation type (Annexure 49 style)",
}

# Header fingerprint → table type.
# We match against the flattened, lowercased, whitespace-stripped header text.
_FINGERPRINTS: List[Tuple[str, List[str], List[str]]] = [
    # (type_key, must_contain_ALL, must_not_contain_ANY)
    ("city_summary",       ["million", "totalaccidents"], []),
    ("city_summary",       ["millionpluscities", "killed"], []),
    ("state_accidents",    ["states", "totalnumberofroadaccidents"], []),
    ("state_killed",       ["states", "totalnumberofpersonskilled"], []),
    ("state_killed",       ["states", "personskilled"], ["injured", "accidents"]),
    ("state_injured",      ["states", "personsinjured"], ["killed"]),
    ("collision_type",     ["typeofcollision"], []),
    ("collision_type",     ["collisiontype"], []),
    ("violation_national", ["over-speeding", "fatalities"], ["million", "cities"]),
    ("violation_national", ["overspeeding", "fatalities"], ["million", "cities"]),
    ("road_user_national", ["roadusercategory", "personskilled"], []),
    ("road_user_national", ["road-usercategory", "personskilled"], []),
    ("road_user_national", ["pedestrian", "shareintotal", "personskilled"], []),
    ("city_road_users",    ["pedestrian", "twowheeler"], ["over-speeding", "overspeeding", "violation"]),
    ("city_road_users",    ["pedestrian", "bicycles", "twowheelers"], []),
    ("city_violations",    ["over-speeding", "wrongside"], []),
    ("city_violations",    ["overspeeding", "drunken"], []),
]


def classify_table(header_text: str) -> Optional[str]:
    """Return the canonical table type, or None if unrecognised."""
    h = re.sub(r'[\s,\-]+', '', header_text.lower())  # flatten
    for ttype, musts, nots in _FINGERPRINTS:
        if all(m.replace('-', '') in h for m in musts):
            if not any(n.replace('-', '') in h for n in nots):
                return ttype
    return None


# ---------------------------------------------------------------------------
# Structured table representation
# ---------------------------------------------------------------------------

@dataclass
class StructuredTable:
    """A single extracted and normalised table."""
    page: int                     # 1-based PDF page index
    table_type: Optional[str]     # canonical type or None
    headers: List[str]            # combined column headers
    rows: List[List[str]]         # normalised cell values
    raw_header_text: str          # for debugging
    caption: str = ""
    bbox: Tuple[float, ...] = ()

    # --- convenience ----------------------------------------------------------

    def find_row(self, entity: str, col: int = 1) -> Optional[int]:
        """Return the row index whose *col*-th cell best matches *entity*.

        Matching rules (tried in order):
        1. Exact substring (case-insensitive, after stripping non-alpha)
        2. Prefix match (≥ 5 chars)
        """
        entity_clean = re.sub(r'[^a-zA-Z]', '', entity).lower()
        if not entity_clean:
            return None

        best_idx: Optional[int] = None
        best_len = 0

        for r_idx, row in enumerate(self.rows):
            if col >= len(row):
                continue
            cell = re.sub(r'[^a-zA-Z]', '', row[col]).lower()
            if not cell:
                # Also check col 0 for tables where name is in first column
                cell = re.sub(r'[^a-zA-Z]', '', row[0]).lower() if row[0] else ""
            if not cell:
                continue

            # Exact containment (both ways)
            if entity_clean in cell or cell in entity_clean:
                match_len = min(len(entity_clean), len(cell))
                if match_len > best_len:
                    best_len = match_len
                    best_idx = r_idx
            # Prefix
            elif len(entity_clean) >= 5 and (cell.startswith(entity_clean[:5]) or entity_clean.startswith(cell[:5])):
                if 5 > best_len:
                    best_len = 5
                    best_idx = r_idx

        return best_idx

    def cell_int(self, row_idx: int, col_idx: int) -> Optional[int]:
        """Return the integer value at (row, col), or None."""
        if row_idx < 0 or row_idx >= len(self.rows):
            return None
        if col_idx < 0 or col_idx >= len(self.rows[row_idx]):
            return None
        return cell_to_int(self.rows[row_idx][col_idx])

    def to_markdown(self, max_rows: int = 999) -> str:
        """Render table as Markdown for LLM / debugging."""
        lines = []
        if self.caption:
            lines.append(f"**{self.caption}**")
        lines.append("| " + " | ".join(self.headers) + " |")
        lines.append("| " + " | ".join(["---"] * len(self.headers)) + " |")
        for row in self.rows[:max_rows]:
            lines.append("| " + " | ".join(row) + " |")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Table extraction from a full PDF
# ---------------------------------------------------------------------------

@dataclass
class TableIndex:
    """All extracted tables, indexed by type for O(1) lookup."""
    tables: List[StructuredTable] = field(default_factory=list)
    by_type: Dict[str, List[StructuredTable]] = field(default_factory=dict)
    page_count: int = 0

    def get(self, ttype: str) -> List[StructuredTable]:
        return self.by_type.get(ttype, [])


def extract_tables(pdf_path: str | Path) -> TableIndex:
    """Open *pdf_path* and extract + classify every table.

    Returns a :class:`TableIndex` you can query by type.
    """
    doc = fitz.open(str(pdf_path))
    index = TableIndex(page_count=len(doc))
    seen_types: Dict[str, int] = {}

    for page_idx in range(len(doc)):
        page = doc[page_idx]
        page_num = page_idx + 1

        try:
            found = page.find_tables()
        except Exception:
            continue

        if not found or not found.tables:
            continue

        # Gather text blocks for caption detection
        blocks = page.get_text("blocks", sort=True)

        for t_idx, tab in enumerate(found.tables):
            raw = tab.extract()
            if not raw or len(raw) < 2:
                continue

            # -- Detect header rows (up to 4 rows) --
            n_header = 0
            for r_idx in range(min(4, len(raw))):
                # A header row has mostly non-digit cells
                digit_cells = sum(
                    1 for c in raw[r_idx]
                    if c and re.search(r'\d', str(c))
                )
                total_cells = sum(1 for c in raw[r_idx] if c)
                if total_cells == 0 or digit_cells / max(total_cells, 1) < 0.6:
                    n_header += 1
                else:
                    break

            n_header = max(n_header, 1)

            # Build combined headers
            num_cols = max(len(r) for r in raw)
            headers = []
            for c_idx in range(num_cols):
                parts = []
                for r_idx in range(n_header):
                    if c_idx < len(raw[r_idx]):
                        v = normalise_cell(raw[r_idx][c_idx])
                        if v and (not parts or parts[-1] != v):
                            parts.append(v)
                headers.append(" - ".join(parts) if parts else f"Col{c_idx+1}")

            raw_header_text = " ".join(headers)

            # Normalise data rows
            data_rows = []
            for r_idx in range(n_header, len(raw)):
                row = []
                for c_idx in range(num_cols):
                    if c_idx < len(raw[r_idx]):
                        row.append(normalise_cell(raw[r_idx][c_idx]))
                    else:
                        row.append("")
                data_rows.append(row)

            # Detect caption
            caption = ""
            t_rect = fitz.Rect(tab.bbox)
            for b in reversed(blocks):
                if b[6] != 0:
                    continue
                b_rect = fitz.Rect(b[:4])
                gap = t_rect.y0 - b_rect.y1
                if 0 < gap < 70:
                    cand = b[4].strip().replace('\n', ' ')
                    if re.match(r'^(Table|Statement|Annexure|Chart)\b', cand, re.IGNORECASE) or len(cand) < 140:
                        caption = cand
                        break

            # Classify
            ttype = classify_table(raw_header_text + " " + caption)

            st = StructuredTable(
                page=page_num,
                table_type=ttype,
                headers=headers,
                rows=data_rows,
                raw_header_text=raw_header_text,
                caption=caption,
                bbox=tuple(tab.bbox),
            )
            index.tables.append(st)

            if ttype:
                index.by_type.setdefault(ttype, []).append(st)
                seen_types[ttype] = seen_types.get(ttype, 0) + 1

    doc.close()

    print(f"[TableEngine] Extracted {len(index.tables)} tables across {index.page_count} pages.")
    for k, v in seen_types.items():
        print(f"  {k}: {v} table(s)")
    return index

