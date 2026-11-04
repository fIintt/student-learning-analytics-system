// Bảng dữ liệu API: mỗi cột có nhãn và hàm lấy nội dung ô.
export default function DataTable({ rows, columns, rowKey = 'id' }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {columns.map(([label]) => (
              <th key={label}>{label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={row[rowKey] ?? index}>
              {columns.map(([label, render]) => (
                <td key={label}>{render(row) ?? '—'}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {!rows.length && <p className="empty">Chưa có dữ liệu.</p>}
    </div>
  );
}
