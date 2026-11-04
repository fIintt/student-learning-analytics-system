// Dùng cùng một cách hiển thị số trên tất cả màn hình.
export function formatNumber(value) {
  if (value == null) return '—';
  return new Intl.NumberFormat('vi-VN', {
    maximumFractionDigits: 2,
  }).format(value);
}
