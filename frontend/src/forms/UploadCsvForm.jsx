export default function UploadCsvForm({ handleUploadCsv }) {
  return (
    <form onSubmit={handleUploadCsv}>
      <p>
        Nhập kết quả học kỳ cho sinh viên đã có trong hệ thống. Dòng trùng mã sinh viên,
        năm học và học kỳ có thể cập nhật điểm, tín chỉ cũ sau khi bạn xác nhận.
      </p>
      <details className="reference-details">
        <summary>Cấu trúc CSV</summary>
        <p>
          student_id, academic_year, semester, registered_credits, passed_credits,
          failed_credits, semester_gpa, cumulative_gpa
        </p>
        <p>UTF-8, dấu phẩy; tối đa 10 MiB theo cấu hình mặc định. Học kỳ 1 hoặc 2.</p>
      </details>
      <label>
        File CSV
        <input type="file" name="file" accept=".csv,text/csv" required />
      </label>
      <button className="button">Tải lên để xem trước</button>
    </form>
  );
}
