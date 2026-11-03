CREATE TABLE IF NOT EXISTS accounts (
    account_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username       TEXT NOT NULL UNIQUE,
    password_hash  TEXT NOT NULL,
    role           TEXT NOT NULL CHECK (role IN ('reviewer', 'viewer', 'admin')),
    student_id     TEXT UNIQUE REFERENCES students(student_id),
    staff_id       TEXT UNIQUE REFERENCES staff(staff_id),
    CHECK (
        (role = 'viewer' AND student_id IS NOT NULL AND staff_id IS NULL)
     OR (role IN ('reviewer', 'admin') AND staff_id IS NOT NULL AND student_id IS NULL)
    )
);