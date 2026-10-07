import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ApplicationPaths:
    root: Path

    @classmethod
    def from_environment(cls):
        return cls(
            Path(
                os.environ.get("ONTOPRODUCT_DATA_DIR", str(Path.cwd() / "runtime"))
            ).resolve()
        )

    @property
    def product_db(self):
        return self.root / "data" / "ontoproduct.db"

    @property
    def checkpoint_db(self):
        return self.root / "data" / "checkpoints.db"

    @property
    def uploads(self):
        return self.root / "uploads"

    @property
    def exports(self):
        return self.root / "exports"
