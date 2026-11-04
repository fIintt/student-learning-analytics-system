// Danh sách trường hợp hỗ trợ đã được giáo viên xác nhận.
import StatusBadge from '../components/StatusBadge';
import { ArrowUpRight } from 'lucide-react';
import '../utils/format';
import Empty from '../components/Empty';
export default function SupportCasesPage({
  studentFilters,
  selectedStatus,
  setSelectedStatus,
  cases,
  findStudent,
  setModal,
  navigateToPage,
}) {
  return (
    <>
      {studentFilters}
      <div className="tabs">
        {[
          ['all', 'Tất cả'],
          ['open', 'Mở'],
          ['in_progress', 'Đang xử lý'],
          ['closed', 'Đã đóng'],
        ].map(([value, title]) => (
          <button
            key={value}
            className={selectedStatus === value ? 'selected' : ''}
            onClick={() => setSelectedStatus(value)}
          >
            {title}
          </button>
        ))}
      </div>
      <div className="case-grid">
        {cases
          .filter(
            (supportCase) =>
              selectedStatus === 'all' || supportCase.status === selectedStatus,
          )
          .map((supportCase) => (
            <section className="panel case-card" key={supportCase.id}>
              <div className="case-top">
                <span className="muted">HS-{String(supportCase.id).slice(-5)}</span>
                <StatusBadge status={supportCase.status} />
              </div>
              <h2>{findStudent(supportCase.student)?.name}</h2>
              <small>
                {supportCase.student} · {findStudent(supportCase.student)?.group}
              </small>
              <p>{supportCase.reason}</p>
              <div className="case-meta">
                Phụ trách: {supportCase.owner}
                <br />
                {supportCase.followup_count ?? supportCase.followups.length} lần theo dõi
              </div>
              <button
                className="button secondary"
                onClick={() =>
                  setModal({
                    type: 'case',
                    item: supportCase,
                  })
                }
              >
                Xem và theo dõi <ArrowUpRight size={15} />
              </button>
            </section>
          ))}
      </div>
      {!cases.length && (
        <section className="panel">
          <Empty
            text="Chưa có trường hợp hỗ trợ. Xác nhận một cảnh báo để bắt đầu đồng hành cùng sinh viên."
            action={() => navigateToPage('alerts')}
            label="Đến hàng chờ rà soát"
          />
        </section>
      )}
    </>
  );
}
