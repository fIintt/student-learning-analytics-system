import GpaTrendChart from '../components/GpaTrendChart';
import { useEffect, useState } from 'react';
import { allPages } from '../services/api';
import DataTable from '../components/DataTable';
import StatusBadge from '../components/StatusBadge';
import ChangePasswordForm from '../forms/ChangePasswordForm';

export default function StudentPortal({ session, api, logout }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [passwordForm, setPasswordForm] = useState(false);
  const [reload, setReload] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    const options = { token: session.token, signal: controller.signal };
    setLoading(true);
    setError('');
    Promise.all([
      api('/me/student-profile', { signal: controller.signal }),
      api('/me/academic-summary', { signal: controller.signal }),
      allPages('/me/academic-performance', options),
      allPages('/me/alerts', options),
    ])
      .then(([profile, summary, terms, alerts]) => {
        if (!controller.signal.aborted) setData({ profile, summary, terms, alerts });
      })
      .catch((err) => {
        if (!controller.signal.aborted) {
          if (err.status === 401) logout();
          else setError(err.message);
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [session.token, reload]);
  return (
    <div className="student-portal">
      <header className="portal-header">
        <img src="/images/neu-logo.png" alt="Logo NEU" width="60" height="60" />
        <h1>Học tập của tôi</h1>
        <button
          className="button secondary"
          onClick={() => setPasswordForm(!passwordForm)}
        >
          Đổi mật khẩu
        </button>
        <button className="button secondary" onClick={logout}>
          Đăng xuất
        </button>
      </header>
      {passwordForm && (
        <section className="panel portal-section">
          <ChangePasswordForm api={api} onChanged={logout} />
        </section>
      )}
      {loading && <p role="status">Đang tải dữ liệu…</p>}
      {error && (
        <p className="form-error" role="alert">
          {error} <button onClick={() => setReload(reload + 1)}>Thử lại</button>
        </p>
      )}
      {data && !error && (
        <>
          <section className="panel portal-section">
            <h2>{data.profile.name}</h2>
            <p>
              {data.profile.student_id} · {data.profile.program_name} · Khóa{' '}
              {data.profile.cohort}
            </p>
            <StatusBadge status={data.profile.academic_status} />
          </section>
          <div className="stats">
            <section className="stat">
              <div>GPA học kỳ mới nhất</div>
              <strong>{data.summary.latest?.semester_gpa ?? '—'}</strong>
            </section>
            <section className="stat">
              <div>GPA tích lũy mới nhất</div>
              <strong>{data.summary.latest?.cumulative_gpa ?? '—'}</strong>
            </section>
            <section className="stat">
              <div>Số học kỳ có dữ liệu</div>
              <strong>{data.summary.term_count}</strong>
            </section>
            <section className="stat">
              <div>Thay đổi GPA học kỳ</div>
              <strong>{data.summary.latest?.gpa_change ?? '—'}</strong>
            </section>
          </div>
          <GpaTrendChart trend={data.summary.trend} />
          <section className="panel">
            <div className="panel-head">
              <h2>Kết quả theo học kỳ</h2>
            </div>
            <DataTable
              rows={data.terms}
              columns={[
                ['Năm học', (r) => r.academic_year],
                ['Học kỳ', (r) => r.semester],
                ['GPA học kỳ', (r) => r.semester_gpa],
                ['GPA tích lũy', (r) => r.cumulative_gpa],
                ['TC đăng ký', (r) => r.registered_credits],
                ['TC đạt', (r) => r.passed_credits],
                ['TC rớt', (r) => r.failed_credits],
              ]}
            />
          </section>
          <section className="panel">
            <div className="panel-head">
              <h2>Cảnh báo của tôi</h2>
            </div>
            <DataTable
              rows={data.alerts}
              columns={[
                ['Chỉ số', (r) => r.metric_name],
                ['Năm / kỳ', (r) => `${r.academic_year} · HK${r.semester}`],
                ['Giá trị', (r) => r.value],
                ['Ngưỡng', (r) => `${r.threshold.operator} ${r.threshold.value}`],
                ['Trạng thái', (r) => <StatusBadge status={r.status} />],
                ['Hỗ trợ', (r) => r.support_message],
              ]}
            />
          </section>
        </>
      )}
    </div>
  );
}
