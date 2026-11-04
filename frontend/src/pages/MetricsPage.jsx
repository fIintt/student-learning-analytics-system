import StatusBadge from '../components/StatusBadge';
import groupMetrics from '../utils/groupMetrics';

function MetricValues({ metric }) {
  return (
    <div className="metric-meta">
      <span>
        Ngưỡng cảnh báo{' '}
        <b>
          {metric.operator} {metric.threshold}
        </b>
      </span>
      <span>
        Học kỳ <b>{metric.type === 'cumulative_gpa' ? 'Gần nhất' : metric.terms}</b>
      </span>
    </div>
  );
}

export default function MetricsPage({
  canEdit,
  setModal,
  database,
  changeMetricStatus,
  role,
}) {
  const groups = groupMetrics(database.metrics);

  function renderActions(metric) {
    return (
      <div className="card-actions">
        {canEdit && ['draft', 'rejected'].includes(metric.status) && (
          <>
            <button
              className="button secondary small"
              onClick={() => setModal({ type: 'editMetric', item: metric })}
            >
              Sửa
            </button>
            <button
              className="button small"
              onClick={() => changeMetricStatus(metric, 'submitted')}
            >
              Gửi duyệt
            </button>
          </>
        )}
        {role === 'admin' && metric.status === 'submitted' && (
          <>
            <button
              className="button small"
              onClick={() => changeMetricStatus(metric, 'approved')}
            >
              Duyệt thay đổi
            </button>
            <button
              className="text-button danger-text"
              onClick={() => setModal({ type: 'rejectMetric', item: metric })}
            >
              Từ chối
            </button>
          </>
        )}
      </div>
    );
  }

  return (
    <>
      <div className="metrics-actions">
        {canEdit && (
          <button
            className="button secondary"
            onClick={() => setModal({ type: 'compute' })}
          >
            Tính chỉ số
          </button>
        )}
      </div>
      <div className="metric-grid">
        {groups.map(({ code, approved, working, primary, history }) => (
          <section className="panel metric-card" key={code}>
            <div className="case-top">
              <span className="code">{code}</span>
              <StatusBadge status={primary.status} />
            </div>
            <h2>{primary.name}</h2>
            <p className="metric-version-label">
              {approved ? 'Đang áp dụng' : 'Phiên bản hiện tại'} · v{primary.version}
            </p>
            <div className="formula">
              {primary.type === 'cumulative_gpa'
                ? 'GPA tích lũy gần nhất'
                : 'Σ Tín chỉ rớt / Σ Tín chỉ đăng ký'}
            </div>
            <MetricValues metric={primary} />
            {primary.note && <p>Ghi chú: {primary.note}</p>}
            <details className="reference-details">
              <summary>Chi tiết công thức</summary>
              <p>{primary.purpose}</p>
            </details>
            {approved
              ? canEdit &&
                !working && (
                  <div className="card-actions">
                    <button
                      className="button secondary small"
                      onClick={() => setModal({ type: 'metric', item: approved })}
                    >
                      Chỉnh sửa công thức
                    </button>
                  </div>
                )
              : renderActions(primary)}
            {working && working.id !== primary.id && (
              <div className="metric-working">
                <div className="case-top">
                  <h3>Thay đổi · v{working.version}</h3>
                  <StatusBadge status={working.status} />
                </div>
                {working.name !== primary.name && <p>{working.name}</p>}
                <MetricValues metric={working} />
                {working.note && <p>Ghi chú: {working.note}</p>}
                {renderActions(working)}
              </div>
            )}
            {history.length > 0 && (
              <details className="reference-details metric-history">
                <summary>Lịch sử phiên bản ({history.length})</summary>
                {history.map((metric) => (
                  <div className="metric-history-row" key={metric.id}>
                    <div className="case-top">
                      <span>
                        v{metric.version} · {metric.name}
                      </span>
                      <StatusBadge status={metric.status} />
                    </div>
                    <MetricValues metric={metric} />
                    <p>{metric.purpose}</p>
                  </div>
                ))}
              </details>
            )}
          </section>
        ))}
      </div>
      {groups.length === 0 && <p>Chưa có công thức chỉ số.</p>}
    </>
  );
}
