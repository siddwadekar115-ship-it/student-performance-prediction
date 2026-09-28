"""Write the report and the declaration as PDFs with the same margins and type."""

from __future__ import annotations

import sys
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph
from fpdf import FPDF

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def iter_blocks(doc):
    for child in doc.element.body.iterchildren():
        if child.tag == qn("w:p"):
            yield Paragraph(child, doc)
        elif child.tag == qn("w:tbl"):
            yield Table(child, doc)


def paragraph_image(paragraph: Paragraph):
    blips = paragraph._p.findall(".//" + qn("a:blip"))
    if not blips:
        return None
    embed = blips[0].get(qn("r:embed"))
    if not embed:
        return None
    part = paragraph.part.related_parts.get(embed)
    if part is None:
        return None
    return part.blob


class ReportPDF(FPDF):
    def __init__(self):
        super().__init__(format="A4", unit="mm")
        self.set_auto_page_break(auto=True, margin=19)
        self.set_margins(32, 19, 25)
        font_dir = Path("/System/Library/Fonts/Supplemental")
        self.add_font("TNR", "", str(font_dir / "Times New Roman.ttf"))
        self.add_font("TNR", "B", str(font_dir / "Times New Roman Bold.ttf"))
        self.add_font("CR", "", str(font_dir / "Courier New.ttf"))
        self.add_font("CR", "B", str(font_dir / "Courier New Bold.ttf"))
        self.add_page()
        self.set_font("TNR", size=12)

    def footer(self):
        self.set_y(-12)
        self.set_font("TNR", size=10)
        self.cell(0, 6, f"Student Performance Prediction Using Machine Learning    {self.page_no()}", align="C")

    def write_paragraph(self, paragraph: Paragraph):
        image = paragraph_image(paragraph)
        if image is not None:
            folder = ROOT / "report" / "figures"
            folder.mkdir(parents=True, exist_ok=True)
            path = folder / f"_pdf_{self.page_no()}_{abs(hash(image)) % 100000}.png"
            path.write_bytes(image)
            self.ln(2)
            self.image(str(path), w=150)
            self.ln(2)
            return
        text = paragraph.text
        if text == "":
            self.ln(4)
            return
        run = paragraph.runs[0] if paragraph.runs else None
        size = 12
        font = "TNR"
        bold = False
        if run is not None and run.font.size is not None:
            size = run.font.size.pt
        if run is not None and run.font.name == "Courier New":
            font = "CR"
        if run is not None and run.bold:
            bold = True
        style = "B" if bold else ""
        align = "J"
        if paragraph.alignment is not None and paragraph.alignment == 1:
            align = "C"
        elif paragraph.alignment is not None and paragraph.alignment == 0:
            align = "L"
        self.set_font(font, style=style, size=size)
        line_h = size * 0.50 if font == "CR" else size * 0.62
        self.multi_cell(0, line_h, text, align=align)
        self.ln(0.4 if font == "CR" else 1.5)

    def write_table(self, table: Table):
        rows = [[cell.text.replace("\n", " ") for cell in row.cells] for row in table.rows]
        if not rows:
            return
        cols = len(rows[0])
        width = self.epw / cols
        self.set_font("TNR", size=9)
        line_h = 4.2
        for row in rows:
            heights = []
            for value in row:
                lines = self.multi_cell(width, line_h, value, dry_run=True, output="LINES")
                heights.append(max(line_h, line_h * len(lines)))
            row_h = max(heights)
            if self.get_y() + row_h > self.page_break_trigger:
                self.add_page()
            x0 = self.get_x()
            y0 = self.get_y()
            x = x0
            for value in row:
                self.set_xy(x, y0)
                self.rect(x, y0, width, row_h)
                self.multi_cell(width, line_h, value)
                x += width
            self.set_xy(x0, y0 + row_h)
        self.ln(3)


def convert(src: Path, dest: Path) -> int:
    doc = Document(str(src))
    pdf = ReportPDF()
    for block in iter_blocks(doc):
        if isinstance(block, Paragraph):
            pdf.write_paragraph(block)
        else:
            pdf.write_table(block)
    pdf.output(str(dest))
    return pdf.page_no()


if __name__ == "__main__":
    report_pages = convert(ROOT / "Project_Report.docx", ROOT / "Project_Report.pdf")
    declaration_pages = convert(ROOT / "Self_Declaration.docx", ROOT / "Self_Declaration.pdf")
    print(f"report_pages {report_pages}")
    print(f"declaration_pages {declaration_pages}")
