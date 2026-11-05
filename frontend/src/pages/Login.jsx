import PasswordInput from '../components/PasswordInput';
import { createSession } from '../services/session';
// Màn hình đăng nhập qua API. Đọc file này trước để hiểu state, form và sự kiện.
import { useState } from 'react';
import { request } from '../services/api';
import { ArrowRight } from 'lucide-react';
export default function Login({ onLogin }) {
  const [busy, setBusy] = useState(false);
  async function handleLogin(event) {
    event.preventDefault();
    if (busy) return;
    const data = new FormData(event.target);
    setBusy(true);
    setError('');
    try {
      const issuedAt = Date.now();
      const result = await request('/auth/login', {
        method: 'POST',
        body: {
          username: data.get('username').trim(),
          password: data.get('password'),
        },
      });
      const user = await request('/auth/me', { token: result.access_token });
      onLogin(createSession(result, user, issuedAt));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }
  const [error, setError] = useState('');
  return (
    <div className="login">
      <section className="login-story">
        <div className="brand">
          <img
            className="brand-logo"
            src="/images/neu-logo.png"
            alt="Logo Đại học Kinh tế Quốc dân"
          />
          <b>
            Phân tích học tập
            <span>NHÓM 6</span>
          </b>
        </div>

        <div>
          <span className="login-school">ĐẠI HỌC KINH TẾ QUỐC DÂN</span>

          <h1>Hệ thống phân tích học tập</h1>
        </div>
      </section>
      <section className="login-form">
        <div className="login-form-inner">
          <h2>Đăng nhập</h2>

          <form onSubmit={handleLogin}>
            <label>
              Tên đăng nhập
              <input type="text" name="username" autoComplete="username" required />
            </label>
            <label>
              Mật khẩu
              <PasswordInput name="password" autoComplete="current-password" required />
            </label>
            {error && (
              <p className="form-error" role="alert">
                {error}
              </p>
            )}
            <button className="button login-submit" disabled={busy}>
              {busy ? 'Đang đăng nhập…' : 'Đăng nhập'} <ArrowRight size={17} />
            </button>
          </form>
        </div>
      </section>
    </div>
  );
}
