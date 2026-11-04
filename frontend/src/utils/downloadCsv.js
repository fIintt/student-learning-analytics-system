// Tạo và tải tệp CSV. Không gửi dữ liệu lên máy chủ.
export default function downloadCsv(fileName, rows) {
  const csvLines = rows.map((row) => {
    const escapedCells = row.map((cell) => {
      const text = String(cell).replaceAll('"', '""');
      return `"${text}"`;
    });
    return escapedCells.join(',');
  });

  // BOM giúp Excel nhận diện đúng tiếng Việt.
  const csvContent = '\uFEFF' + csvLines.join('\r\n');
  const file = new Blob([csvContent], { type: 'text/csv;charset=utf-8' });
  const fileUrl = URL.createObjectURL(file);
  const downloadLink = document.createElement('a');
  downloadLink.href = fileUrl;
  downloadLink.download = fileName;
  downloadLink.click();
  URL.revokeObjectURL(fileUrl);
}
