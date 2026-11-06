import argparse
import hashlib

import psycopg

import db
from ingest.planetterp import PlanetTerp

GPA_POINTS = {
    "A+": 4.0, "A": 4.0, "A-": 3.7,
    "B+": 3.3, "B": 3.0, "B-": 2.7,
    "C+": 2.3, "C": 2.0, "C-": 1.7,
    "D+": 1.3, "D": 1.0, "D-": 0.7,
    "F": 0.0,
}


def average_gpa(sections: list[dict]) -> float | None:
    points = students = 0
    for section in sections:
        for grade, value in GPA_POINTS.items():
            n = section.get(grade, 0)
            points += n * value
            students += n
    return round(points / students, 3) if students else None


def review_hash(slug: str, review: dict) -> str:
    key = "\x1f".join([slug, review.get("created") or "", review["review"]])
    return hashlib.sha256(key.encode()).hexdigest()


def upsert_professor(conn: psycopg.Connection, prof: dict) -> None:
    conn.execute(
        """
        INSERT INTO professors (slug, name, type, courses, average_rating)
        VALUES (%(slug)s, %(name)s, %(type)s, %(courses)s, %(average_rating)s)
        ON CONFLICT (slug) DO UPDATE SET
            name = EXCLUDED.name,
            type = EXCLUDED.type,
            courses = EXCLUDED.courses,
            average_rating = EXCLUDED.average_rating,
            updated_at = now()
        """,
        {**prof, "courses": sorted(set(prof.get("courses") or []))},
    )


def insert_reviews(conn: psycopg.Connection, slug: str, reviews: list[dict]) -> int:
    rows = [
        {
            "slug": slug,
            "course": r.get("course"),
            "body": r["review"],
            "rating": r.get("rating"),
            "expected_grade": r.get("expected_grade") or None,
            "created_at": r.get("created"),
            "hash": review_hash(slug, r),
        }
        for r in reviews
        if r.get("review", "").strip()
    ]
    if not rows:
        return 0
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO reviews
                (professor_slug, course, body, rating, expected_grade, created_at, content_hash)
            VALUES
                (%(slug)s, %(course)s, %(body)s, %(rating)s, %(expected_grade)s, %(created_at)s, %(hash)s)
            ON CONFLICT (content_hash) DO NOTHING
            """,
            rows,
        )
        return cur.rowcount


def set_gpa(conn: psycopg.Connection, slug: str, gpa: float | None) -> None:
    conn.execute("UPDATE professors SET average_gpa = %s WHERE slug = %s", (gpa, slug))


def main() -> None:
    parser = argparse.ArgumentParser(description="Load PlanetTerp professors and reviews.")
    parser.add_argument("--refresh", action="store_true", help="ignore the response cache")
    parser.add_argument("--grades", action="store_true", help="also fetch grades (one request per professor)")
    parser.add_argument("--max-pages", type=int, help="stop after N pages of 100 professors")
    args = parser.parse_args()

    client = PlanetTerp(refresh=args.refresh)
    profs = new_reviews = 0
    with db.connect() as conn:
        for prof in client.professors(max_pages=args.max_pages):
            upsert_professor(conn, prof)
            new_reviews += insert_reviews(conn, prof["slug"], prof.get("reviews") or [])
            if args.grades:
                set_gpa(conn, prof["slug"], average_gpa(client.grades(prof["name"])))
            conn.commit()
            profs += 1
    print(f"professors: {profs}, new reviews: {new_reviews}")


if __name__ == "__main__":
    main()
