export default function CalculateMetricsForm({ handleCalculateMetrics, database }) {
  return (
    <form onSubmit={handleCalculateMetrics}>
      <label>
        Công thức đã duyệt
        <select name="metric" required>
          {database.metrics
            .filter((metric) => metric.status === 'approved')
            .map((metric) => (
              <option key={metric.id} value={metric.id}>
                {metric.name} · v{metric.version}
              </option>
            ))}
        </select>
      </label>
      <p className="notice">
        Tính trên dữ liệu hiện có của toàn hệ thống, kể cả khi giáo viên chỉ được xem một
        số nhóm. Không chọn batch.
      </p>
      <button className="button">Tính và tạo cảnh báo chờ rà soát</button>
    </form>
  );
}
