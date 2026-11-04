import { useState } from 'react';
import { linePath, selectTerms } from '../utils/chartData';
import { formatNumber } from '../utils/format';

const series = [
  { field: 'semester_gpa', name: 'GPA học kỳ', color: 'var(--color-primary)' },
  { field: 'cumulative_gpa', name: 'GPA tích lũy', color: '#7b8999' },
];

export default function GpaTrendChart({ trend }) {
  const [year, setYear] = useState('all');
  const [limit, setLimit] = useState('6');
  const [visible, setVisible] = useState(['semester_gpa', 'cumulative_gpa']);
  const [selected, setSelected] = useState(null);
  const years = [...new Set(trend.map((row) => row.academic_year))].sort().reverse();
  const rows = selectTerms(trend, year, limit);
  const keyOf = (row) => `${row.academic_year}-${row.semester}`;
  const active = rows.find((row) => keyOf(row) === selected) || rows.at(-1);
  const activeIndex = active ? rows.indexOf(active) : -1;
  // Khung tọa độ cố định giúp trục GPA luôn giữ thang 0–4 khi đổi bộ lọc.
  const x = (index) => (rows.length === 1 ? 400 : 48 + (index * 680) / (rows.length - 1));
  const y = (value) => 216 - value * 46;
  const animationKey = `${year}-${limit}-${visible.join(',')}-${rows.map((r) => `${r.semester_gpa}:${r.cumulative_gpa}`).join(',')}`;

  function toggle(field) {
    setVisible((old) =>
      old.includes(field) ? old.filter((item) => item !== field) : [...old, field],
    );
  }

  return (
    <section className="panel chart-panel">
      <div className="chart-heading">
        <h2>GPA qua các học kỳ</h2>
        <div className="chart-filters">
          <select
            aria-label="Năm học của biểu đồ GPA"
            value={year}
            onChange={(e) => setYear(e.target.value)}
          >
            <option value="all">Tất cả năm học</option>
            {years.map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
          <select
            aria-label="Số học kỳ trên biểu đồ GPA"
            value={limit}
            onChange={(e) => setLimit(e.target.value)}
          >
            <option value="4">4 kỳ gần nhất</option>
            <option value="6">6 kỳ gần nhất</option>
            <option value="all">Toàn bộ học kỳ</option>
          </select>
        </div>
      </div>
      <div className="chart-series" aria-label="Đường dữ liệu GPA">
        {series.map((item) => (
          <button
            key={item.field}
            type="button"
            aria-pressed={visible.includes(item.field)}
            onClick={() => toggle(item.field)}
          >
            <span style={{ background: item.color }} />
            {item.name}
          </button>
        ))}
      </div>
      {!rows.length ? (
        <p className="chart-empty">Chưa có kết quả trong khoảng đã chọn.</p>
      ) : (
        <>
          <div className="gpa-chart-scroll">
            <svg
              className="gpa-chart"
              style={{ minWidth: Math.max(560, rows.length * 70) }}
              viewBox="0 0 760 264"
              role="group"
              aria-label="Biểu đồ GPA theo học kỳ, thang điểm từ 0 đến 4"
            >
              {[0, 1, 2, 3, 4].map((value) => (
                <g key={value} className="chart-axis">
                  <line x1="48" x2="728" y1={y(value)} y2={y(value)} />
                  <text x="28" y={y(value) + 4}>
                    {value}
                  </text>
                </g>
              ))}
              {active && (
                <line
                  className="gpa-guide"
                  x1={x(activeIndex)}
                  x2={x(activeIndex)}
                  y1="26"
                  y2="216"
                />
              )}
              <g key={animationKey}>
                {series
                  .filter((item) => visible.includes(item.field))
                  .map((item) => (
                    <g key={item.field} style={{ color: item.color }}>
                      <path
                        className="gpa-line"
                        pathLength="1"
                        d={linePath(rows, item.field, x, y)}
                      />
                      {rows.map(
                        (row, index) =>
                          Number.isFinite(row[item.field]) && (
                            <circle
                              key={keyOf(row)}
                              cx={x(index)}
                              cy={y(row[item.field])}
                              r={index === activeIndex ? 5 : 3.5}
                              fill="white"
                              stroke="currentColor"
                              strokeWidth="2"
                            />
                          ),
                      )}
                    </g>
                  ))}
              </g>
              {rows.map((row, index) => {
                const width = rows.length > 1 ? 680 / (rows.length - 1) : 680;
                return (
                  <g key={keyOf(row)}>
                    <text className="gpa-tick" x={x(index)} y="240" textAnchor="middle">
                      HK{row.semester}
                      <tspan x={x(index)} dy="16">
                        {row.academic_year.slice(0, 4)}–{row.academic_year.slice(-2)}
                      </tspan>
                    </text>
                    <rect
                      className="gpa-hit"
                      x={Math.max(36, x(index) - width / 2)}
                      y="25"
                      width={Math.min(width, 740 - Math.max(36, x(index) - width / 2))}
                      height="193"
                      role="button"
                      tabIndex="0"
                      aria-pressed={index === activeIndex}
                      aria-label={`${row.academic_year}, học kỳ ${row.semester}: GPA học kỳ ${formatNumber(row.semester_gpa)}, GPA tích lũy ${formatNumber(row.cumulative_gpa)}`}
                      onMouseEnter={() => setSelected(keyOf(row))}
                      onClick={() => setSelected(keyOf(row))}
                      onFocus={() => setSelected(keyOf(row))}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          setSelected(keyOf(row));
                        }
                      }}
                    />
                  </g>
                );
              })}
            </svg>
          </div>
          {active && (
            <div className="gpa-reading" aria-live="polite">
              <strong>
                {active.academic_year} · HK{active.semester}
              </strong>
              {series
                .filter((item) => visible.includes(item.field))
                .map((item) => (
                  <span key={item.field}>
                    {item.name} <b>{formatNumber(active[item.field])}</b>
                  </span>
                ))}
            </div>
          )}
        </>
      )}
    </section>
  );
}
