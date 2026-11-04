export default function MetricForm({
  modal,
  showNotification,
  setDatabase,
  setModal,
  handleSaveMetric,
}) {
  return (
    <form onSubmit={handleSaveMetric}>
      <label>
        Mã công thức *
        <input
          name="code"
          required
          pattern="[A-Za-z0-9_]+"
          defaultValue={modal.item?.code}
          readOnly={!!modal.item}
        />
      </label>
      <label>
        Tên hiển thị *<input name="name" required defaultValue={modal.item?.name} />
      </label>
      <label>
        Loại công thức
        <select
          disabled={!!modal.item}
          name="type"
          defaultValue={modal.item?.type || 'cumulative_gpa'}
        >
          <option value="cumulative_gpa">GPA tích lũy thấp</option>
          <option value="failed_credit_ratio">Tỷ lệ tín chỉ rớt</option>
        </select>
      </label>
      <label>
        Điều kiện cảnh báo
        <select name="operator" defaultValue={modal.item?.operator || '<'}>
          {['<', '<=', '>', '>=', '=='].map((operator) => (
            <option key={operator}>{operator}</option>
          ))}
        </select>
      </label>
      <div className="form-grid">
        <label>
          Ngưỡng *
          <input
            name="threshold"
            type="number"
            min="0"
            step="0.01"
            required
            defaultValue={modal.item?.threshold ?? 2}
          />
        </label>
        <label>
          Số học kỳ (tỷ lệ rớt)
          <input
            name="terms"
            type="number"
            min="1"
            step="1"
            required
            defaultValue={modal.item?.terms ?? 1}
          />
        </label>
      </div>
      <label>
        Mục đích sử dụng *
        <textarea name="purpose" required defaultValue={modal.item?.purpose} />
      </label>
      <button className="button">Lưu bản nháp</button>
    </form>
  );
}
