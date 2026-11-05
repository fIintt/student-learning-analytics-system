import { Check } from 'lucide-react';
import { formatNumber } from '../utils/format';
export default function ReviewAlertForm({
  handleReviewAlert,
  findStudent,
  modal,
  findMetric,
  setModal,
  session,
}) {
  return (
    <form onSubmit={handleReviewAlert}>
      <div className="review-summary">
        <strong>{findStudent(modal.item.student)?.name}</strong>
        <p>
          {findMetric(modal.item.metric)?.name}: <b>{formatNumber(modal.item.value)}</b> ·
          v{modal.item.version} · {modal.item.term}
        </p>
        <p>
          Điều kiện cảnh báo: {modal.item.operator} {modal.item.threshold}
        </p>
      </div>
      <label>
        Kết quả rà soát
        <select
          value={modal.action}
          onChange={(event) =>
            setModal({
              ...modal,
              action: event.target.value,
            })
          }
        >
          <option value="confirm">Xác nhận cần hỗ trợ</option>
          <option value="dismiss">Bác cảnh báo</option>
        </select>
      </label>
      <label>
        Ghi chú rà soát *
        <textarea
          name="note"
          required
          placeholder="Bối cảnh và nhận xét của giáo viên…"
        />
      </label>
      {modal.action === 'confirm' && (
        <>
          <label>
            Lý do cần hỗ trợ *<textarea name="reason" required />
          </label>
          <label>
            Người phụ trách
            <select name="owner">
              <option value="">Chưa phân công</option>
              {(modal.assignees || []).map((user) => (
                <option key={user.id} value={user.id}>
                  {user.full_name} · {user.username || user.email}
                </option>
              ))}
            </select>
          </label>
        </>
      )}
      <button className="button" type="submit">
        <Check size={16} />
        {modal.action === 'confirm' ? 'Xác nhận và mở hỗ trợ' : 'Bác cảnh báo'}
      </button>
    </form>
  );
}
