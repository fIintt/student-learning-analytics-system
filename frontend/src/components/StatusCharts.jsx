import { useState } from 'react';
import { filterByDays } from '../utils/chartData';

const alertStates = [
  ['pending', 'Chờ rà soát', '#bb8a50'],
  ['confirmed', 'Đã xác nhận', 'var(--color-primary)'],
  ['dismissed', 'Đã bác', '#a8b3bf'],
  ['superseded', 'Đã được thay thế', '#7e8a9c'],
];
const caseStates = [
  ['open', 'Mở', 'var(--color-primary)'],
  ['in_progress', 'Đang xử lý', '#7298b8'],
  ['closed', 'Đã đóng', '#a8b3bf'],
];

function TimeFilter({ value, onChange, label }) {
  return (
    <select aria-label={label} value={value} onChange={(e) => onChange(e.target.value)}>
      <option value="all">Mọi thời điểm tạo</option>
      <option value="30">Tạo trong 30 ngày</option>
      <option value="90">Tạo trong 90 ngày</option>
    </select>
  );
}

export default function StatusCharts({ alerts, cases, metrics, loadErrors = {} }) {
  const [alertDays, setAlertDays] = useState('all');
  const [caseDays, setCaseDays] = useState('all');
  const [metric, setMetric] = useState('all');
  const alertRows = filterByDays(alerts, alertDays).filter(
    (row) => metric === 'all' || row.metric === metric,
  );
  const caseRows = filterByDays(cases, caseDays);
  const counts = (rows, states) =>
    states.map(([key, label, color]) => ({
      key,
      label,
      color,
      value: rows.filter((row) => row.status === key).length,
    }));
  const alertCounts = counts(alertRows, alertStates);
  const caseCounts = counts(caseRows, caseStates);
  const alertMax = Math.max(1, ...alertCounts.map((row) => row.value));
  const caseMax = Math.max(1, ...caseCounts.map((row) => row.value));
  const unavailable = (key) => loadErrors.students || loadErrors[key];
  return (
    <div className="status-charts">
      <section className="panel chart-panel">
        <div className="chart-heading">
          <h2>Cảnh báo theo trạng thái</h2>
        </div>
        <div className="chart-filters status-chart-filters">
          <TimeFilter
            label="Thời gian tạo cảnh báo"
            value={alertDays}
            onChange={setAlertDays}
          />
          <select
            aria-label="Công thức của biểu đồ cảnh báo"
            value={metric}
            onChange={(e) => setMetric(e.target.value)}
            disabled={!!loadErrors.metrics}
          >
            <option value="all">Tất cả công thức</option>
            {metrics.map((item) => (
              <option key={item.id} value={`${item.code}@${item.version}`}>
                {item.name} · v{item.version}
              </option>
            ))}
          </select>
        </div>
        {unavailable('alerts') ? (
          <p className="chart-empty">Chưa tải được dữ liệu cảnh báo.</p>
        ) : (
          <>
            <div
              className="status-columns"
              aria-label={`Số cảnh báo theo trạng thái, tổng ${alertRows.length}`}
            >
              {alertCounts.map((row) => (
                <div className="status-column" key={row.key}>
                  <div className="status-column-area">
                    <div
                      className="status-column-level"
                      style={{ height: `${(row.value / alertMax) * 100}%` }}
                    >
                      <b>{row.value}</b>
                      <div
                        key={`${alertDays}-${metric}-${row.value}`}
                        className="status-column-fill"
                        style={{ background: row.color }}
                        title={`${row.label}: ${row.value} cảnh báo`}
                      />
                    </div>
                  </div>
                  <span>{row.label}</span>
                </div>
              ))}
            </div>
            {!alertRows.length && (
              <p className="chart-empty compact">
                Không có cảnh báo trong phạm vi đã chọn.
              </p>
            )}
          </>
        )}
      </section>
      <section className="panel chart-panel">
        <div className="chart-heading">
          <h2>Hồ sơ hỗ trợ</h2>
        </div>
        <div className="chart-filters status-chart-filters">
          <TimeFilter
            label="Thời gian mở hồ sơ"
            value={caseDays}
            onChange={setCaseDays}
          />
        </div>
        {unavailable('cases') ? (
          <p className="chart-empty">Chưa tải được dữ liệu hồ sơ.</p>
        ) : (
          <>
            <div
              className="status-horizontal"
              aria-label={`Số hồ sơ theo trạng thái, tổng ${caseRows.length}`}
            >
              {caseCounts.map((row) => (
                <div className="status-horizontal-row" key={row.key}>
                  <span>{row.label}</span>
                  <div className="status-horizontal-track">
                    <div
                      key={`${caseDays}-${row.value}`}
                      className="status-horizontal-fill"
                      style={{
                        width: `${(row.value / caseMax) * 100}%`,
                        background: row.color,
                      }}
                      title={`${row.label}: ${row.value} hồ sơ`}
                    />
                  </div>
                  <b>{row.value}</b>
                </div>
              ))}
            </div>
            {!caseRows.length && (
              <p className="chart-empty compact">Không có hồ sơ trong phạm vi đã chọn.</p>
            )}
          </>
        )}
      </section>
    </div>
  );
}
