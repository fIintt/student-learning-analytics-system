import StatusBadge from '../components/StatusBadge';
import DataTable from '../components/DataTable';
import { saveDownload } from '../services/api';
export default function ImportDataPage({ setModal, database, api, showNotification }) {
  async function downloadTemplate() {
    try {
      saveDownload(
        await api('/academic-imports/template', { blob: true }),
        'ket-qua-hoc-tap-mau.csv',
      );
    } catch (err) {
      showNotification(err.message);
    }
  }
  return (
    <section className="panel">
      <div className="panel-head">
        <h2>Lịch sử nhập kết quả học kỳ</h2>
        <button className="button secondary" onClick={downloadTemplate}>
          Tải CSV mẫu
        </button>
      </div>
      <DataTable
        rows={database.batches}
        columns={[
          ['Tệp dữ liệu', (r) => r.filename],
          ['Thời gian', (r) => new Date(r.created_at).toLocaleString('vi-VN')],
          [
            'Tổng / đã nhập / bị loại',
            (r) => `${r.total_rows} / ${r.inserted_rows} / ${r.rejected_rows}`,
          ],
          ['Trạng thái', (r) => <StatusBadge status={r.status} />],
          [
            'Thao tác',
            (r) => (
              <button
                className="text-button"
                onClick={() => setModal({ type: 'batch', item: r })}
              >
                Chi tiết
              </button>
            ),
          ],
        ]}
      />
    </section>
  );
}
