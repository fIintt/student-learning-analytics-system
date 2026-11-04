import { statusLabels } from '../config/navigation';

// Nhận mã trạng thái tiếng Anh, hiển thị nhãn tiếng Việt và màu tương ứng.
export default function StatusBadge({ status }) {
  return <span className={'badge ' + status}>{statusLabels[status] || status}</span>;
}
