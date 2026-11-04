import StatusBadge from '../components/StatusBadge';
import { formatNumber } from '../utils/format';
export default function SupportCaseContent({
  findStudent,
  modal,
  canEdit,
  handleSaveFollowup,
  database,
  findMetric,
}) {
  return (
    <>
      <div className="review-summary">
        <strong>{findStudent(modal.item.student)?.name}</strong>
        <p>{modal.item.reason}</p>
        <StatusBadge status={modal.item.status} />
      </div>
      <div className="timeline">
        {modal.item.followups.map((formData, index) => (
          <div key={index}>
            <small>{new Date(formData.date).toLocaleString('vi-VN')}</small>
            <strong>{formData.action}</strong>
            <p>
              {formData.result || 'Chưa ghi nhận kết quả'} ·{' '}
              {
                {
                  unknown: 'Chưa rõ',
                  improved: 'Cải thiện',
                  no_change: 'Không đổi',
                  worsened: 'Xấu đi',
                }[formData.assessment]
              }
            </p>
            {formData.measurement && (
              <small>
                Kết quả đo lại:{' '}
                {formData.post_metric_result
                  ? `${formData.post_metric_result.metric_code}: ${formatNumber(formData.post_metric_result.value)}`
                  : `#${formData.measurement}`}
              </small>
            )}
          </div>
        ))}
      </div>
      {canEdit && modal.item.status !== 'closed' ? (
        <form onSubmit={handleSaveFollowup}>
          {modal.savedFollowupId && (
            <p role="status">
              Đã lưu lần theo dõi #{modal.savedFollowupId}. Lần gửi tiếp chỉ cập nhật hồ
              sơ.
            </p>
          )}
          <fieldset disabled={!!modal.savedFollowupId || modal.uncertain}>
            <label>
              Hành động hỗ trợ *<textarea name="action" required />
            </label>
            <label>
              Kết quả
              <textarea name="result" />
            </label>
            <label>
              Đánh giá
              <select name="assessment">
                <option value="unknown">Chưa rõ</option>
                <option value="improved">Cải thiện</option>
                <option value="no_change">Không thay đổi</option>
                <option value="worsened">Xấu đi</option>
              </select>
            </label>
            <label>
              Gắn kết quả đo lại
              <select name="measurement">
                <option value="">Không gắn</option>
                {database.results
                  .filter((row) => row.student === modal.item.student)
                  .map((row) => (
                    <option key={row.id} value={row.id}>
                      {findMetric(row.metric)?.name} · {formatNumber(row.value)} ·{' '}
                      {row.term}
                    </option>
                  ))}
              </select>
            </label>
          </fieldset>
          <label>
            Trạng thái
            <select name="status" defaultValue={modal.item.status}>
              {modal.item.status === 'open' && <option value="open">Mở</option>}
              <option value="in_progress">Đang xử lý</option>
              <option value="closed">Đóng</option>
            </select>
          </label>
          <label>
            Người phụ trách
            <select name="owner" defaultValue={modal.item.assigned_to ?? ''}>
              <option value="">Chưa phân công</option>
              {modal.item.assigned_to != null &&
                !(modal.assignees || []).some(
                  (user) => user.id === modal.item.assigned_to,
                ) && (
                  <option value={modal.item.assigned_to}>
                    Tài khoản #{modal.item.assigned_to} (không còn trong danh sách phân
                    công)
                  </option>
                )}
              {(modal.assignees || []).map((user) => (
                <option key={user.id} value={user.id}>
                  {user.full_name} · {user.username || user.email}
                </option>
              ))}
            </select>
          </label>
          <button className="button" disabled={modal.uncertain}>
            {modal.savedFollowupId ? 'Cập nhật hồ sơ' : 'Lưu theo dõi'}
          </button>
        </form>
      ) : (
        <p className="muted">
          {modal.item.status === 'closed'
            ? 'Trường hợp đã đóng.'
            : 'Bạn có quyền xem thông tin.'}
        </p>
      )}
    </>
  );
}
