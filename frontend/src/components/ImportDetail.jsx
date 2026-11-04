import DataTable from './DataTable';
import StatusBadge from './StatusBadge';
export default function ImportDetail({ modal, confirmImport }) {
  const job = modal.item;
  return (
    <>
      <p>
        <b>{job.filename}</b> · <StatusBadge status={job.status} />
      </p>
      <p>
        Tổng: {job.total_rows} · Mới: {job.new_rows} · Trùng: {job.duplicated_rows} ·
        Không đổi: {job.unchanged_rows} · Bị loại: {job.rejected_rows} · Đã nhập:{' '}
        {job.inserted_rows}
      </p>
      {job.error_message && (
        <p className="form-error" role="alert">
          {job.error_message}
        </p>
      )}
      {job.status === 'ready' && (
        <button className="button" onClick={() => confirmImport(job.id)}>
          Xác nhận nhập các dòng mới hợp lệ
        </button>
      )}
      {['processing', 'importing'].includes(job.status) && (
        <p role="status">Đang xử lý, trạng thái sẽ tự cập nhật…</p>
      )}
      <h3>Xem trước dòng mới (tối đa 20)</h3>
      <DataTable
        rows={job.preview_rows || []}
        columns={[
          ['Mã SV', (r) => r.student_id],
          ['Năm học', (r) => r.academic_year],
          ['Kỳ', (r) => r.semester],
          ['GPA kỳ', (r) => r.semester_gpa],
          ['GPA tích lũy', (r) => r.cumulative_gpa],
        ]}
      />
      <h3>Dòng bị loại</h3>
      <DataTable
        rows={modal.issues || []}
        columns={[
          ['Dòng', (r) => r.row_number],
          ['Lý do', (r) => r.reason],
          ['Giá trị', (r) => JSON.stringify(r.values)],
        ]}
      />
    </>
  );
}
