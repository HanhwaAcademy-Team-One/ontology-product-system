import json
from pathlib import Path
from uuid import uuid4

import pytest

from ontoproduct.schemas.product import FileReference
from ontoproduct.services.document_service import DocumentService


def test_multiple_uploads_become_json_file_references(tmp_path):
    documents = DocumentService(tmp_path / "uploads")
    session = str(uuid4())
    refs = [
        documents.save(session, "motor_spec.pdf", b"%PDF mock"),
        documents.save(session, "bom.xlsx", b"mock workbook"),
    ]
    documents.validate_references(refs)
    json.dumps(refs)
    assert all(set(ref) == set(FileReference.model_fields) for ref in refs)
    assert Path(refs[0]["path"]).read_bytes() == b"%PDF mock"
    assert Path(refs[1]["path"]).read_bytes() == b"mock workbook"
    again = documents.save(session, "motor_spec.pdf", b"another document")
    assert again["path"] != refs[0]["path"]


@pytest.mark.parametrize(
    "name", ["../bad.pdf", "folder/bad.pdf", "folder\\bad.pdf", "bad.exe", "bad.pdf."]
)
def test_upload_rejects_invalid_names(tmp_path, name):
    with pytest.raises(ValueError):
        DocumentService(tmp_path).save(str(uuid4()), name, b"content")


def test_upload_rejects_empty_oversized_or_invalid_session(tmp_path):
    service = DocumentService(tmp_path, max_file_size=3)
    for session, data in [
        (str(uuid4()), b""),
        (str(uuid4()), b"1234"),
        ("../../bad", b"123"),
    ]:
        with pytest.raises(ValueError):
            service.save(session, "x.pdf", data)


def test_reference_must_stay_inside_workspace_and_keep_size(tmp_path):
    service = DocumentService(tmp_path / "uploads")
    session = str(uuid4())
    ref = service.save(session, "x.txt", b"abc")
    Path(ref["path"]).write_bytes(b"changed")
    with pytest.raises(ValueError):
        service.validate_references([ref])
    outside = tmp_path / "outside.txt"
    outside.write_bytes(b"abc")
    ref.update(path=str(outside), size=3)
    with pytest.raises(ValueError):
        service.validate_references([ref])
