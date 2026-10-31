"""
create_sample_report.py — Generates a self-contained synthetic statistical report PDF.
Includes:
- Cover page
- Executive Summary prose
- Table 3.1: Unemployment rate by state, 2024
- Table 4.1: Labour Force Participation Rate by Age and Sector
- Chapter notes and footnotes
"""
from pathlib import Path
import fitz  # PyMuPDF


def generate_sample_pdf(output_path: Path):
    doc = fitz.open()

    # --- Page 1: Cover Page ---
    page1 = doc.new_page(width=595, height=842)  # A4 size
    page1.insert_text((72, 140), "NATIONAL STATISTICAL REPORT", fontsize=22, fontname="helv", color=(0.1, 0.1, 0.3))
    page1.insert_text((72, 175), "ANNUAL STATISTICAL BULLETIN - 2024", fontsize=14, fontname="helv", color=(0.3, 0.3, 0.3))
    page1.insert_text((72, 215), "Ministry of Statistics and Programme Implementation", fontsize=11, fontname="helv", color=(0.4, 0.4, 0.4))
    page1.insert_text((72, 750), "Government Statistics Division, New Delhi", fontsize=10, fontname="helv", color=(0.5, 0.5, 0.5))

    # --- Page 2: Executive Summary (Prose) ---
    page2 = doc.new_page(width=595, height=842)
    page2.insert_text((72, 50), "National Statistical Report 2024", fontsize=9, fontname="helv", color=(0.6, 0.6, 0.6))
    page2.insert_text((72, 90), "Executive Summary & Key Findings", fontsize=16, fontname="helv", color=(0.1, 0.1, 0.3))
    summary_text = (
        "The Annual Employment and Labour Bulletin 2024 presents comprehensive indicators regarding labour force "
        "participation, unemployment rates, and demographic distributions across rural and urban sectors.\n\n"
        "During 2024, the nationwide Labour Force Participation Rate (LFPR) for persons aged 15 years and above "
        "stood at 56.4 per cent, marking an increase from 54.6 per cent recorded in 2023. "
        "Urban female participation witnessed a steady rise to 28.5 per cent, compared to 25.4 per cent in the prior survey.\n\n"
        "Total employment in the manufacturing sector expanded by 4.2 per cent year-on-year, while the services "
        "sector accounted for 54.1 per cent of gross value added."
    )
    rect2 = fitz.Rect(72, 120, 523, 300)
    page2.insert_textbox(rect2, summary_text, fontsize=10, fontname="helv", color=(0.15, 0.15, 0.15))
    page2.insert_text((280, 800), "1", fontsize=10, fontname="helv", color=(0.3, 0.3, 0.3))

    # --- Page 3: Chapter 3 Unemployment & Table 3.1 ---
    page3 = doc.new_page(width=595, height=842)
    page3.insert_text((72, 50), "Chapter 3: Unemployment Trends", fontsize=9, fontname="helv", color=(0.6, 0.6, 0.6))
    page3.insert_text((72, 85), "Chapter 3: Unemployment and State-wise Disparities", fontsize=14, fontname="helv", color=(0.1, 0.1, 0.3))
    
    body3 = (
        "This chapter examines unemployment metrics across states. In Kerala, the total unemployment rate for the "
        "calendar year 2024 was recorded at 9.9 per cent. Female unemployment remained higher at 14.3 per cent "
        "compared to 7.1 per cent for males. Conversely, Gujarat recorded the lowest overall unemployment at 3.8 per cent, "
        "with male unemployment at 3.1 per cent and female unemployment at 4.8 per cent. "
        "Punjab recorded an overall unemployment rate of 6.3 per cent, while Bihar stood at 10.2 per cent."
    )
    rect3 = fitz.Rect(72, 110, 523, 195)
    page3.insert_textbox(rect3, body3, fontsize=10, fontname="helv", color=(0.15, 0.15, 0.15))

    # Table 3.1
    page3.insert_text((72, 215), "Table 3.1: Unemployment rate by state, 2024 (per cent)", fontsize=11, fontname="helv", color=(0.1, 0.1, 0.2))

    table_x0, table_y0 = 72, 230
    col_widths = [140, 100, 100, 110]
    row_height = 24

    headers = ["State", "Male", "Female", "Total"]
    rows = [
        ["Kerala", "7.1", "14.3", "9.9"],
        ["Punjab", "5.2", "8.4", "6.3"],
        ["Bihar", "8.9", "12.1", "10.2"],
        ["Gujarat", "3.1", "4.8", "3.8"],
        ["All India Average", "5.8", "8.6", "6.7"]
    ]

    all_table_data = [headers] + rows

    for r_idx, row in enumerate(all_table_data):
        curr_y = table_y0 + r_idx * row_height
        if r_idx == 0:
            hdr_rect = fitz.Rect(table_x0, curr_y, table_x0 + sum(col_widths), curr_y + row_height)
            page3.draw_rect(hdr_rect, color=(0.8, 0.8, 0.85), fill=(0.92, 0.94, 0.98))

        curr_x = table_x0
        for c_idx, cell in enumerate(row):
            w = col_widths[c_idx]
            cell_rect = fitz.Rect(curr_x, curr_y, curr_x + w, curr_y + row_height)
            page3.draw_rect(cell_rect, color=(0.7, 0.7, 0.7), width=0.5)
            font_choice = "helv"
            font_size = 9
            text_x = curr_x + 8
            text_y = curr_y + 16
            page3.insert_text((text_x, text_y), cell, fontsize=font_size, fontname=font_choice, color=(0.1, 0.1, 0.1))
            curr_x += w

    page3.insert_text((72, 400), "Note: Figures refer to usual principal and subsidiary status (UPSS).", fontsize=8, fontname="helv", color=(0.4, 0.4, 0.4))
    page3.insert_text((280, 800), "43", fontsize=10, fontname="helv", color=(0.3, 0.3, 0.3))

    # --- Page 4: Chapter 4 Labour Force Participation & Table 4.1 ---
    page4 = doc.new_page(width=595, height=842)
    page4.insert_text((72, 50), "Chapter 4: Labour Force Participation Rate", fontsize=9, fontname="helv", color=(0.6, 0.6, 0.6))
    page4.insert_text((72, 85), "Chapter 4: Demographic Labour Force Distribution", fontsize=14, fontname="helv", color=(0.1, 0.1, 0.3))

    body4 = (
        "Labour Force Participation Rates vary considerably across demographic age bands and sectors. "
        "Among prime working age cohorts (25-54 years), overall participation reached 78.4 per cent nationwide. "
        "Rural male participation was highest at 84.2 per cent, while urban female participation recorded 31.6 per cent."
    )
    rect4 = fitz.Rect(72, 110, 523, 185)
    page4.insert_textbox(rect4, body4, fontsize=10, fontname="helv", color=(0.15, 0.15, 0.15))

    # Table 4.1
    page4.insert_text((72, 205), "Table 4.1: Labour Force Participation Rate by Age Group and Sector, 2024 (per cent)", fontsize=11, fontname="helv", color=(0.1, 0.1, 0.2))

    t2_x0, t2_y0 = 72, 220
    t2_widths = [110, 85, 85, 85, 85]
    t2_row_height = 24

    t2_headers = ["Age Group", "Rural Male", "Rural Female", "Urban Male", "Urban Female"]
    t2_rows = [
        ["15-24 Years", "52.4", "26.1", "44.8", "21.3"],
        ["25-54 Years", "84.2", "41.5", "81.9", "31.6"],
        ["55-64 Years", "68.7", "28.3", "59.4", "18.9"],
        ["65+ Years", "29.1", "8.4", "18.2", "5.1"],
        ["All Ages (15+)", "72.1", "34.2", "68.5", "28.5"]
    ]

    all_t2_data = [t2_headers] + t2_rows

    for r_idx, row in enumerate(all_t2_data):
        curr_y = t2_y0 + r_idx * t2_row_height
        if r_idx == 0:
            hdr_rect = fitz.Rect(t2_x0, curr_y, t2_x0 + sum(t2_widths), curr_y + t2_row_height)
            page4.draw_rect(hdr_rect, color=(0.8, 0.8, 0.85), fill=(0.92, 0.94, 0.98))

        curr_x = t2_x0
        for c_idx, cell in enumerate(row):
            w = t2_widths[c_idx]
            cell_rect = fitz.Rect(curr_x, curr_y, curr_x + w, curr_y + t2_row_height)
            page4.draw_rect(cell_rect, color=(0.7, 0.7, 0.7), width=0.5)
            font_choice = "helv"
            font_size = 9
            text_x = curr_x + 6
            text_y = curr_y + 16
            page4.insert_text((text_x, text_y), cell, fontsize=font_size, fontname=font_choice, color=(0.1, 0.1, 0.1))
            curr_x += w

    page4.insert_text((72, 395), "Source: National Sample Survey Organization (NSSO), 2024.", fontsize=8, fontname="helv", color=(0.4, 0.4, 0.4))
    page4.insert_text((280, 800), "54", fontsize=10, fontname="helv", color=(0.3, 0.3, 0.3))

    # --- Page 5: Chapter 5 Conclusion & Methodological Notes (Prose) ---
    page5 = doc.new_page(width=595, height=842)
    page5.insert_text((72, 50), "Chapter 5: Technical and Explanatory Notes", fontsize=9, fontname="helv", color=(0.6, 0.6, 0.6))
    page5.insert_text((72, 85), "Methodology and Statistical Definitions", fontsize=14, fontname="helv", color=(0.1, 0.1, 0.3))

    notes = (
        "Statistical definitions in this report follow standard international definitions adopted by the International "
        "Labour Organization (ILO).\n\n"
        "1. Labour Force: Persons who were either 'working' (or employed) or 'seeking or available for work' (or unemployed).\n"
        "2. Labour Force Participation Rate (LFPR): The percentage of population in the labour force.\n"
        "3. Unemployment Rate (UR): The percentage of persons unemployed among the persons in the labour force.\n\n"
        "Sampling errors are within acceptable statistical tolerance of 0.85 per cent at the 95 per cent confidence level."
    )
    rect5 = fitz.Rect(72, 110, 523, 300)
    page5.insert_textbox(rect5, notes, fontsize=10, fontname="helv", color=(0.15, 0.15, 0.15))
    page5.insert_text((280, 800), "62", fontsize=10, fontname="helv", color=(0.3, 0.3, 0.3))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    doc.close()
    print(f"Sample PDF successfully generated at: {output_path}")


if __name__ == "__main__":
    out = Path("data/report.pdf")
    generate_sample_pdf(out)
