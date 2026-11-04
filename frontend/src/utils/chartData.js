// Chỉ tổng hợp dữ liệu API đã được phép xem, không sinh dữ liệu mẫu.
export function filterByDays(rows, days, now = Date.now()) {
  if (days === 'all') return rows;
  const start = now - Number(days) * 24 * 60 * 60 * 1000;
  return rows.filter((row) => {
    const date = Date.parse(row.date || row.created_at);
    return date >= start && date <= now;
  });
}

export function selectTerms(trend, year, limit) {
  const rows = [...trend]
    .filter((row) => year === 'all' || row.academic_year === year)
    .sort(
      (a, b) => a.academic_year.localeCompare(b.academic_year) || a.semester - b.semester,
    );
  return limit === 'all' ? rows : rows.slice(-Number(limit));
}

// Mỗi giá trị thiếu bắt đầu một đoạn mới; không nối đường qua khoảng trống.
export function linePath(rows, field, x, y) {
  let connected = false;
  return rows
    .map((row, index) => {
      const value = row[field];
      if (value == null || !Number.isFinite(value)) {
        connected = false;
        return '';
      }
      const command = `${connected ? 'L' : 'M'}${x(index)},${y(value)}`;
      connected = true;
      return command;
    })
    .join(' ');
}
