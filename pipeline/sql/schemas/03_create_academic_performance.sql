CREATE TABLE IF NOT EXISTS academic_performance (
    student_id          TEXT NOT NULL REFERENCES students(student_id),
    academic_year       TEXT NOT NULL CHECK (academic_year ~ '^[0-9]{4}-[0-9]{4}$'),
    semester            SMALLINT NOT NULL CHECK (semester IN (1,2)),
    registered_credits  SMALLINT NOT NULL CHECK (registered_credits >= 0),
    passed_credits      SMALLINT NOT NULL CHECK (passed_credits >= 0),
    failed_credits      SMALLINT NOT NULL CHECK (failed_credits >= 0),
    semester_gpa        NUMERIC(3,2) NOT NULL CHECK (semester_gpa BETWEEN 0 AND 4),
    cumulative_gpa      NUMERIC(3,2) NOT NULL CHECK (cumulative_gpa BETWEEN 0 AND 4),
    PRIMARY KEY (student_id, academic_year, semester),
    CHECK (passed_credits + failed_credits <= registered_credits)
);