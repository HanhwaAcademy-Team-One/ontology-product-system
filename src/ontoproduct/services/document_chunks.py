"""Bound document payloads without dropping pages, rows, or the document tail."""

from ontoproduct.schemas.product import ParsedDocument
from ontoproduct.services.evidence_service import EXCEL_PREFIX


def document_chunks(
    documents: list[ParsedDocument], *, max_chars=12000, overlap_chars=128
):
    if type(max_chars) is not int or max_chars < 64:
        raise ValueError("max_chars must be an integer of at least 64")
    if type(overlap_chars) is not int or not 0 <= overlap_chars < max_chars:
        raise ValueError("overlap_chars must be between zero and max_chars - 1")
    for document in documents:
        pending = ""
        for line in document.text.splitlines(keepends=True):
            if len(line) > max_chars:
                if pending:
                    yield {**document.model_dump(mode="json"), "text": pending}
                    pending = ""
                location = EXCEL_PREFIX.match(line)
                position = 0
                while position < len(line):
                    end = min(position + max_chars, len(line))
                    chunk = {
                        **document.model_dump(mode="json"),
                        "text": line[position:end],
                    }
                    if location:
                        chunk["location_prefix"] = location.group()
                    yield chunk
                    if end == len(line):
                        break
                    position = end - overlap_chars
            else:
                if pending and len(pending) + len(line) > max_chars:
                    yield {**document.model_dump(mode="json"), "text": pending}
                    pending = ""
                pending += line
        if pending:
            yield {**document.model_dump(mode="json"), "text": pending}
