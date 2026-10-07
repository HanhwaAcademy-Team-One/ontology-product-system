from datetime import datetime, timezone


class RegistrationRepository:
    def __init__(self, database):
        self.database = database

    def create(self, thread_id, session_id):
        now = datetime.now(timezone.utc).isoformat()
        with self.database.connect() as connection:
            connection.execute(
                "INSERT INTO registration_cases VALUES (?, ?, ?, ?, ?)",
                (thread_id, session_id, "NEW", now, now),
            )

    def update_status(self, thread_id, status):
        with self.database.connect() as connection:
            connection.execute(
                "UPDATE registration_cases SET status=?, updated_at=? WHERE thread_id=?",
                (status, datetime.now(timezone.utc).isoformat(), thread_id),
            )

    def get(self, thread_id):
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM registration_cases WHERE thread_id=?", (thread_id,)
            ).fetchone()
        return dict(row) if row else None

    def list(self, *, limit=100):
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM registration_cases ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def summary(self):
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT status, COUNT(*) AS count FROM registration_cases GROUP BY status"
            ).fetchall()
        return {
            "total": sum(row["count"] for row in rows),
            "statuses": {row["status"]: row["count"] for row in rows},
        }
