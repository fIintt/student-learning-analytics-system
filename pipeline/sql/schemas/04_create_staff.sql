CREATE TABLE IF NOT EXISTS staff (
    staff_id    TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    email       TEXT NOT NULL UNIQUE,
    department  TEXT NOT NULL,
    type  TEXT NOT NULL CHECK (type IN ('lecturer', 'administrator'))
);