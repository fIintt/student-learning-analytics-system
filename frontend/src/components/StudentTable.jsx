import StatusBadge from './StatusBadge';
import { ArrowUpRight } from 'lucide-react';
import { formatNumber } from '../utils/format';
import Empty from './Empty';
export default function StudentTable({ openStudent, database, list }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Sinh viên</th>
            <th>Chương trình / Nhóm</th>
            <th>Trạng thái</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {list.map((student) => (
            <tr key={student.id}>
              <td>
                <button className="person" onClick={() => openStudent(student.id)}>
                  <span>
                    <strong>{student.name}</strong>
                    <small>{student.id}</small>
                  </span>
                </button>
              </td>
              <td>
                {
                  database.programs.find((program) => program.id === student.program)
                    ?.name
                }
                <small>{student.group}</small>
              </td>
              <td>
                <StatusBadge status={student.status} />
              </td>
              <td>
                <button
                  className="icon-button"
                  aria-label={'Xem ' + student.name}
                  onClick={() => openStudent(student.id)}
                >
                  <ArrowUpRight size={17} />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {!list.length && <Empty text="Không tìm thấy sinh viên phù hợp." />}
    </div>
  );
}
