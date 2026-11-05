import ImportDetail from './ImportDetail';
import ChangePasswordForm from '../forms/ChangePasswordForm';
import StatusBadge from './StatusBadge';
import { LogOut, X } from 'lucide-react';
import { formatNumber } from '../utils/format';
import ReviewAlertForm from '../forms/ReviewAlertForm';
import MetricForm from '../forms/MetricForm';
import RejectMetricForm from '../forms/RejectMetricForm';
import CalculateMetricsForm from '../forms/CalculateMetricsForm';
import UploadCsvForm from '../forms/UploadCsvForm';
import SupportCaseContent from '../forms/SupportCaseContent';
export default function AppDialog({
  setModal,
  modal,
  session,
  role,
  groups,
  setSession,
  handleReviewAlert,
  findStudent,
  findMetric,
  showNotification,
  setDatabase,
  handleSaveMetric,
  changeMetricStatus,
  handleCalculateMetrics,
  database,
  handleUploadCsv,
  canEdit,
  handleSaveFollowup,
  confirmImport,
  error,
  busy,
  api,
}) {
  return (
    <div
      className="modal-overlay"
      onClick={(event) => {
        if (event.target === event.currentTarget) {
          setModal(null);
        }
      }}
    >
      <section
        className={'modal ' + (modal.type === 'batch' ? 'wide' : '')}
        role="dialog"
        aria-modal="true"
        aria-label="Chi tiết thao tác"
      >
        <div className="modal-head">
          <h2>
            {
              {
                review: 'Rà soát cảnh báo',
                metric: modal.item ? 'Chỉnh sửa công thức' : 'Tạo công thức',
                editMetric: 'Sửa bản nháp',
                rejectMetric: 'Từ chối công thức',
                compute: 'Tính chỉ số',
                upload: 'Nhập dữ liệu CSV',
                batch: 'Chi tiết nhập dữ liệu',
                case: 'Theo dõi trường hợp hỗ trợ',
                account: 'Thông tin tài khoản',
                alert: 'Chi tiết cảnh báo',
              }[modal.type]
            }
          </h2>
          <button
            className="icon-button"
            aria-label="Đóng"
            onClick={() => setModal(null)}
          >
            <X size={20} />
          </button>
        </div>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        {modal.loading && <p role="status">Đang tải chi tiết…</p>}
        {modal.error && (
          <p className="form-error" role="alert">
            {modal.error}
          </p>
        )}
        {!modal.loading && !modal.error && (
          <fieldset disabled={busy}>
            {modal.type === 'account' && (
              <>
                <p>
                  <b>{session.username || session.email}</b>
                </p>
                <p>
                  Vai trò:{' '}
                  {{ admin: 'Quản trị viên', reviewer: 'Giáo viên', viewer: 'Sinh viên' }[
                    role
                  ] || role}
                </p>
                {role === 'admin' && <p>Phạm vi: Toàn hệ thống</p>}
                {role === 'reviewer' &&
                  (groups.length > 0 ? (
                    <details className="reference-details account-groups">
                      <summary>Phạm vi: {groups.length} nhóm phụ trách</summary>
                      <ul>
                        {groups.map((group) => (
                          <li key={group}>{group}</li>
                        ))}
                      </ul>
                    </details>
                  ) : (
                    <p>Phạm vi: Chưa được gán nhóm</p>
                  ))}
                <p>Hết phiên: {new Date(session.expires).toLocaleString('vi-VN')}</p>
                <details className="reference-details">
                  <summary>Đổi mật khẩu</summary>
                  <ChangePasswordForm api={api} onChanged={() => setSession(null)} />
                </details>
                <button
                  className="button secondary"
                  onClick={() => {
                    setSession(null);
                    setModal(null);
                  }}
                >
                  <LogOut size={16} />
                  Đăng xuất
                </button>
              </>
            )}
            {modal.type === 'review' && (
              <ReviewAlertForm
                handleReviewAlert={handleReviewAlert}
                findStudent={findStudent}
                modal={modal}
                findMetric={findMetric}
                setModal={setModal}
                session={session}
              />
            )}
            {['metric', 'editMetric'].includes(modal.type) && (
              <MetricForm
                modal={modal}
                showNotification={showNotification}
                setDatabase={setDatabase}
                setModal={setModal}
                handleSaveMetric={handleSaveMetric}
              />
            )}
            {modal.type === 'rejectMetric' && (
              <RejectMetricForm
                changeMetricStatus={changeMetricStatus}
                modal={modal}
                setModal={setModal}
              />
            )}
            {modal.type === 'compute' && (
              <CalculateMetricsForm
                handleCalculateMetrics={handleCalculateMetrics}
                database={database}
              />
            )}
            {modal.type === 'upload' && (
              <UploadCsvForm
                handleUploadCsv={handleUploadCsv}
                setModal={setModal}
                modal={modal}
              />
            )}
            {modal.type === 'batch' && (
              <ImportDetail modal={modal} confirmImport={confirmImport} />
            )}
            {modal.type === 'alert' && (
              <>
                <p>
                  {findStudent(modal.item.student)?.name} ·{' '}
                  {findMetric(modal.item.metric)?.name}
                </p>
                <StatusBadge status={modal.item.status} />
                <p>
                  Giá trị: {formatNumber(modal.item.value)} · Phiên bản{' '}
                  {modal.item.version}
                </p>
                <p>
                  Điều kiện cảnh báo: {modal.item.operator} {modal.item.threshold}
                </p>
                <p>
                  {modal.item.term} · {new Date(modal.item.date).toLocaleString('vi-VN')}
                </p>
                <p>Ghi chú: {modal.item.note || 'Chưa được rà soát'}</p>
              </>
            )}
            {modal.type === 'case' && (
              <SupportCaseContent
                findStudent={findStudent}
                modal={modal}
                canEdit={canEdit}
                handleSaveFollowup={handleSaveFollowup}
                database={database}
                findMetric={findMetric}
              />
            )}
          </fieldset>
        )}
      </section>
    </div>
  );
}
