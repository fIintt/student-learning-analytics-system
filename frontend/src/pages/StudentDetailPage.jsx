// Thông tin, lịch sử chỉ số, cảnh báo và hỗ trợ của một sinh viên.
import StatusBadge from '../components/StatusBadge';
import { HeartHandshake, ChevronRight } from 'lucide-react';
import { formatNumber } from '../utils/format';
import AlertTable from '../components/AlertTable';
import Empty from '../components/Empty';
export default function StudentDetailPage({
  navigateToPage,
  selectedStudent,
  database,
  selectedStudentId,
  findMetric,
  openStudent,
  findStudent,
  canEdit,
  setModal,
  alerts,
  cases,
}) {
  return (
    <>
      <button className="text-button back" onClick={() => navigateToPage('students')}>
        ← Danh sách sinh viên
      </button>
      <section className="panel profile">
        <span className="avatar large">
          {selectedStudent.name
            .split(' ')
            .slice(-2)
            .map((index) => index[0])
            .join('')}
        </span>
        <div>
          <h2>{selectedStudent.name}</h2>
          <p>
            {selectedStudent.id} ·{' '}
            {
              database.programs.find((program) => program.id === selectedStudent.program)
                ?.name
            }
          </p>
          <span>
            Khóa {selectedStudent.cohort} · Nhóm {selectedStudent.group}
          </span>
        </div>
        <StatusBadge status={selectedStudent.status} />
      </section>
      <section className="panel">
        <div className="panel-head">
          <h2>Lịch sử chỉ số</h2>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Chỉ số / Phiên bản</th>
                <th>Giá trị</th>
                <th>Năm học / Học kỳ</th>
                <th>Thời điểm tính</th>
                <th>Kết quả</th>
              </tr>
            </thead>
            <tbody>
              {database.results
                .filter((row) => row.student === selectedStudentId)
                .map((row) => (
                  <tr key={row.id}>
                    <td>
                      {findMetric(row.metric)?.name}
                      <small>v{row.version}</small>
                    </td>
                    <td>{formatNumber(row.value)}</td>
                    <td>{row.term}</td>
                    <td>{new Date(row.date).toLocaleString('vi-VN')}</td>
                    <td>
                      <span className={'badge ' + (row.flag ? 'pending' : 'approved')}>
                        {row.value == null
                          ? 'Chưa có giá trị'
                          : row.flag
                            ? 'Vượt ngưỡng'
                            : 'Trong ngưỡng'}
                      </span>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </section>
      <section className="panel">
        <div className="panel-head">
          <h2>Cảnh báo và rà soát</h2>
        </div>
        <AlertTable
          openStudent={openStudent}
          findStudent={findStudent}
          findMetric={findMetric}
          canEdit={canEdit}
          setModal={setModal}
          list={alerts.filter((alert) => alert.student === selectedStudentId)}
        />
      </section>
      <section className="panel">
        <div className="panel-head">
          <h2>Hành trình hỗ trợ</h2>
        </div>
        {cases
          .filter((supportCase) => supportCase.student === selectedStudentId)
          .map((supportCase) => (
            <button
              className="support-row"
              key={supportCase.id}
              onClick={() =>
                setModal({
                  type: 'case',
                  item: supportCase,
                })
              }
            >
              <HeartHandshake size={20} />
              <span>
                {supportCase.reason}
                <small>
                  {supportCase.followup_count ?? supportCase.followups.length} lần theo
                  dõi · {supportCase.owner}
                </small>
              </span>
              <StatusBadge status={supportCase.status} />
              <ChevronRight size={17} />
            </button>
          ))}
        {!cases.some((supportCase) => supportCase.student === selectedStudentId) && (
          <Empty text="Chưa có trường hợp hỗ trợ." />
        )}
      </section>
    </>
  );
}
