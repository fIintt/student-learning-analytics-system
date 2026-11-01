CREATE TABLE IF NOT EXISTS programs (
    program_id         TEXT PRIMARY KEY,
    program_name_vi    TEXT NOT NULL,
    program_name_en    TEXT NOT NULL,
    major_code         TEXT NOT NULL,
    program_type       TEXT NOT NULL
        CHECK (program_type IN ('Standard','Advanced (EP)','POHE','CLC','TT')),
    first_cohort_year  SMALLINT NOT NULL,
    last_cohort_year   SMALLINT NOT NULL,
    CHECK (last_cohort_year >= first_cohort_year)
);