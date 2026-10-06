from collections import Counter
from pathlib import Path

import openpyxl
import pdfplumber

from ontoproduct.schemas.product import FileReference, ParsedDocument
from ontoproduct.services.document_service import DocumentService


class ParserService:
    """Read uploaded TXT/PDF/XLSX files into ParsedDocument dictionaries.

    page is None for TXT and XLSX and the 1-based page number for PDF. Excel sheet and
    cell positions are kept inside text because ParsedDocument has no field for them.
    Scanned PDFs without a text layer are rejected; OCR is not supported.
    """

    def __init__(self, workspace):
        self.documents = DocumentService(workspace)

    def parse(self, references):
        self.documents.validate_references(references)
        refs = [FileReference.model_validate(value) for value in references]
        name_counts = Counter(ref.name for ref in refs)
        parsed = []
        for ref in refs:
            reader = READERS.get(Path(ref.name).suffix.lower())
            if reader is None:
                raise ValueError(f"{ref.name}: 지원하지 않는 파일 형식입니다")
            source = ref.name if name_counts[ref.name] == 1 else f"{ref.name} ({ref.file_id[:8]})"
            try:
                items = reader(Path(ref.path))
            except ValueError as exc:
                raise ValueError(f"{ref.name}: {exc}") from exc
            except Exception as exc:
                raise ValueError(f"{ref.name}: 문서를 읽을 수 없습니다 ({type(exc).__name__}: {exc})") from exc
            parsed += [ParsedDocument(source_file=source, text=text, page=page).model_dump(mode="json")
                       for page, text in items]
        return parsed


def read_txt(path):
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "cp949"):
        try:
            text = data.decode(encoding).replace("\r\n", "\n")
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError("텍스트 인코딩을 판별할 수 없습니다 (UTF-8, CP949 지원)")
    if not text.strip():
        raise ValueError("읽을 수 있는 텍스트가 없습니다")
    return [(None, text)]


def read_pdf(path):
    pages = []
    with pdfplumber.open(path) as pdf:
        for number, page in enumerate(pdf.pages, start=1):
            # extract_text loses cell boundaries, so tables are appended row by row.
            blocks = [page.extract_text() or ""]
            for index, table in enumerate(page.extract_tables(), start=1):
                rows = [" | ".join((cell or "").strip() for cell in row) for row in table]
                blocks.append(f"[Table {index}]\n" + "\n".join(rows))
            text = "\n\n".join(block for block in blocks if block.strip())
            if text:
                pages.append((number, text))
    if not pages:
        raise ValueError("읽을 수 있는 텍스트가 없습니다 (스캔 PDF OCR 미지원)")
    return pages


def read_xlsx(path):
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        sheets = []
        for sheet in workbook.worksheets:
            lines = []
            for row in sheet.iter_rows():
                cells = [cell for cell in row if cell.value is not None and str(cell.value).strip()]
                if cells:
                    values = " | ".join(f"{cell.coordinate}={cell.value}" for cell in cells)
                    lines.append(f"[Sheet: {sheet.title}, Row: {cells[0].row}] {values}")
            if lines:
                sheets.append((None, "\n".join(lines)))
    finally:
        workbook.close()
    if not sheets:
        raise ValueError("시트에 읽을 수 있는 값이 없습니다")
    return sheets


READERS = {".txt": read_txt, ".pdf": read_pdf, ".xlsx": read_xlsx}
