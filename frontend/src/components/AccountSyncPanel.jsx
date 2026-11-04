import { useState } from 'react';
import DataTable from './DataTable';

export default function AccountSyncPanel({ api, preview, onSynced }) {
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  async function sync() {
    if (busy) return;
    setBusy(true);
    setError('');
    setResult(null);
    try {
      setResult(await api('/admin/accounts/sync', { method: 'POST' }));
      onSynced?.();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel">
      <div className="panel-head">
        <h2>Tài khoản từ pipeline</h2>
        <button className="button secondary" disabled={busy || preview} onClick={sync}>
          {busy ? 'Đang đồng bộ…' : 'Đồng bộ tài khoản nguồn'}
        </button>
      </div>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      {result && (
        <>
          <p className="portal-section" role="status">
            Tổng {result.total} · Tạo mới {result.created} · Bỏ qua {result.skipped} ·
            Xung đột {result.conflicts}
          </p>
          <DataTable
            rows={result.items}
            rowKey="username"
            columns={[
              ['Tên đăng nhập', (r) => r.username],
              [
                'Kết quả',
                (r) =>
                  ({
                    created: 'Đã tạo',
                    skipped: 'Bỏ qua',
                    conflict: 'Xung đột',
                  })[r.status] || r.status,
              ],
              ['Lý do', (r) => r.reason],
              ['ID tài khoản', (r) => r.user_id],
            ]}
          />
        </>
      )}
    </section>
  );
}
