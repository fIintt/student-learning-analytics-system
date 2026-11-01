CREATE TABLE IF NOT EXISTS students (
    student_id       TEXT PRIMARY KEY CHECK (student_id ~ '^11[0-9]{6}$'),
    name             TEXT NOT NULL,
    program_id       TEXT NOT NULL REFERENCES programs(program_id),
    cohort           SMALLINT NOT NULL,
    academic_status  TEXT NOT NULL
        CHECK (academic_status IN ('studying','graduated','suspended'))
);