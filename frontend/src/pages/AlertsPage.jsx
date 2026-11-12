// Lọc cảnh báo theo trạng thái và hiển thị bảng rà soát.
import AlertTable from '../components/AlertTable';
export default function AlertsPage({
  studentFilters,
  selectedStatus,
  setSelectedStatus,
  alerts,
  openStudent,
  findStudent,
  findMetric,
  canEdit,
  setModal,
}) {
  return (
    <>
      {studentFilters}
      <div className="tabs">
        {[
          ['all', 'Tất cả'],
          ['pending', 'Chờ rà soát'],
          ['confirmed', 'Đã xác nhận'],
          ['dismissed', 'Đã bác'],
          ['superseded', 'Đã được thay thế'],
        ].map(([value, title]) => (
          <button
            key={value}
            className={selectedStatus === value ? 'selected' : ''}
            onClick={() => setSelectedStatus(value)}
          >
            {title}
            <span>
              {alerts.filter((alert) => value === 'all' || alert.status === value).length}
            </span>
          </button>
        ))}
      </div>
      <section className="panel">
        <AlertTable
          openStudent={openStudent}
          findStudent={findStudent}
          findMetric={findMetric}
          canEdit={canEdit}
          setModal={setModal}
          list={alerts.filter(
            (alert) => selectedStatus === 'all' || alert.status === selectedStatus,
          )}
        />
      </section>
    </>
  );
}
