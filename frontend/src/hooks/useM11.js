import { isSessionValid } from '../services/session';
import { loadCollections } from '../services/loadCollections';
// State giao diện ở React; mọi dữ liệu nghiệp vụ được đọc/ghi qua backend.
import { useEffect, useRef, useState } from 'react';
import useLocalStorage from './useLocalStorage';
import { request, allPages } from '../services/api';
import {
  metricFromApi,
  resultFromApi,
  alertFromApi,
  caseFromApi,
} from '../services/backendData';
import { navigationItems } from '../config/navigation';
import downloadCsv from '../utils/downloadCsv';

const emptyDatabase = () => ({
  students: [],
  programs: [],
  groups: [],
  metrics: [],
  results: [],
  alerts: [],
  cases: [],
  batches: [],
});

export default function useM11() {
  const [savedSession, saveSession] = useLocalStorage('m11-api-session', null);
  // Phiên xem giao diện chỉ ở bộ nhớ, không tạo token hoặc đổi phiên API đã lưu.
  const [previewSession, setPreviewSession] = useState(null);
  const session = previewSession || savedSession;
  const [database, setDatabase] = useState(emptyDatabase);
  const [currentPage, setCurrentPage] = useState('overview');
  const [selectedStudentId, setSelectedStudentId] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedGroup, setSelectedGroup] = useState('all');
  const [selectedProgram, setSelectedProgram] = useState('all');
  const [selectedStatus, setSelectedStatus] = useState('all');
  const [modal, saveModal] = useState(null);
  const [notification, setNotification] = useState('');
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [loadErrors, setLoadErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const actionLock = useRef(false);
  const modalVersion = useRef(0);
  const currentToken = useRef(session?.token);
  currentToken.current = session?.token;
  const role = session?.role;
  const canEdit = role === 'admin' || role === 'reviewer';

  function showNotification(text) {
    setNotification(text);
  }
  function enterPreview() {
    setPreviewSession({
      preview: true,
      role: 'admin',
      email: 'Chưa đăng nhập API',
    });
    setDatabase(emptyDatabase());
    setError('');
    setLoadErrors({});
    setLoading(false);
    setCurrentPage('overview');
  }
  function setSession(value) {
    setPreviewSession(null);
    modalVersion.current++;
    currentToken.current = value?.token;
    saveSession(value);
    setLoadErrors({});
    setLoading(false);
    setDatabase(emptyDatabase());
    saveModal(null);
    setError('');
    setSelectedStudentId(null);
    setSearchQuery('');
    setSelectedStatus('all');
    setIsMenuOpen(false);
    setSelectedGroup('all');
    setSelectedProgram('all');
    setCurrentPage('overview');
  }
  function onError(err) {
    if (session?.preview) return showNotification(err.message);
    if (err.status === 401) setSession(null);
    setError(err.message);
  }
  async function api(path, options = {}) {
    if (session?.preview)
      throw new Error(
        'Cần đăng nhập backend thật để dùng chức năng này. Bạn vẫn có thể xem và chỉnh giao diện.',
      );
    try {
      return await request(path, { token: session?.token, ...options });
    } catch (err) {
      if (err.status === 401) setSession(null);
      throw err;
    }
  }
  function navigateToPage(page) {
    setCurrentPage(page);
    setSearchQuery('');
    setSelectedStatus('all');
    setSelectedStudentId(null);
    setIsMenuOpen(false);
  }

  async function refresh(signal) {
    if (!session?.token || session.preview) return;
    setLoading(true);
    setError('');
    const options = { token: session.token, signal };
    try {
      const me = await request('/auth/me', options);
      if (signal?.aborted || currentToken.current !== session.token) return;
      saveSession((old) => (old?.token === session.token ? { ...old, ...me } : old));
      if (me.must_change_password || me.role === 'viewer') {
        if (!signal?.aborted) setDatabase(emptyDatabase());
        return;
      }
      const { data, errors } = await loadCollections(
        {
          students: '/learners',
          programs: '/programs',
          groups: '/groups',
          metrics: '/metric-definitions',
          results: '/metrics/results',
          alerts: '/review/alerts',
          cases: '/support-cases',
          batches: '/academic-imports',
        },
        options,
      );
      const { students, programs, groups, metrics, results, alerts, cases, batches } =
        data;
      if (!signal?.aborted && currentToken.current === session.token)
        setLoadErrors(errors);
      if (signal?.aborted || currentToken.current !== session.token) return;
      setDatabase({
        students: students.map((student) => ({
          ...student,
          name: student.full_name,
          program: student.program_id,
          status: student.academic_status,
          group:
            groups.find(
              (group) =>
                group.program_id === student.program_id &&
                group.cohort === student.cohort,
            )?.name || 'Chưa có nhóm',
        })),
        programs,
        groups,
        metrics: metrics.map(metricFromApi),
        results: results.map(resultFromApi),
        alerts: alerts.map(alertFromApi),
        cases: cases.map(caseFromApi),
        batches,
      });
    } catch (err) {
      if (err.name !== 'AbortError' && !signal?.aborted) onError(err);
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }
  useEffect(() => {
    if (!session?.token || session.preview) return;
    if (!isSessionValid(session)) {
      setSession(null);
      return;
    }
    const controller = new AbortController();
    refresh(controller.signal);
    const timer = setTimeout(
      () => setSession(null),
      Math.max(0, session.expires - Date.now()),
    );
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [session?.token]);

  // Chặn gửi hai lần. Lỗi ghi không tự retry vì có thể tạo bản ghi trùng.
  async function perform(action, success) {
    if (actionLock.current) return;
    actionLock.current = true;
    setBusy(true);
    setError('');
    try {
      await action();
      saveModal(null);
      if (success) showNotification(success);
      await refresh();
    } catch (err) {
      onError(err);
    } finally {
      actionLock.current = false;
      setBusy(false);
    }
  }

  async function setModal(value) {
    if (actionLock.current) return;
    const version = ++modalVersion.current;
    saveModal(value);
    if (value?.type === 'review' && value.assignees) return;
    if (!value || !['review', 'case', 'batch'].includes(value.type)) return;
    saveModal({ ...value, loading: true });
    try {
      const id = value.item.id;
      let extra = {};
      if (value.type === 'review') {
        extra.assignees = await allPages(
          `/support-cases/assignees?learner_id=${encodeURIComponent(value.item.student)}`,
          { token: session.token },
        );
      } else if (value.type === 'case') {
        const [detail, assignees] = await Promise.all([
          api(`/support-cases/${id}`),
          allPages(
            `/support-cases/assignees?learner_id=${encodeURIComponent(value.item.student)}`,
            { token: session.token },
          ),
        ]);
        extra = { item: caseFromApi(detail), assignees };
      } else {
        const [detail, issues] = await Promise.all([
          api(`/academic-imports/${id}`),
          allPages(`/academic-imports/${id}/errors`, { token: session.token }),
        ]);
        extra = { item: detail, issues };
      }
      if (modalVersion.current === version)
        saveModal({ ...value, ...extra, loading: false });
    } catch (err) {
      if (modalVersion.current === version)
        saveModal({ ...value, loading: false, error: err.message });
      onError(err);
    }
  }

  // Import chạy nền: chỉ poll các job còn đang chạy, không tự confirm/compute.
  useEffect(() => {
    const running = database.batches.some((job) =>
      ['processing', 'importing'].includes(job.status),
    );
    if (!running || !session?.token) return;
    const timer = setTimeout(async () => {
      try {
        const batches = await allPages('/academic-imports', {
          token: session.token,
        });
        setDatabase((old) => ({ ...old, batches }));
        if (
          modal?.type === 'batch' &&
          ['processing', 'importing'].includes(modal.item.status)
        )
          setModal(modal);
      } catch (err) {
        if (err.status === 401) onError(err);
        else setLoadErrors((old) => ({ ...old, batches: err.message }));
      }
    }, 2000);
    return () => clearTimeout(timer);
  }, [database.batches, session?.token, modal?.item?.status]);

  const accessibleStudents = database.students;
  const filteredStudents = accessibleStudents.filter(
    (student) =>
      (selectedGroup === 'all' || student.group === selectedGroup) &&
      (selectedProgram === 'all' || student.program === selectedProgram) &&
      `${student.id} ${student.name}`.toLowerCase().includes(searchQuery.toLowerCase()),
  );
  const ids = new Set(filteredStudents.map((student) => student.id));
  const alerts = database.alerts.filter((alert) => ids.has(alert.student));
  const cases = database.cases.filter((item) => ids.has(item.student));
  const pendingAlerts = alerts.filter((alert) => alert.status === 'pending');
  const findStudent = (id) => database.students.find((item) => item.id === id);
  const findMetric = (id) =>
    database.metrics.find(
      (item) => item.id === id || `${item.code}@${item.version}` === id,
    );
  function openStudent(id) {
    setSelectedStudentId(id);
    setCurrentPage('detail');
  }

  async function handleReviewAlert(event) {
    event.preventDefault();
    const data = new FormData(event.target);
    const { item, action } = modal;
    const body = { note: data.get('note').trim() };
    if (action === 'confirm') {
      body.reason = data.get('reason').trim();
      body.assigned_to = data.get('owner') ? Number(data.get('owner')) : null;
    }
    await perform(
      () => api(`/review/alerts/${item.id}/${action}`, { method: 'POST', body }),
      action === 'confirm' ? 'Đã xác nhận và mở hồ sơ hỗ trợ.' : 'Đã bác cảnh báo.',
    );
  }
  async function handleSaveMetric(event) {
    event.preventDefault();
    const data = new FormData(event.target);
    const type = modal.item?.type || data.get('type');
    const threshold = Number(data.get('threshold'));
    const terms = Number(data.get('terms'));
    if (!Number.isFinite(threshold) || !Number.isInteger(terms) || terms < 1)
      return showNotification('Ngưỡng hoặc số học kỳ không hợp lệ.');
    const body = {
      name: data.get('name').trim(),
      purpose: data.get('purpose').trim(),
      formula_params: type === 'cumulative_gpa' ? {} : { terms },
      threshold: { operator: data.get('operator'), value: threshold },
    };
    let path = '/metric-definitions';
    let method = 'POST';
    if (modal.type === 'editMetric') {
      path += `/${modal.item.id}`;
      method = 'PATCH';
    } else if (modal.item) path += `/${modal.item.id}/new-version`;
    else {
      body.code = data.get('code').trim();
      body.formula_type = type;
    }
    await perform(() => api(path, { method, body }), 'Đã lưu bản nháp.');
  }
  async function changeMetricStatus(metric, status, note = '') {
    const action = {
      submitted: 'submit',
      approved: 'approve',
      rejected: 'reject',
    }[status];
    await perform(
      () =>
        api(`/metric-definitions/${metric.id}/${action}`, {
          method: 'POST',
          body: action === 'submit' ? undefined : { note },
        }),
      'Đã cập nhật công thức.',
    );
  }
  async function handleCalculateMetrics(event) {
    event.preventDefault();
    const id = Number(new FormData(event.target).get('metric'));
    await perform(async () => {
      const result = await api('/metrics/compute', {
        method: 'POST',
        body: { metric_definition_id: id },
      });
      showNotification(
        `Đã tính ${result.learners_computed} sinh viên; tạo ${result.alerts_created} cảnh báo.`,
      );
    });
  }
  async function handleUploadCsv(event) {
    event.preventDefault();
    const data = new FormData(event.target);
    const file = data.get('file');
    if (file.size > 10 * 1024 * 1024)
      return showNotification('File vượt giới hạn 10 MiB mặc định.');
    await perform(
      () => api('/academic-imports', { method: 'POST', body: data }),
      'Đã tải file. Chờ xem trước trong lịch sử nhập.',
    );
  }
  async function confirmImport(id) {
    await perform(
      () => api(`/academic-imports/${id}/confirm`, { method: 'POST' }),
      'Đang nhập dữ liệu. Theo dõi trạng thái trong lịch sử.',
    );
  }
  async function handleSaveFollowup(event) {
    event.preventDefault();
    const data = new FormData(event.target);
    const item = modal.item;
    // Ghi followup trước, PATCH sau. Giữ ID để retry PATCH mà không tạo followup lần hai.
    await perform(async () => {
      let followupId = modal.savedFollowupId;
      if (!followupId) {
        let result;
        try {
          result = await api('/followups', {
            method: 'POST',
            body: {
              case_id: item.id,
              action: data.get('action').trim(),
              outcome: data.get('result') || null,
              result_status: data.get('assessment'),
              post_metric_result_id: data.get('measurement')
                ? Number(data.get('measurement'))
                : null,
            },
          });
        } catch (err) {
          if (!err.status) {
            saveModal((old) => ({ ...old, uncertain: true }));
            throw new Error(
              'Chưa xác định lần theo dõi đã được lưu hay chưa. Đóng rồi mở lại hồ sơ để đối chiếu lịch sử trước khi thử lại.',
            );
          }
          throw err;
        }
        followupId = result.id;
        saveModal((old) => ({ ...old, savedFollowupId: followupId }));
      }
      try {
        await api(`/support-cases/${item.id}`, {
          method: 'PATCH',
          body: {
            status: data.get('status'),
            assigned_to: data.get('owner') ? Number(data.get('owner')) : null,
          },
        });
      } catch (err) {
        if (err.status === 409) {
          const latest = await api(`/support-cases/${item.id}`);
          saveModal((old) => ({
            ...old,
            item: caseFromApi(latest),
            savedFollowupId: followupId,
          }));
        }
        throw new Error(
          `Đã lưu theo dõi #${followupId}, chưa cập nhật hồ sơ: ${err.message}. Chỉ thử lại cập nhật hồ sơ.`,
        );
      }
    }, 'Đã lưu theo dõi và cập nhật hồ sơ.');
  }
  function handleExportReport() {
    if (['students', 'alerts', 'cases'].some((key) => loadErrors[key]))
      return showNotification('Chưa tải đủ dữ liệu để xuất báo cáo. Hãy tải lại.');
    downloadCsv('m11-bao-cao.csv', [
      ['Mã sinh viên', 'Họ tên', 'Chương trình', 'Khóa', 'Cảnh báo', 'Hồ sơ hỗ trợ'],
      ...filteredStudents.map((student) => [
        student.id,
        student.name,
        student.program,
        student.cohort,
        alerts.filter((item) => item.student === student.id).length,
        cases.filter((item) => item.student === student.id).length,
      ]),
    ]);
  }
  const groups = database.groups.map((item) => item.name);
  const activePage = navigationItems.find((item) => item[0] === currentPage);
  const selectedStudent = findStudent(selectedStudentId);
  return {
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
    handleCalculateMetrics,
    handleUploadCsv,
    handleSaveFollowup,
    handleExportReport,
    groups,
    activePage,
    selectedStudent,
    loadErrors,
    loading,
    busy,
    error,
    refresh,
    confirmImport,
    api,
  };
}
