"""
Script to create a realistic statistical test PDF for Report Navigator.
"""
from pathlib import Path
import fitz  # PyMuPDF

def generate_sample_pdf(output_path: Path):
    doc = fitz.open()

    # Page 1: Cover Page
    page1 = doc.new_page(width=595, height=842)  # A4 size
    page1.insert_text((72, 140), "NATIONAL EMPLOYMENT SURVEY REPORT", fontsize=20, fontname="helv", color=(0.1, 0.1, 0.3))
    page1.insert_text((72, 170), "ANNUAL STATISTICAL BULLETIN - 2024", fontsize=14, fontname="helv", color=(0.3, 0.3, 0.3))
    page1.insert_text((72, 210), "Ministry of Statistics and Programme Implementation", fontsize=11, fontname="helv", color=(0.4, 0.4, 0.4))
    page1.insert_text((72, 750), "Government Statistics Division", fontsize=10, fontname="helv", color=(0.5, 0.5, 0.5))

    # Page 2: Executive Summary
    page2 = doc.new_page(width=595, height=842)
    page2.insert_text((72, 50), "National Employment Survey Report 2024", fontsize=9, fontname="helv", color=(0.6, 0.6, 0.6))
    page2.insert_text((72, 90), "Executive Summary & Key Findings", fontsize=16, fontname="helv", color=(0.1, 0.1, 0.3))
    summary_text = (
        "The Annual Employment Survey 2024 presents comprehensive indicators regarding labour force "
        "participation, unemployment rates, and demographic distributions across rural and urban sectors. "
        "During 2024, the nationwide Labour Force Participation Rate (LFPR) for persons aged 15 years and above "
        "stood at 56.4 per cent, marking an increase from 54.6 per cent recorded in 2023. "
        "Urban female participation witnessed a steady rise to 28.5 per cent."
    )
    rect2 = fitz.Rect(72, 120, 523, 260)
    page2.insert_textbox(rect2, summary_text, fontsize=10, fontname="helv", color=(0.15, 0.15, 0.15))
    page2.insert_text((280, 800), "1", fontsize=10, fontname="helv", color=(0.3, 0.3, 0.3))

    # Page 3: Chapter 3 Unemployment
    page3 = doc.new_page(width=595, height=842)
    page3.insert_text((72, 50), "Chapter 3: Unemployment Trends", fontsize=9, fontname="helv", color=(0.6, 0.6, 0.6))
    page3.insert_text((72, 85), "Chapter 3: Unemployment and State-wise Disparities", fontsize=14, fontname="helv", color=(0.1, 0.1, 0.3))
    
    body3 = (
        "This chapter examines unemployment metrics across states. In Kerala, the total unemployment rate for the "
        "calendar year 2024 was recorded at 9.9 per cent. Female unemployment remained higher at 14.3 per cent "
        "compared to 7.1 per cent for males. Conversely, Gujarat recorded the lowest overall unemployment at 3.8 per cent."
    )
    rect3 = fitz.Rect(72, 110, 523, 180)
    page3.insert_textbox(rect3, body3, fontsize=10, fontname="helv", color=(0.15, 0.15, 0.15))

    # Table 3.1
    page3.insert_text((72, 215), "Table 3.1: Unemployment rate by state, 2024 (per cent)", fontsize=11, fontname="helv", color=(0.1, 0.1, 0.2))

    # Draw table borders and text
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
        # Draw background for header
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

    # Footnote
    page3.insert_text((72, 400), "Note: Figures refer to usual principal and subsidiary status (UPSS).", fontsize=8, fontname="helv", color=(0.4, 0.4, 0.4))
    page3.insert_text((280, 800), "43", fontsize=10, fontname="helv", color=(0.3, 0.3, 0.3))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    doc.close()
    print(f"Sample PDF successfully generated at: {output_path}")

if __name__ == "__main__":
    out = Path("data/report.pdf")
    generate_sample_pdf(out)

