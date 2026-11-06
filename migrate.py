from pathlib import Path

import psycopg

import db

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def migrate(conn: psycopg.Connection) -> list[str]:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        " name text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())"
    )
    applied = {r["name"] for r in conn.execute("SELECT name FROM schema_migrations")}
    ran = []
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if path.name in applied:
            continue
        with conn.transaction():
            conn.execute(path.read_text())
            conn.execute("INSERT INTO schema_migrations (name) VALUES (%s)", (path.name,))
        ran.append(path.name)
    conn.commit()
    return ran


if __name__ == "__main__":
    with db.connect() as conn:
        ran = migrate(conn)
    print(f"applied: {', '.join(ran)}" if ran else "up to date")
