import httpx

from ingest.umdio import (
    GEN_EDS,
    gen_ed_codes,
    gen_ed_courses,
    recent_semesters,
    replace_gen_ed_courses,
)


def test_recent_semesters_skips_winter_and_summer():
    semesters = [202512, 202601, 202605, 202608, 202612, 202701]
    assert recent_semesters(semesters) == ["202608", "202701"]


def test_gen_ed_codes_flattens_alternatives():
    assert gen_ed_codes([["DSHS"], ["DSHU", "DVUP", "SCIS"]]) == ["DSHS", "DSHU", "DVUP", "SCIS"]
    assert gen_ed_codes([]) == []
    assert gen_ed_codes([["DSNL|AOSC201", "DSNS"]]) == ["DSNL", "DSNS"]


def test_gen_ed_courses_pages_dedupes_and_prefers_later_semester():
    requests = []

    def handler(request):
        p = request.url.params
        requests.append((p["semester"], p["gen_ed"], p["page"]))
        if p["gen_ed"] not in {"DSHS", "DVUP"} or p["page"] != "1":
            return httpx.Response(200, json=[])
        course = {"course_id": "AAAS100", "name": f"Intro {p['semester']}",
                  "gen_ed": [["DSHS", "DVUP"]]}
        return httpx.Response(200, json=[course])

    http = httpx.Client(base_url="https://umd.test", transport=httpx.MockTransport(handler))
    rows = gen_ed_courses(http, ["202608", "202701"])

    assert rows == [{"course_id": "AAAS100", "name": "Intro 202701", "gen_eds": ["DSHS", "DVUP"]}]
    assert ("202701", "DSHS", "2") in requests
    # Each code needs one page, plus a second page for the two codes that returned a course.
    assert len(requests) == 2 * (len(GEN_EDS) + 2)


def test_replace_gen_ed_courses_drops_stale_rows(conn):
    replace_gen_ed_courses(conn, [{"course_id": "OLD100", "name": "Old", "gen_eds": ["DSHS"]}])
    replace_gen_ed_courses(conn, [{"course_id": "NEW100", "name": "New", "gen_eds": ["DSHU"]}])
    rows = conn.execute("SELECT course_id, gen_eds FROM gen_ed_courses").fetchall()
    assert rows == [{"course_id": "NEW100", "gen_eds": ["DSHU"]}]
