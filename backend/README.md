# Backend — Phân tích học tập sinh viên

BE FastAPI dùng PostgreSQL, chạy Python 3.14. Source ứng dụng nằm trong `app/`; pipeline nằm ở `../pipeline/` và dùng môi trường Python riêng.

## Chức năng và quyền

| Role API | Đối tượng | Phạm vi                                                                                                     |
| -------- | --------- | ----------------------------------------------------------------------------------------------------------- |
| admin    | Admin     | Toàn bộ dữ liệu; quản trị tài khoản sinh viên, đồng bộ tài khoản, gán nhóm giáo viên và phê duyệt công thức |
| reviewer | Giáo viên | Sinh viên thuộc nhóm được gán theo chương trình và khoá; thao tác theo quyền từng API                       |
| viewer   | Sinh viên | Chỉ dữ liệu của mã sinh viên liên kết với tài khoản                                                         |

Đã có đăng nhập username/JWT, đổi mật khẩu, danh mục chương trình/nhóm/sinh viên, công thức và duyệt công thức, tính chỉ số, rà soát cảnh báo, hồ sơ hỗ trợ, phân công, theo dõi và báo cáo JSON.

Cổng sinh viên cung cấp hồ sơ cá nhân, kết quả học kỳ, tổng hợp học tập và cảnh báo. Dữ liệu học tập gồm GPA học kỳ/tích luỹ và tín chỉ đăng ký/đạt/rớt; GPA đọc từ dữ liệu nhập. Không có bảng điểm từng môn. API báo cáo chưa xuất Excel/PDF/CSV; CSV mẫu nhập là chức năng riêng.

## Cài đặt

Chạy PowerShell trong thư mục `backend`:

```powershell
py -3.14 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --only-binary=:all: -r .\requirements.txt
cd ..\pipeline
uv sync --python 3.14
cd ..\backend
```

Cần PostgreSQL đang chạy và database đã tồn tại. Tạo `.env` tại gốc dự án (ngang hàng với `backend` và `pipeline`), ví dụ:

```dotenv
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=student_learning
DB_USER=postgres
DB_PASSWORD=replace-with-local-password
SECRET_KEY=replace-with-long-random-secret
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

Đây chỉ là giá trị mẫu. Cổng phải khớp PostgreSQL thực tế; BE mặc định 5433 nếu không cấu hình. Pipeline yêu cầu `DB_PASSWORD` không rỗng. Nếu đặt `DATABASE_URL`, BE ưu tiên URL đó; phải bảo đảm vẫn trỏ cùng database với pipeline. Không commit `.env`, file upload hoặc `.venv`.

Tuỳ chọn: `PIPELINE_DIR`, `PIPELINE_PYTHON`, `ACADEMIC_IMPORT_DIR`, `ACADEMIC_IMPORT_MAX_BYTES`, `ACADEMIC_IMPORT_MAX_ROWS`, `ACADEMIC_IMPORT_TIMEOUT_SECONDS`.

Mặc định BE tìm worker tại `../pipeline/src/pipeline/academic_import_worker.py`, dùng Python trong `../pipeline/.venv`; file upload lưu ở `backend/data/academic_imports`.

## Nạp dữ liệu và khởi động

Từ `backend`:

```powershell
cd ..\pipeline
uv run --python 3.14 python src/pipeline/main.py
cd ..\backend
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Pipeline tạo cấu trúc bảng nguồn và nạp lần lượt chương trình, sinh viên, kết quả học tập, nhân sự, tài khoản từ dữ liệu raw. BE yêu cầu có `programs`, `students`, `academic_performance`; sau đó tạo/cập nhật bảng nghiệp vụ riêng và đồng bộ nhóm khi khởi động.

- Base URL: http://127.0.0.1:8000
- Swagger: http://127.0.0.1:8000/docs
- OpenAPI: http://127.0.0.1:8000/openapi.json
- Prefix API: `/api/v1`
- Kiểm tra tiến trình: `GET /api/v1/health/live`
- Kiểm tra sẵn sàng: `GET /api/v1/health/ready`

CORS hiện cho phép mọi origin, method và header, bật credentials; cần cấu hình domain cụ thể khi triển khai.

## Đăng nhập và tài khoản

```http
POST /api/v1/auth/login
Content-Type: application/json

{"username":"your-username","password":"your-password"}
```

Dùng `access_token` trong header `Authorization: Bearer <token>`. Gọi `GET /api/v1/auth/me` để đọc vai trò, nhóm và mã sinh viên liên kết. Token mặc định hết hạn sau 60 phút; nhận 401 thì đăng nhập lại.

`accounts` là bảng nguồn pipeline; `users` là bảng đăng nhập BE. Nạp `accounts.csv` không tự tạo `users`. Admin BE đã đăng nhập gọi `POST /api/v1/admin/accounts/sync` để tạo tài khoản từ `accounts`/`staff`, không ghi đè mật khẩu tài khoản đã có. Cần chuẩn bị admin BE ban đầu trước khi gọi; tài liệu này không cung cấp lệnh bootstrap admin hoặc mật khẩu mặc định.

Nhóm giáo viên lưu trong `user_group_access`, gán qua API, không cần sửa CSV. Sinh viên phải được liên kết với một `student_id` mới xem được dữ liệu cá nhân.

## Luồng nhập CSV kết quả học tập

| Thao tác             | Method và URL (sau `/api/v1`)         |
| -------------------- | ------------------------------------- |
| Tải mẫu              | GET `/academic-imports/template`      |
| Upload               | POST `/academic-imports`              |
| Danh sách lần nhập   | GET `/academic-imports`               |
| Trạng thái/xem trước | GET `/academic-imports/{id}`          |
| Dòng lỗi             | GET `/academic-imports/{id}/errors`   |
| Xác nhận             | POST `/academic-imports/{id}/confirm` |

Upload bằng multipart/form-data, trường `file`. CSV UTF-8, dấu phẩy, đúng tám cột:

```csv
student_id,academic_year,semester,registered_credits,passed_credits,failed_credits,semester_gpa,cumulative_gpa
11224850,2026-2027,1,20,18,2,3.10,2.85
```

Mã sinh viên phải có trong database. Giới hạn mặc định 10 MiB và 50.000 dòng. FE gửi file; BE quản lý đường dẫn lưu nội bộ.

```text
Upload → processing → ready → xác nhận → importing → completed
Lỗi xử lý → failed
```

Upload/xác nhận trả HTTP 202; FE gọi API chi tiết để chờ trạng thái cuối. `ready` chưa ghi điểm. Xem trước hiển thị tối đa 20 dòng mới, các bộ đếm và API lỗi phản ánh toàn bộ file.

BE gọi worker của pipeline bằng subprocess. Worker tái sử dụng hàm chuẩn hoá và kiểm tra dữ liệu pipeline; không gọi hàm CLI ghi ngay tại bước upload, để giữ bước xem trước/xác nhận.

- Khoá dữ liệu: `student_id + academic_year + semester`.
- Bản ghi học kỳ mới hợp lệ: thêm sau xác nhận.
- Bản ghi giống dữ liệu đã có: bỏ qua, không tạo trùng.
- Cùng khoá nhưng GPA/tín chỉ khác: đưa vào nhóm cập nhật và ghi đè các giá trị học kỳ khi xác nhận; dữ liệu trùng hoàn toàn được bỏ qua.
- Giáo viên chỉ nhập trong nhóm được gán; quyền được kiểm tra lại khi xác nhận.
- Có bảo vệ nhập đồng thời; lỗi database làm rollback lần xác nhận.
- Nhập CSV không tự tính chỉ số/cảnh báo; cần gọi API tính chỉ số riêng.

Tác vụ nền hiện chạy trong tiến trình BE, chưa có hàng đợi bền vững. Tác vụ bị gián đoạn được đánh dấu lỗi khi đọc trạng thái quá hạn, cần upload lại.

## Nhóm API

Swagger của bản đang chạy là căn cứ cho method, request, enum, bộ lọc và response chi tiết. Mọi đường dẫn dưới đây có prefix `/api/v1`.

| Chức năng           | Đường dẫn chính                                                                               |
| ------------------- | --------------------------------------------------------------------------------------------- |
| Xác thực            | `/auth/login`, `/auth/me`, `/auth/change-password`                                            |
| Liên kết sinh viên  | `/auth/users/{user_id}/student-link`                                                          |
| Danh mục            | `/programs`, `/groups`, `/learners`                                                           |
| Công thức           | `/metric-definitions` và các thao tác submit/approve/reject                                   |
| Tính/tra cứu chỉ số | `/metrics/compute`, `/metrics/results`                                                        |
| Rà soát cảnh báo    | Nhóm review trong Swagger                                                                     |
| Hồ sơ hỗ trợ        | `/support-cases`, `/support-cases/{id}`                                                       |
| Người nhận hồ sơ    | `/support-cases/assignees`                                                                    |
| Theo dõi            | `/followups`                                                                                  |
| Báo cáo JSON        | `/reports/learner/{learner_id}`, `/reports/group/{group_id}`, `/reports/program/{program_id}` |
| Cổng sinh viên      | `/me/student-profile`, `/me/academic-performance`, `/me/academic-summary`, `/me/alerts`       |
| Tài khoản sinh viên | `/admin/student-accounts`                                                                     |
| Đồng bộ tài khoản   | `/admin/accounts/sync`                                                                        |
| Giáo viên/gán nhóm  | `/admin/teacher-accounts`, `/admin/teacher-accounts/{user_id}/groups`                         |

Quyền được kiểm tra tại BE. Danh sách thường có phân trang; dùng tổng số và lấy đủ trang khi tổng hợp. FE cần xử lý 401 (xác thực), 403 (quyền), 404, 409 (trạng thái/xung đột), 413 (file lớn), 422 (request không hợp lệ), 503 (chưa sẵn sàng). Lỗi thông thường có trường `detail`; đọc schema từng endpoint.

## Kiểm thử

Dùng database PostgreSQL riêng cho test. Fixture tạo schema riêng và xoá schema khi kết thúc.

```powershell
$env:TEST_DATABASE_URL='postgresql+psycopg://test_user:test_password@127.0.0.1:5432/test_database'
& .\.venv\Scripts\python.exe -m pytest app/tests/test_academic_imports.py -q
& .\.venv\Scripts\python.exe -m pip check
```

Test gọi CLI pipeline cũng cần các biến `DB_*` hợp lệ để import module cấu hình.

Ngày 04/11/2026: 13 kiểm thử CSV đã đạt trên Python 3.14.10 và PostgreSQL riêng, bao gồm preview, thêm mới, chống ghi đè/trùng, quyền, nhập đồng thời, giới hạn file, lỗi worker, rollback và SQL schema thực tế của pipeline. Chưa kiểm thử thao tác trên giao diện FE.
