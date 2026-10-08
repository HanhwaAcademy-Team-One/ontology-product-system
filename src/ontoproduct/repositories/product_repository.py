import json
from datetime import datetime, timezone
from uuid import uuid4


class ProductRepository:
    def __init__(self, database):
        self.database = database

    @staticmethod
    def _record(row):
        if row is None:
            return None
        return {
            "product_id": row["product_id"],
            "registration_case_id": row["registration_case_id"],
            "product": json.loads(row["product_json"]),
            "created_at": row["created_at"],
            "origin": row["origin"],
        }

    def save(self, case_id, product, *, origin="REGISTRATION"):
        payload = json.dumps(
            product, ensure_ascii=False, allow_nan=False, sort_keys=True
        )
        with self.database.connect() as connection:
            cursor = connection.execute(
                """INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(registration_case_id) DO NOTHING""",
                (
                    str(uuid4()),
                    case_id,
                    product.get("product_name"),
                    product["product_class"],
                    payload,
                    datetime.now(timezone.utc).isoformat(),
                    origin,
                ),
            )
            status = "REGISTERED" if cursor.rowcount == 1 else "ALREADY_REGISTERED"
            row = connection.execute(
                "SELECT * FROM products WHERE registration_case_id=?", (case_id,)
            ).fetchone()
        return {"status": status, "record": self._record(row)}

    def get_by_case(self, case_id):
        with self.database.connect() as connection:
            return self._record(
                connection.execute(
                    "SELECT * FROM products WHERE registration_case_id=?", (case_id,)
                ).fetchone()
            )

    def get(self, product_id):
        with self.database.connect() as connection:
            return self._record(
                connection.execute(
                    "SELECT * FROM products WHERE product_id=?", (product_id,)
                ).fetchone()
            )

    def list(self, *, search="", limit=500, product_class=None, origin=None):
        # Escape LIKE wildcards so the search text matches literally; LIMIT -1 means no limit in SQLite.
        pattern = (
            "%"
            + search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            + "%"
        )
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM products WHERE COALESCE(product_name,'') LIKE ? ESCAPE '\\' AND (? IS NULL OR product_class=?) AND (? IS NULL OR origin=?) ORDER BY created_at DESC LIMIT ?",
                (
                    pattern,
                    product_class,
                    product_class,
                    origin,
                    origin,
                    -1 if limit is None else limit,
                ),
            ).fetchall()
        return [self._record(row) for row in rows]

    def count(self):
        with self.database.connect() as connection:
            return connection.execute("SELECT COUNT(*) FROM products").fetchone()[0]

    def summary(self):
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT product_class, origin, COUNT(*) AS count FROM products GROUP BY product_class, origin"
            ).fetchall()
        return {
            "total": sum(row["count"] for row in rows),
            "registered": sum(
                row["count"] for row in rows if row["origin"] == "REGISTRATION"
            ),
            "seed": sum(row["count"] for row in rows if row["origin"] == "SEED"),
            "groups": [dict(row) for row in rows],
        }
