"""Load gen-ed course designations from umd.io."""

from collections.abc import Iterable, Iterator
from typing import Literal, get_args

import httpx
import psycopg

import db

BASE_URL = "https://api.umd.io/v1"
PAGE_SIZE = 100  # API maximum

GenEd = Literal[
    "FSAW", "FSAR", "FSMA", "FSOC", "FSPW",
    "DSHS", "DSHU", "DSNS", "DSNL", "DSSP",
    "SCIS", "DVCC", "DVUP",
]
GEN_EDS: tuple[str, ...] = get_args(GenEd)


def recent_semesters(semesters: list[int], n: int = 2) -> list[str]:
    """The last n fall and spring terms, oldest first. Winter and summer list few courses."""
    regular = [str(s) for s in semesters if str(s).endswith(("01", "08"))]
    return sorted(regular)[-n:]


def courses(http: httpx.Client, semester: str, gen_ed: str) -> Iterator[dict]:
    # Filtering by gen-ed server side: the unfiltered listing is ~50 slow pages per semester.
    page = 1
    while True:
        resp = http.get("/courses", params={
            "semester": semester, "gen_ed": gen_ed, "per_page": PAGE_SIZE, "page": page,
        })
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            return
        yield from batch
        page += 1


def gen_ed_codes(gen_ed: list[list[str]]) -> list[str]:
    # umd.io nests designations, e.g. AMST290 is [["DSHS"], ["DSHU", "DVUP", "SCIS"]].
    # Flattened so a filter on any of those codes finds the course. Labs can read
    # "DSNL|AOSC201" (DSNL when taken with AOSC201), so only the code before "|" is kept.
    return sorted({code.split("|")[0] for option in gen_ed for code in option})


def gen_ed_courses(http: httpx.Client, semesters: list[str]) -> list[dict]:
    """Courses with at least one gen-ed code. A later semester's listing wins."""
    found: dict[str, dict] = {}
    for semester in semesters:
        for code in GEN_EDS:
            for course in courses(http, semester, code):
                found[course["course_id"]] = {
                    "course_id": course["course_id"],
                    "name": course["name"],
                    "gen_eds": gen_ed_codes(course["gen_ed"]),
                }
    return sorted(found.values(), key=lambda c: c["course_id"])


def replace_gen_ed_courses(conn: psycopg.Connection, rows: Iterable[dict]) -> None:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM gen_ed_courses")
        cur.executemany(
            "INSERT INTO gen_ed_courses (course_id, name, gen_eds)"
            " VALUES (%(course_id)s, %(name)s, %(gen_eds)s)",
            list(rows),
        )


def main() -> None:
    # Some filtered pages take over 15 s to come back.
    with httpx.Client(base_url=BASE_URL, timeout=120) as http:
        resp = http.get("/courses/semesters")
        resp.raise_for_status()
        semesters = recent_semesters(resp.json())
        rows = gen_ed_courses(http, semesters)
    with db.connect() as conn:
        replace_gen_ed_courses(conn, rows)
        conn.commit()
    print(f"gen-ed courses: {len(rows)} from semesters {', '.join(semesters)}")


if __name__ == "__main__":
    main()
