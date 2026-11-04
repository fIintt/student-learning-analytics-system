from app.schemas.common import ORMModel, UtcDatetime


class AcademicImportOut(ORMModel):
    id: int
    uploaded_by: int
    confirmed_by: int | None
    filename: str
    status: str
    total_rows: int
    duplicated_rows: int
    new_rows: int
    updated_rows: int
    unchanged_rows: int
    rejected_rows: int
    inserted_rows: int
    error_message: str | None
    created_at: UtcDatetime
    updated_at: UtcDatetime


class AcademicImportDetail(AcademicImportOut):
    preview_rows: list[dict]


class AcademicImportErrorOut(ORMModel):
    id: int
    row_number: int
    reason: str
    values: dict
