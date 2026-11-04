import { useEffect, useState } from 'react';
import { allPages } from '../services/api';
import DataTable from '../components/DataTable';

export default function StudentAccountsPage({ api, token, students }) {
  const [accounts, setAccounts] = useState([]);
  const [form, setForm] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [reload, setReload] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setBusy(true);
    setError('');
    allPages('/admin/student-accounts', { token, signal: controller.signal })
      .then((rows) => {
        if (!controller.signal.aborted) setAccounts(rows);
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
  }, [token, reload]);
  async function submit(event) {
    event.preventDefault();
    if (busy) return;
    const data = new FormData(event.target);
    const password = data.get('password');
    if (password && new TextEncoder().encode(password).length > 72)
      return setError('Mật khẩu tối đa 72 byte UTF-8.');
    setBusy(true);
    setError('');
    setMessage('');
    try {
      if (form.type === 'create')
        await api('/admin/student-accounts', {
          method: 'POST',
          body: {
            username: data.get('username').trim(),
            email: data.get('email').trim() || null,
            student_id: data.get('student_id'),
            password,
          },
        });
      if (form.type === 'reset')
        await api(`/admin/student-accounts/${form.item.id}/reset-password`, {
          method: 'POST',
          body: { password },
        });
      if (form.type === 'link')
        await api(`/auth/users/${form.item.id}/student-link`, {
          method: 'PUT',
          body: { student_id: data.get('student_id') || null },
        });
      if (form.type === 'status')
        await api(`/admin/student-accounts/${form.item.id}`, {
          method: 'PATCH',
          body: { is_active: !form.item.is_active },
        });
      setForm(null);
      setMessage('Đã cập nhật tài khoản.');
      setReload((n) => n + 1);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel">
      <div className="panel-head">
        <h2>Tài khoản sinh viên</h2>
        <button
          className="button"
          disabled={busy}
          onClick={() => setForm({ type: 'create' })}
        >
          Tạo tài khoản
        </button>
      </div>
      <div className="account-tools">
        {error && (
          <p className="form-error" role="alert">
            {error} <button onClick={() => setReload((n) => n + 1)}>Tải lại</button>
          </p>
        )}
        {message && <p role="status">{message}</p>}
        {form && (
          <form onSubmit={submit} key={`${form.type}-${form.item?.id}`}>
            <h3>
              {
                {
                  create: 'Tạo tài khoản',
                  reset: 'Đặt mật khẩu tạm',
                  link: 'Liên kết mã sinh viên',
                  status: form.item?.is_active ? 'Khóa tài khoản' : 'Mở tài khoản',
                }[form.type]
              }
            </h3>
            {form.item && <p>{form.item.username}</p>}
            {form.type === 'create' && (
              <>
                <label>
                  Tên đăng nhập
                  <input name="username" pattern="\S+" maxLength={255} required />
                </label>
                <label>
                  Email liên hệ (không bắt buộc)
                  <input type="email" name="email" />
                </label>
              </>
            )}
            {['create', 'link'].includes(form.type) && (
              <label>
                Sinh viên
                <select
                  name="student_id"
                  defaultValue={form.item?.student_id || ''}
                  required={form.type === 'create'}
                >
                  <option value="">
                    {form.type === 'link' ? 'Gỡ liên kết' : 'Chọn sinh viên'}
                  </option>
                  {students.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.id} · {s.name}
                    </option>
                  ))}
                </select>
              </label>
            )}
            {['create', 'reset'].includes(form.type) && (
              <label>
                Mật khẩu tạm
                <input
                  type="password"
                  name="password"
                  minLength={8}
                  maxLength={72}
                  autoComplete="new-password"
                  required
                />
              </label>
            )}
            <button className="button" disabled={busy}>
              Xác nhận
            </button>{' '}
            <button
              className="button secondary"
              type="button"
              disabled={busy}
              onClick={() => setForm(null)}
            >
              Hủy
            </button>
          </form>
        )}
      </div>
      <DataTable
        rows={accounts}
        columns={[
          ['Tên đăng nhập', (r) => r.username],
          ['Email liên hệ', (r) => r.email],
          ['Họ tên', (r) => r.full_name],
          ['Mã SV', (r) => r.student_id],
          ['Trạng thái', (r) => (r.is_active ? 'Đang hoạt động' : 'Đã khóa')],
          [
            'Thao tác',
            (r) => (
              <div className="card-actions">
                {[
                  ['status', r.is_active ? 'Khóa' : 'Mở'],
                  ['reset', 'Đặt mật khẩu'],
                  ['link', 'Liên kết'],
                ].map(([type, label]) => (
                  <button
                    key={type}
                    className="text-button"
                    disabled={busy}
                    onClick={() => setForm({ type, item: r })}
                  >
                    {label}
                  </button>
                ))}
              </div>
            ),
          ],
        ]}
      />
    </section>
  );
}
