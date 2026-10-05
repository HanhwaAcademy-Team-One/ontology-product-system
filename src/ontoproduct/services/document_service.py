from pathlib import Path
from uuid import UUID, uuid4

from ontoproduct.schemas.product import FileReference


MIME_TYPES = {".pdf": "application/pdf",
              ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
              ".txt": "text/plain"}


class DocumentService:
    def __init__(self, workspace, *, max_file_size=20 * 1024 * 1024):
        self.workspace = Path(workspace).resolve()
        self.max_file_size = max_file_size

    def save(self, session_id, name, content):
        session_id = str(UUID(session_id))
        if not isinstance(name, str) or not name or any(c in name for c in '/\\:*?"<>|') or name in {".", ".."}:
            raise ValueError("Invalid upload filename")
        if name.endswith((" ", ".")) or any(ord(c) < 32 for c in name):
            raise ValueError("Invalid upload filename")
        extension = Path(name).suffix.lower()
        if extension not in MIME_TYPES:
            raise ValueError("Supported files: PDF, XLSX, TXT")
        if not isinstance(content, bytes) or not content:
            raise ValueError("Uploaded file is empty")
        if len(content) > self.max_file_size:
            raise ValueError("Each upload must be 20 MB or smaller")
        folder = self.workspace / session_id
        folder.mkdir(parents=True, exist_ok=True)
        file_id = str(uuid4())
        destination = folder / f"{file_id}_{name}"
        destination.write_bytes(content)
        return FileReference(file_id=file_id, name=name, path=str(destination),
                             mime_type=MIME_TYPES[extension], size=len(content)).model_dump(mode="json")

    def validate_references(self, references):
        if not references:
            raise ValueError("At least one source document is required")
        for value in references:
            reference = FileReference.model_validate(value)
            path = Path(reference.path).resolve()
            if not path.is_relative_to(self.workspace) or not path.is_file():
                raise ValueError("Source document must exist inside the upload workspace")
            if path.stat().st_size != reference.size:
                raise ValueError("Source document size changed")
