import { useState } from 'react';
import { isSessionValid } from './services/session';
import TeacherGroupsPage from './pages/TeacherGroupsPage';
import AccountSyncPanel from './components/AccountSyncPanel';
import StudentPortal from './pages/StudentPortal';
import StudentAccountsPage from './pages/StudentAccountsPage';
import ChangePasswordForm from './forms/ChangePasswordForm';
// Ghép bố cục chung với màn hình đang chọn. Dữ liệu và sự kiện lấy từ useM11.
import StudentFilters from './components/StudentFilters';
import { X, Info } from 'lucide-react';
import useM11 from './hooks/useM11';
import Login from './pages/Login';
import OverviewPage from './pages/OverviewPage';
import StudentsPage from './pages/StudentsPage';
import AlertsPage from './pages/AlertsPage';
import SupportCasesPage from './pages/SupportCasesPage';
import ImportDataPage from './pages/ImportDataPage';
import MetricsPage from './pages/MetricsPage';
import StudentDetailPage from './pages/StudentDetailPage';
import AppDialog from './components/AppDialog';
import Sidebar from './components/Sidebar';
import Topbar from './components/Topbar';
import PageHeading from './components/PageHeading';
export default function App() {
  const [accountsVersion, setAccountsVersion] = useState(0);
  const {
    session,
    enterPreview,
    setSession,
    database,
    setDatabase,
    currentPage,
    selectedStudentId,
    searchQuery,
    setSearchQuery,
    selectedGroup,
    setSelectedGroup,
    selectedProgram,
    setSelectedProgram,
    selectedStatus,
    setSelectedStatus,
    modal,
    setModal,
    notification,
    setNotification,
    isMenuOpen,
    setIsMenuOpen,
    showNotification,
    navigateToPage,
    role,
    canEdit,
    accessibleStudents,
    filteredStudents,
    alerts,
    cases,
    pendingAlerts,
    findStudent,
    findMetric,
    openStudent,
    handleReviewAlert,
    handleSaveMetric,
    changeMetricStatus,
    loadErrors,
    loading,
    busy,
    error,
    refresh,
    confirmImport,
    api,
    handleCalculateMetrics,
    handleUploadCsv,
    handleSaveFollowup,
    handleExportReport,
    groups,
    activePage,
    selectedStudent,
  } = useM11();
  const studentFilters = (
    <StudentFilters
      searchQuery={searchQuery}
      setSearchQuery={setSearchQuery}
      selectedProgram={selectedProgram}
      setSelectedProgram={setSelectedProgram}
      database={database}
      accessibleStudents={accessibleStudents}
      selectedGroup={selectedGroup}
      setSelectedGroup={setSelectedGroup}
      groups={groups}
    />
  );
  if (!session?.preview && !isSessionValid(session)) {
    return (
      <Login
        onPreview={enterPreview}
        onLogin={(newSession) => {
          setSession(newSession);
          navigateToPage('overview');
        }}
      />
    );
  }
  if (session.must_change_password)
    return (
      <div className="password-required">
        <section className="panel portal-section">
          <h1>Đổi mật khẩu tạm</h1>
          <ChangePasswordForm api={api} onChanged={() => setSession(null)} />
          <button className="text-button" onClick={() => setSession(null)}>
            Đăng xuất
          </button>
        </section>
      </div>
    );
  if (role === 'viewer')
    return <StudentPortal session={session} api={api} logout={() => setSession(null)} />;
  return (
    <div className="shell">
      <Sidebar
        isMenuOpen={isMenuOpen}
        navigateToPage={navigateToPage}
        canEdit={canEdit}
        currentPage={currentPage}
        pendingAlerts={pendingAlerts}
        setModal={setModal}
        role={role}
        session={session}
      />
      <div className="main-shell">
        <Topbar
          preview={session.preview}
          setIsMenuOpen={setIsMenuOpen}
          isMenuOpen={isMenuOpen}
          activePage={activePage}
          navigateToPage={navigateToPage}
          pendingAlerts={pendingAlerts}
          role={role}
        />
        <main>
          {!!Object.keys(loadErrors).length && (
            <div className="notice" role="alert">
              Chưa tải được một số dữ liệu:{' '}
              {Object.entries(loadErrors)
                .map(
                  ([key, value]) =>
                    `${{ students: 'sinh viên', programs: 'chương trình', groups: 'nhóm', metrics: 'công thức', results: 'kết quả chỉ số', alerts: 'cảnh báo', cases: 'hồ sơ', batches: 'lịch sử nhập CSV' }[key]}: ${value}`,
                )
                .join('; ')}
              . Các phần khác vẫn dùng được.
            </div>
          )}
          {session.preview && (
            <div className="notice" role="status">
              Đang xem giao diện tạm. Chưa có dữ liệu hoặc token backend; các thao tác lưu
              cần đăng nhập thật.
              <button className="text-button" onClick={() => setSession(null)}>
                Về đăng nhập
              </button>
            </div>
          )}
          <div className="api-status">
            {loading && <span role="status">Đang tải dữ liệu…</span>}
            <button
              className="text-button"
              disabled={loading || busy}
              onClick={() => refresh()}
            >
              Tải lại dữ liệu
            </button>
          </div>
          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
          <fieldset disabled={busy || loading || !!error}>
            <PageHeading
              currentPage={currentPage}
              activePage={activePage}
              handleExportReport={handleExportReport}
              canEdit={canEdit}
              setModal={setModal}
            />

            {currentPage === 'overview' && (
              <OverviewPage
                loadErrors={loadErrors}
                studentFilters={studentFilters}
                database={database}
                filteredStudents={filteredStudents}
                pendingAlerts={pendingAlerts}
                cases={cases}
                navigateToPage={navigateToPage}
                openStudent={openStudent}
              />
            )}
            {currentPage === 'students' && (
              <StudentsPage
                studentFilters={studentFilters}
                database={database}
                filteredStudents={filteredStudents}
                openStudent={openStudent}
              />
            )}
            {currentPage === 'alerts' && (
              <AlertsPage
                studentFilters={studentFilters}
                selectedStatus={selectedStatus}
                setSelectedStatus={setSelectedStatus}
                alerts={alerts}
                openStudent={openStudent}
                findStudent={findStudent}
                findMetric={findMetric}
                canEdit={canEdit}
                setModal={setModal}
              />
            )}
            {currentPage === 'cases' && (
              <SupportCasesPage
                studentFilters={studentFilters}
                selectedStatus={selectedStatus}
                setSelectedStatus={setSelectedStatus}
                cases={cases}
                findStudent={findStudent}
                setModal={setModal}
                navigateToPage={navigateToPage}
              />
            )}
            {currentPage === 'imports' && canEdit && (
              <ImportDataPage
                api={api}
                showNotification={showNotification}
                setModal={setModal}
                selectedStatus={selectedStatus}
                setSelectedStatus={setSelectedStatus}
                database={database}
              />
            )}
            {currentPage === 'teachers' && role === 'admin' && (
              <TeacherGroupsPage
                api={api}
                token={session.token}
                groups={database.groups}
                preview={session.preview}
                groupsError={loadErrors.groups}
              />
            )}
            {currentPage === 'accounts' && role === 'admin' && (
              <AccountSyncPanel
                api={api}
                preview={session.preview}
                onSynced={() => setAccountsVersion((n) => n + 1)}
              />
            )}
            {currentPage === 'accounts' && session.preview && (
              <p>Cần đăng nhập backend để tải và quản lý tài khoản sinh viên.</p>
            )}
            {currentPage === 'accounts' && role === 'admin' && !session.preview && (
              <StudentAccountsPage
                key={accountsVersion}
                api={api}
                token={session.token}
                students={database.students}
              />
            )}
            {currentPage === 'metrics' && (
              <MetricsPage
                canEdit={canEdit}
                setModal={setModal}
                database={database}
                changeMetricStatus={changeMetricStatus}
                role={role}
              />
            )}
            {currentPage === 'detail' && selectedStudent && (
              <StudentDetailPage
                navigateToPage={navigateToPage}
                selectedStudent={selectedStudent}
                database={database}
                selectedStudentId={selectedStudentId}
                findMetric={findMetric}
                openStudent={openStudent}
                findStudent={findStudent}
                canEdit={canEdit}
                setModal={setModal}
                alerts={alerts}
                cases={cases}
              />
            )}
          </fieldset>
        </main>
      </div>
      {modal && (
        <AppDialog
          setModal={setModal}
          modal={modal}
          session={session}
          role={role}
          groups={groups}
          setSession={setSession}
          handleReviewAlert={handleReviewAlert}
          findStudent={findStudent}
          findMetric={findMetric}
          showNotification={showNotification}
          setDatabase={setDatabase}
          handleSaveMetric={handleSaveMetric}
          changeMetricStatus={changeMetricStatus}
          handleCalculateMetrics={handleCalculateMetrics}
          database={database}
          handleUploadCsv={handleUploadCsv}
          canEdit={canEdit}
          error={error}
          busy={busy}
          api={api}
          confirmImport={confirmImport}
          handleSaveFollowup={handleSaveFollowup}
        />
      )}
      {notification && (
        <div className="toast" role="status">
          <Info size={18} />
          {notification}
          <button aria-label="Ẩn thông báo" onClick={() => setNotification('')}>
            <X size={16} />
          </button>
        </div>
      )}
    </div>
  );
}
