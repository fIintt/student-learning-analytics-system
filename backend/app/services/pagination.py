from dataclasses import dataclass

from fastapi import Query
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session


@dataclass
class PageParams:
    page: int
    size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


def page_params(page: int = Query(1, ge=1), size: int = Query(50, ge=1, le=200)) -> PageParams:
    return PageParams(page=page, size=size)


def paginate(db: Session, stmt: Select, params: PageParams) -> tuple[list, int]:
    """Trả (danh sách bản ghi của trang, tổng số). stmt phải đã có order_by."""
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    items = db.scalars(stmt.offset(params.offset).limit(params.size)).all()
    return list(items), total
