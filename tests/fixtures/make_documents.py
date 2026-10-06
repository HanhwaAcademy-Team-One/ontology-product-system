"""Regenerate the parser fixtures: uv run python tests/fixtures/make_documents.py"""
from datetime import datetime, timezone
from pathlib import Path

from fpdf import FPDF
from openpyxl import Workbook

OUT = Path(__file__).parent / "documents"
FIXED_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)
MOTOR_TEXT = ("Product: DM-600\nClass: BLDCMotor\nManufacturer: XYZ Motors\n"
              "Rated Voltage: 24 V\nRated Power: 0.6 kW\nRated Speed: 3200 rpm\n"
              "비고: 한글 English 혼합 문서 ±5% Ω\n")


def new_pdf():
    pdf = FPDF()
    pdf.set_creation_date(FIXED_TIME)
    pdf.set_font("Helvetica", size=12)
    return pdf


def make_text():
    (OUT / "motor_spec.txt").write_text(MOTOR_TEXT, encoding="utf-8")
    (OUT / "motor_spec_cp949.txt").write_bytes(MOTOR_TEXT.replace("±5% Ω", "").encode("cp949"))


def make_pdf():
    pdf = new_pdf()
    pdf.add_page()
    pdf.multi_cell(0, 8, "Product: DM-600\nClass: BLDCMotor\nManufacturer: XYZ Motors")
    pdf.add_page()
    pdf.cell(0, 10, "Electrical Ratings", new_x="LMARGIN", new_y="NEXT")
    with pdf.table(col_widths=(60, 40, 30)) as table:
        for row in [("Item", "Value", "Unit"), ("Power", "0.6", "kW"),
                    ("Voltage", "24", "V"), ("Speed", "3200", "rpm")]:
            cells = table.row()
            for value in row:
                cells.cell(value)
    pdf.output(OUT / "two_page_spec.pdf")


def make_scanned_pdf():
    # Vector shapes only: no extractable text, like a scanned page.
    pdf = new_pdf()
    pdf.add_page()
    pdf.rect(20, 20, 120, 40, style="F")
    pdf.output(OUT / "scanned.pdf")


def make_xlsx():
    workbook = Workbook()
    spec = workbook.active
    spec.title = "Spec"
    for row in [("Item", "Value", "Unit"), ("Product", "DM-600", None),
                ("Manufacturer", "XYZ Motors", None), ("정격 전압", 24, "V")]:
        spec.append(row)
    electrical = workbook.create_sheet("Electrical")
    electrical["A1"], electrical["B1"], electrical["C1"] = "Rated Power", 0.6, "kW"
    electrical["A3"], electrical["C3"] = "Rated Speed", "rpm"
    electrical["B3"] = 3200
    workbook.properties.created = workbook.properties.modified = FIXED_TIME.replace(tzinfo=None)
    workbook.save(OUT / "two_sheet_spec.xlsx")


def make_corrupt():
    (OUT / "corrupt.pdf").write_bytes((OUT / "two_page_spec.pdf").read_bytes()[:200])
    (OUT / "corrupt.xlsx").write_bytes((OUT / "two_sheet_spec.xlsx").read_bytes()[:200])


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    make_text()
    make_pdf()
    make_scanned_pdf()
    make_xlsx()
    make_corrupt()
