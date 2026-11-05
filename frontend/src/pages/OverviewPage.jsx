import StatusCharts from '../components/StatusCharts';
import StatCard from '../components/StatCard';
import StudentTable from '../components/StudentTable';
import { dashboardData } from '../utils/dashboardData';
export default function OverviewPage({
  loadErrors = {},
  studentFilters,
  database,
  filteredStudents: studentsInFilter,
  cases: allCases,
  navigateToPage,
  openStudent,
}) {
  // Dashboard theo dõi sinh viên đang học; hồ sơ khác vẫn có ở trang Sinh viên.
  const {
    students: filteredStudents,
    alerts: scopedAlerts,
    pendingAlerts,
    cases,
    openCases,
  } = dashboardData(studentsInFilter, database.alerts, allCases);
  const attention = new Set(pendingAlerts.map((item) => item.student));
  return (
    <>
      {studentFilters}
      <div className="stats">
        <StatCard
          title="Sinh viên đang học"
          value={loadErrors.students ? '—' : filteredStudents.length}
        />
        <StatCard
          title="Cảnh báo chờ rà soát"
          value={loadErrors.alerts || loadErrors.students ? '—' : pendingAlerts.length}
        />
        <StatCard
          title="Hồ sơ hỗ trợ chưa đóng"
          value={loadErrors.cases || loadErrors.students ? '—' : openCases.length}
        />
        <StatCard
          title="Sinh viên chờ rà soát"
          value={loadErrors.alerts || loadErrors.students ? '—' : attention.size}
        />
      </div>
      <StatusCharts
        alerts={scopedAlerts}
        cases={cases}
        metrics={database.metrics}
        loadErrors={loadErrors}
      />
      <section className="panel">
        <div className="panel-head">
          <h2>Sinh viên chờ rà soát</h2>
          <button className="text-button" onClick={() => navigateToPage('alerts')}>
            Xem cảnh báo
          </button>
        </div>
        <StudentTable
          database={database}
          list={filteredStudents.filter((item) => attention.has(item.id))}
          openStudent={openStudent}
        />
      </section>
    </>
  );
}
