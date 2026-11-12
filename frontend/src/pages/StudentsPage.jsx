// Trang danh sách: bộ lọc ở trên, bảng sinh viên ở dưới.
import StudentTable from '../components/StudentTable';
export default function StudentsPage({
  studentFilters,
  database,
  filteredStudents,
  openStudent,
}) {
  // Sắp trên bản sao để không đổi thứ tự dữ liệu dùng ở các màn hình khác.
  const sortedStudents = [...filteredStudents].sort(
    (a, b) => Number(b.status === 'studying') - Number(a.status === 'studying'),
  );
  return (
    <>
      {studentFilters}
      <section className="panel">
        <div className="panel-head">
          <h2>
            Danh sách sinh viên{' '}
            <span className="total-pill">{filteredStudents.length}</span>
          </h2>
        </div>
        <StudentTable
          openStudent={openStudent}
          database={database}
          list={sortedStudents}
        />
      </section>
    </>
  );
}
