import { useEffect, useRef, useState } from 'react';
import { allPages } from '../services/api';
import DataTable from '../components/DataTable';

export default function TeacherGroupsPage({ api, token, groups, preview, groupsError }) {
  const [teachers, setTeachers] = useState([]);
  const [selected, setSelected] = useState(null);
  const [ids, setIds] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [reload, setReload] = useState(0);
  const [query, setQuery] = useState('');
  const editorRef = useRef(null);
  const searchRef = useRef(null);

  useEffect(() => {
    if (!selected) return;
    editorRef.current?.scrollIntoView({ block: 'start' });
    searchRef.current?.focus({ preventScroll: true });
  }, [selected]);
  useEffect(() => {
    if (preview) return;
    const controller = new AbortController();
    setBusy(true);
    setError('');
    allPages('/admin/teacher-accounts', { token, signal: controller.signal })
      .then((rows) => {
        if (!controller.signal.aborted) setTeachers(rows);
      })
      .catch((err) => {
        if (!controller.signal.aborted) {
          setError(err.message);
          if (err.status === 401) api('/auth/me').catch(() => {});
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setBusy(false);
      });
    return () => controller.abort();
  }, [token, preview, reload]);
  async function save(event) {
    event.preventDefault();
    if (busy || groupsError) return;
    setBusy(true);
    setError('');
    setMessage('');
    try {
      // PUT thay toàn bộ tập nhóm, kể cả [] để gỡ tất cả; ID gửi dưới dạng số.
      const user = await api(`/admin/teacher-accounts/${selected.id}/groups`, {
        method: 'PUT',
        body: { group_ids: ids },
      });
      setTeachers((rows) => rows.map((row) => (row.id === user.id ? user : row)));
      setSelected(null);
      setMessage('Đã cập nhật nhóm. Quyền mới áp dụng ở request tiếp theo.');
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }
  if (preview) return <p>Cần đăng nhập backend để tải và phân nhóm giáo viên.</p>;
  return (
    <section className="panel">
      <div className="panel-head">
        <h2>Phạm vi nhóm của giáo viên</h2>
        <button
          className="text-button"
          disabled={busy}
          onClick={() => setReload((n) => n + 1)}
        >
          Tải lại
        </button>
      </div>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      {message && <p role="status">{message}</p>}
      <DataTable
        rows={teachers}
        columns={[
          ['Tên đăng nhập', (r) => r.username],
          ['Họ tên', (r) => r.full_name],
          ['Email liên hệ', (r) => r.email],
          ['Trạng thái', (r) => (r.is_active ? 'Đang hoạt động' : 'Đã khóa')],
          [
            'Nhóm',
            (r) =>
              r.group_ids
                .map((id) => groups.find((g) => g.id === id)?.name || `#${id}`)
                .join(', ') || 'Chưa gán',
          ],
          [
            'Thao tác',
            (r) => (
              <button
                className="text-button"
                disabled={busy || !!groupsError}
                onClick={() => {
                  setSelected(r);
                  setIds([...r.group_ids]);
                  setQuery('');
                  setError('');
                }}
              >
                Sửa nhóm
              </button>
            ),
          ],
        ]}
      />
      {selected && (
        <form ref={editorRef} className="portal-section" onSubmit={save}>
          <h3>
            Nhóm của {selected.full_name} ({selected.username})
          </h3>
          <label>
            Tìm nhóm
            <input
              ref={searchRef}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </label>
          <fieldset disabled={busy} style={{ maxHeight: 300, overflowY: 'auto' }}>
            {groups
              .filter((g) => g.name.toLowerCase().includes(query.toLowerCase()))
              .map((g) => (
                <label
                  key={g.id}
                  style={{ display: 'flex', alignItems: 'center', gap: 10 }}
                >
                  <input
                    type="checkbox"
                    style={{ width: 'auto' }}
                    checked={ids.includes(g.id)}
                    onChange={(e) =>
                      setIds((old) =>
                        e.target.checked
                          ? [...old, g.id]
                          : old.filter((id) => id !== g.id),
                      )
                    }
                  />
                  {g.name}
                </label>
              ))}
          </fieldset>
          <p>Đã chọn {ids.length} nhóm. Bỏ chọn tất cả sẽ gỡ toàn bộ phạm vi.</p>
          <button
            type="button"
            className="text-button"
            disabled={busy}
            onClick={() => setIds([])}
          >
            Bỏ chọn tất cả
          </button>{' '}
          <button className="button" disabled={busy || !!groupsError}>
            Lưu nhóm
          </button>{' '}
          <button
            type="button"
            className="button secondary"
            disabled={busy}
            onClick={() => setSelected(null)}
          >
            Hủy
          </button>
        </form>
      )}
    </section>
  );
}
