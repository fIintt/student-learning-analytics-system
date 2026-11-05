# M11 Frontend

Frontend React 19 + Vite 6, giao diện tiếng Việt cho hệ thống phân tích kết quả học tập và hỗ trợ sinh viên. Tài liệu này dành cho người chạy frontend và các thành viên backend/pipeline khi tích hợp.

Hợp đồng API đang đối chiếu: `BACKEND_HANDOVER_FOR_FE.md`, cập nhật 04/11/2026. Tài liệu handover do nhóm backend cung cấp riêng, không được đóng gói trong thư mục này. README ghi lại cách frontend đang sử dụng API; không thay thế đặc tả nghiệp vụ.

## Chạy frontend

Cần Node.js 22 hoặc 24 LTS và npm đi kèm (môi trường kiểm tra hiện tại: Node.js 24, npm 11) và backend/database được bên phụ trách khởi động riêng.

Tại thư mục chứa `package.json` của frontend:

```powershell
npm ci
Copy-Item .env.example .env.local
npm run dev
```

Chỉ sao chép `.env.example` khi chưa có `.env.local`; tránh ghi đè cấu hình đang dùng. Mở URL Vite in trong terminal, thường là `http://127.0.0.1:5173`. Dừng bằng `Ctrl + C`.

Nội dung cấu hình mẫu:

```dotenv
VITE_API_URL=http://127.0.0.1:8000/api/v1
```

URL phải bao gồm `/api/v1`. Sau khi đổi biến môi trường cần khởi động lại Vite. Biến bắt đầu bằng `VITE_` được đưa vào ứng dụng trên trình duyệt: không đặt mật khẩu database, JWT secret hoặc bí mật khác ở đây.

Frontend không kết nối trực tiếp PostgreSQL, không chạy Docker, pipeline, migration hay seed dữ liệu. Để kiểm thử đầy đủ cần cả ba phần: database, backend API và frontend. Chỉ chạy database Docker và `npm run dev` là chưa đủ.

## Dependencies và yêu cầu tích hợp

Frontend dùng `package.json` và `package-lock.json` thay cho `requirements.txt` của Python. Commit cả hai file, dùng `npm ci` để cài đúng lockfile. Không cần cài Python hay PostgreSQL trong thư mục frontend.

- Thư viện chạy: React, React DOM, Lucide React. Công cụ build/style: Vite, plugin React, Tailwind CSS.
- Backend cần cung cấp base URL truy cập được, tài khoản kiểm thử hợp lệ cho từng vai trò và CORS cho origin frontend thực tế. JWT secret và thông tin database chỉ thuộc backend.
- Các ID sinh viên phải nhất quán giữa danh mục, cảnh báo, kết quả và hồ sơ hỗ trợ. Các trạng thái frontend dùng gồm `studying`, `graduated`, `suspended`; `pending_review`, `confirmed`, `dismissed`; `open`, `in_progress`, `closed`.
- Pipeline phụ trách dữ liệu nguồn và worker theo hợp đồng backend. Khi thay đổi schema CSV, response API, enum hoặc quy tắc tính, cần báo frontend và cập nhật handover trước khi tích hợp.
- Không chạy seed/reset database chỉ để làm frontend hoạt động. Tài khoản và dữ liệu kiểm thử do bên vận hành backend/database cấp.

## Lệnh kiểm tra

| Lệnh              | Mục đích                                       |
| ----------------- | ---------------------------------------------- |
| `npm run dev`     | Chạy giao diện khi phát triển                  |
| `npm run build`   | Build vào `dist/`, kiểm tra khả năng biên dịch |
| `npm run preview` | Xem bản build local, vẫn cần API riêng         |

Build/test frontend thành công không chứng minh toàn bộ nghiệp vụ backend đã chạy đúng. Khi triển khai, cấu hình API trước khi build và cấu hình backend cho phép origin thực tế của frontend qua CORS. Không dùng `vite preview` làm dịch vụ production.

## Đăng nhập và phân quyền

Đăng nhập bằng **username và password** của tài khoản có thật trong backend. Không có bộ tài khoản thử bắt buộc hoặc mật khẩu hardcode trong frontend.

- `admin`: quản trị, duyệt/từ chối công thức, quản lý tài khoản sinh viên, đồng bộ tài khoản nguồn và gán nhóm giáo viên.
- `reviewer`: xem/xử lý dữ liệu trong các nhóm được backend cấp. Riêng API tính chỉ số hiện chạy toàn hệ thống.
- `viewer`: cổng cá nhân `/me/...`, chỉ dữ liệu sinh viên liên kết với tài khoản.
- `must_change_password`: buộc đổi mật khẩu rồi đăng nhập lại.

Một nhóm được backend định nghĩa bằng **chương trình × khóa** (`program_id` + `cohort`). Gán nhóm giáo viên là thay đổi phạm vi quyền, không chuyển sinh viên sang lớp khác. Backend phải thực thi phân quyền; ẩn nút trên frontend không thay thế kiểm tra quyền API.

Ứng dụng yêu cầu đăng nhập qua API backend ở cả chế độ phát triển và bản build. Không còn chế độ bỏ qua đăng nhập. Tài khoản/dữ liệu kiểm thử local không được đóng gói cùng frontend.

Frontend lưu token và thông tin phiên ở khóa localStorage `m11-api-session`; sinh viên, điểm, cảnh báo và hồ sơ nghiệp vụ được lấy qua API, không lưu thành database trong localStorage.

## Các luồng API đang sử dụng

Các đường dẫn dưới đây tính từ `VITE_API_URL`. Đây là nhóm API chính, không phải danh sách đầy đủ mọi request.

| Luồng               | Endpoint / hành vi frontend                                                             |
| ------------------- | --------------------------------------------------------------------------------------- |
| Phiên đăng nhập     | `/auth/login`, `/auth/me`, `/auth/change-password`                                      |
| Danh mục            | `/learners`, `/programs`, `/groups`                                                     |
| Công thức           | `/metric-definitions`, sửa nháp, `/new-version`, `/submit`, `/approve`, `/reject`       |
| Tính chỉ số         | `POST /metrics/compute`, body chỉ có `metric_definition_id`                             |
| Kết quả             | `/metrics/results`, `/reports/learner/{id}`                                             |
| Rà soát             | `/review/alerts`, chi tiết, `/confirm`, `/dismiss`                                      |
| Hỗ trợ              | `/support-cases`, `/support-cases/assignees`, `/followups`                              |
| Tài khoản sinh viên | `/admin/student-accounts`, khóa/mở, reset mật khẩu; `/auth/users/{id}/student-link`     |
| Đồng bộ tài khoản   | `POST /admin/accounts/sync`; phải đọc cả created/skipped/conflicts                      |
| Nhóm giáo viên      | `GET /admin/teacher-accounts`, `PUT /admin/teacher-accounts/{id}/groups`                |
| Nhập CSV            | `/academic-imports/template`, upload, lịch sử, chi tiết, errors và confirm              |
| Cổng sinh viên      | `/me/student-profile`, `/me/academic-performance`, `/me/academic-summary`, `/me/alerts` |

Request có xác thực dùng `Authorization: Bearer ...`. Các API danh sách cần trả `{ items, total, page, size }`; frontend tải đủ trang với `size=200`, loại bản ghi trùng ID rồi mới lọc/thống kê. Cách này phù hợp bộ dữ liệu hiện tại; khi dữ liệu lớn cần thống nhất chuyển lọc/phân trang sang server.

Các bộ dữ liệu được tải độc lập. Một API lỗi không làm mất dữ liệu các API khác; ô thống kê thiếu nguồn tương ứng hiện `—`. API trả 401 làm mất phiên đăng nhập. Các request nhiều endpoint chưa có snapshot chung, nên dữ liệu có thể lệch thời điểm; dùng nút **Tải lại dữ liệu** để cập nhật. Sau thao tác ghi thành công qua hook chung, frontend tải lại dữ liệu.

## Quy tắc frontend cần backend/pipeline giữ nhất quán

### Chỉ số và cảnh báo

Backend tính chỉ số và sinh cảnh báo; frontend chỉ cấu hình/gọi API/hiển thị:

- GPA: `cumulative_gpa` ở học kỳ gần nhất, không tự suy ra từ điểm từng môn trên frontend.
- Tỷ lệ rớt: tổng `failed_credits` chia tổng `registered_credits` trong N học kỳ gần nhất. Ngưỡng `0.25` là 25%, không phải `25`.
- Chỉ công thức đã duyệt mới được tính; backend hiện chỉ tính cho sinh viên có trạng thái `studying` và có dữ liệu học tập.
- Mỗi lần tính chọn một công thức. Bộ lọc nhóm/chương trình trên giao diện không được gửi làm phạm vi tính.
- Frontend gom các phiên bản cùng mã thành một ô; bản đang sửa hiển thị cùng ô, phiên bản cũ thu trong lịch sử. Việc gom không thay đổi vòng đời phiên bản hoặc dữ liệu backend.
- Công thức bị từ chối phải sửa và lưu lại thành nháp trước khi gửi duyệt.
- Duyệt công thức không tự tính lại kết quả: cần thao tác **Tính chỉ số** riêng.

Dashboard chỉ thống kê sinh viên `studying`, sau bộ lọc chương trình, nhóm và tên/mã. Cả bốn ô, biểu đồ trạng thái và bảng trên dashboard cùng dùng phạm vi này:

| Ô                      | Đơn vị đếm                            |
| ---------------------- | ------------------------------------- |
| Sinh viên đang học     | Sinh viên                             |
| Cảnh báo chờ rà soát   | Cảnh báo `pending_review`             |
| Hồ sơ hỗ trợ chưa đóng | Hồ sơ có trạng thái khác `closed`     |
| Sinh viên chờ rà soát  | Mã sinh viên duy nhất có cảnh báo chờ |

Một người có thể có nhiều cảnh báo/hồ sơ. Các ô không phải những nhóm loại trừ nhau. Bộ lọc riêng trong biểu đồ không thay đổi bốn ô. Trang Sinh viên vẫn giữ đầy đủ trạng thái; trang Hàng chờ không tự áp dụng điều kiện `studying` của dashboard.

### Rà soát và hỗ trợ

Xác nhận cảnh báo đồng thời mở hồ sơ hỗ trợ theo backend. ID người phụ trách lấy từ API assignees, không tự giả định danh sách tài khoản. Hồ sơ đóng không có chức năng mở lại trên frontend hiện tại.

Thêm followup rồi PATCH hồ sơ là hai request riêng. Nếu POST thành công nhưng PATCH lỗi, form giữ ID followup để lần thử tiếp chỉ PATCH. Khi mất phản hồi POST, không tự gửi lại mù quáng; tải lại lịch sử để kiểm tra thao tác đã được ghi chưa.

### Dữ liệu và CSV — dành cho pipeline

- Pipeline/backend phụ trách kiểm tra, làm sạch và nạp dữ liệu. Frontend không trực tiếp đọc file nguồn vào database.
- Luồng nhập web dùng template từ API, upload bằng multipart, xem preview/lỗi rồi confirm. Job `processing`/`importing` được poll mỗi 2 giây. Polling tự thử lại sau lỗi mạng, xóa lỗi khi phục hồi và bỏ qua phản hồi từ phiên cũ. Khi phát hiện nhập hoàn tất, frontend tải lại các bộ dữ liệu; không tự tính chỉ số.
- Nhập CSV trên web dành cho kết quả học kỳ của sinh viên có sẵn; không phải tạo mới chương trình/sinh viên.
- Nhập xong không tự tính chỉ số. Cần gọi tính riêng sau khi backend xác nhận hoàn tất.
- Khi kiểm thử nhập web, luôn tải template từ API. CSV mẫu cũ trong `samples/` và cấu hình editor `.vscode/` chỉ giữ local, đã được loại khỏi Git.
- Xuất CSV trên frontend là xuất từ danh sách đã tải/lọc, không phải API xuất báo cáo của backend. Xuất tại dashboard chỉ gồm người đang học, đếm cảnh báo chờ và hồ sơ chưa đóng. Xuất tại trang Sinh viên giữ các trạng thái sinh viên và đếm tổng cảnh báo/hồ sơ trong danh sách đã lọc.

## Vấn đề còn mở và kiểm thử bàn giao

Trạng thái đối chiếu code ngày 05/11/2026, backend/pipeline trên main tại commit 57e36e2:

1. Khi tính phiên bản công thức mới, backend chưa tự kết thúc cảnh báo chờ của phiên bản cũ cùng mã. Hàng chờ có thể chồng phiên bản; thu hẹp ngưỡng không tự loại cảnh báo cũ. Frontend không tự ẩn hoặc đổi trạng thái để giả lập việc này.
2. Bản main mới đã có worker CSV và hỗ trợ thêm mới/cập nhật điểm, tín chỉ trùng sinh viên–năm học–học kỳ sau xác nhận. Frontend đã cập nhật thông báo, preview và số dòng cập nhật. Chưa kiểm thử end-to-end với bản backend này; môi trường local cũ từng trả 503 không đại diện cho bản main mới.
3. Lần kiểm tra dữ liệu nguồn ban đầu: CSV 204 dòng, database sau pipeline 193 người, file rejected 7 dòng. Chênh lệch 4 dòng còn lại chưa được xác minh; không coi số dòng nguồn là số người hợp lệ trong database.

Trước khi thu gọn bản bàn giao đã chạy 13 kiểm thử frontend; từng kiểm tra một số luồng với backend thật/database local. Chưa xác nhận toàn bộ chức năng end-to-end cho mọi vai trò. Khi bàn giao cần kiểm tra:

- Admin/reviewer/viewer: đăng nhập, đăng xuất, đổi mật khẩu, phạm vi 403 và tài khoản chưa liên kết.
- Công thức: sửa nháp, gửi duyệt, duyệt/từ chối, lịch sử, tính và số cảnh báo.
- Rà soát: confirm/dismiss, thao tác trùng 409, phân công, followup và đóng hồ sơ.
- Tài khoản: tạo, liên kết, khóa/mở, reset, đồng bộ có conflict; gán/gỡ nhóm giáo viên.
- CSV: template, upload, preview/errors, confirm, poll và trạng thái thất bại khi worker đã sẵn sàng.
- Dashboard: cùng bộ lọc, số người khác số cảnh báo/hồ sơ, tải lỗi và tải lại.

## Cấu trúc source

| Đường dẫn                     | Nội dung                                    |
| ----------------------------- | ------------------------------------------- |
| `src/pages/`                  | Màn hình theo chức năng                     |
| `src/components/`             | Bảng, thẻ, biểu đồ và dialog dùng lại       |
| `src/forms/`                  | Form nhập liệu                              |
| `src/hooks/useM11.js`         | State và các thao tác API chung             |
| `src/services/api.js`         | HTTP, Bearer token, lỗi và phân trang       |
| `src/services/backendData.js` | Đổi cấu trúc response sang dữ liệu hiển thị |
| `src/styles/`                 | Theme và CSS theo nhóm giao diện            |
| `src/utils/`                  | Định dạng, dữ liệu biểu đồ, gom phiên bản   |

Bản bàn giao tối giản không kèm kiểm thử tự động, công cụ Prettier hoặc tài liệu học code cá nhân. Các file đó chỉ giữ local và không cần để chạy/build ứng dụng.

## Đưa frontend vào repository chung

Đưa thư mục này vào `frontend/` trên branch frontend đã thống nhất. Giữ `src/`, `public/`, cấu hình build, `package.json`, `package-lock.json`, `.env.example` và tài liệu. Không đưa môi trường backend local hoặc database thử vào commit frontend.

`.gitignore` đã loại dependencies, build, môi trường cá nhân, log, cache, mẫu CSV cũ, kiểm thử local, cấu hình editor/format, tài liệu học code và các file `backup*.zip`. Database trong Docker không tự đi theo Git. Trước khi commit, đọc `git status` và `git diff --cached` để bảo đảm chỉ có file mong muốn. `.gitignore` không tự bỏ theo dõi các file đã được commit trước đó.
