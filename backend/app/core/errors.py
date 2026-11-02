"""Chuẩn hoá mọi lỗi về dạng {"detail": "thông báo tiếng Việt"}."""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

_VALIDATION_MESSAGES = {
    "missing": "thiếu trường bắt buộc",
    "string_too_short": "không được để trống",
    "string_too_long": "quá dài",
    "value_error": "giá trị không hợp lệ",
    "enum": "giá trị không nằm trong danh sách cho phép",
    "literal_error": "giá trị không nằm trong danh sách cho phép",
    "int_parsing": "phải là số nguyên",
    "int_type": "phải là số nguyên",
    "float_parsing": "phải là số",
    "float_type": "phải là số",
    "bool_parsing": "phải là true/false",
    "greater_than": "phải lớn hơn giá trị cho phép",
    "greater_than_equal": "nhỏ hơn giá trị cho phép",
    "less_than_equal": "lớn hơn giá trị cho phép",
    "json_invalid": "JSON không hợp lệ",
    "dict_type": "phải là đối tượng JSON",
    "list_type": "phải là danh sách",
    "string_type": "phải là chuỗi",
}

_HTTP_DEFAULTS = {
    400: "Yêu cầu không hợp lệ",
    401: "Chưa đăng nhập hoặc phiên đăng nhập không hợp lệ",
    403: "Không có quyền thực hiện thao tác này",
    404: "Không tìm thấy tài nguyên",
    405: "Phương thức không được hỗ trợ",
    409: "Xung đột trạng thái dữ liệu",
}


def _format_validation_error(exc: RequestValidationError) -> str:
    first = exc.errors()[0]
    loc = [str(p) for p in first.get("loc", ()) if p not in ("body", "query", "path", "form")]
    field = ".".join(loc) or "dữ liệu"
    err_type = first.get("type", "")
    if err_type == "value_error":
        # Lỗi do validator tự viết: thông điệp đã là tiếng Việt.
        msg = str(first.get("ctx", {}).get("error", "")) or _VALIDATION_MESSAGES["value_error"]
    else:
        msg = _VALIDATION_MESSAGES.get(err_type, "giá trị không hợp lệ")
    return f"Dữ liệu không hợp lệ ở trường '{field}': {msg}"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def _validation_handler(_request: Request, exc: RequestValidationError):
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"detail": _format_validation_error(exc)})

    @app.exception_handler(StarletteHTTPException)
    async def _http_handler(_request: Request, exc: StarletteHTTPException):
        detail = exc.detail
        if not isinstance(detail, str) or detail in ("Not Found", "Method Not Allowed", "Unauthorized",
                                                    "Forbidden", "Not authenticated"):
            detail = _HTTP_DEFAULTS.get(exc.status_code, "Có lỗi xảy ra")
        return JSONResponse(status_code=exc.status_code, content={"detail": detail},
                            headers=getattr(exc, "headers", None))
