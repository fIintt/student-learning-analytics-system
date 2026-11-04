import { useState } from 'react';

export default function ChangePasswordForm({ api, onChanged }) {
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  async function submit(event) {
    event.preventDefault();
    if (busy) return;
    const data = new FormData(event.target);
    const password = data.get('password');
    if (password !== data.get('confirm')) return setError('Hai mật khẩu mới không khớp.');
    if (new TextEncoder().encode(password).length > 72)
      return setError('Mật khẩu tối đa 72 byte UTF-8.');
    setBusy(true);
    setError('');
    try {
      await api('/auth/change-password', {
        method: 'POST',
        body: { current_password: data.get('current_password'), password },
      });
      onChanged();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <form onSubmit={submit}>
      <label>
        Mật khẩu hiện tại
        <input
          name="current_password"
          type="password"
          autoComplete="current-password"
          required
        />
      </label>
      <label>
        Mật khẩu mới
        <input
          name="password"
          type="password"
          minLength={8}
          maxLength={72}
          autoComplete="new-password"
          required
        />
      </label>
      <label>
        Nhập lại mật khẩu mới
        <input name="confirm" type="password" autoComplete="new-password" required />
      </label>
      {error && (
        <p role="alert" className="form-error">
          {error}
        </p>
      )}
      <button className="button" disabled={busy}>
        {busy ? 'Đang lưu…' : 'Đổi mật khẩu và đăng nhập lại'}
      </button>
    </form>
  );
}
