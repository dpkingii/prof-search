CREATE TABLE gen_ed_courses (
    course_id text PRIMARY KEY,
    name      text NOT NULL,
    gen_eds   text[] NOT NULL
);

CREATE INDEX reviews_course_idx ON reviews (course);
