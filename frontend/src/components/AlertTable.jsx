import StatusBadge from './StatusBadge';
import { ArrowRight } from 'lucide-react';
import { formatNumber } from '../utils/format';
import Empty from './Empty';
export default function AlertTable({
  openStudent,
  findStudent,
  findMetric,
  canEdit,
  setModal,
  list,
}) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Sinh viên</th>
            <th>Chỉ số cần rà soát</th>
            <th>Giá trị / Ngưỡng</th>
            <th>Trạng thái</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {list.map((alert) => (
            <tr key={alert.id}>
              <td>
                <button
                  className="text-button"
                  onClick={() => openStudent(alert.student)}
                >
                  {findStudent(alert.student)?.name}
                </button>
                <small>
                  {alert.student} · {findStudent(alert.student)?.group}
                </small>
              </td>
              <td>{findMetric(alert.metric)?.name}</td>
              <td>
                <b className="danger-text">{formatNumber(alert.value)}</b>
                <span className="muted"> / {alert.threshold}</span>
              </td>
              <td>
                <StatusBadge status={alert.status} />
              </td>
              <td>
                {canEdit && alert.status === 'pending' ? (
                  <button
                    className="button small"
                    onClick={() =>
                      setModal({
                        type: 'review',
                        item: alert,
                        action: 'confirm',
                      })
                    }
                  >
                    Rà soát <ArrowRight size={14} />
                  </button>
                ) : (
                  <button
                    className="text-button"
                    onClick={() =>
                      setModal({
                        type: 'alert',
                        item: alert,
                      })
                    }
                  >
                    Chi tiết
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {!list.length && <Empty text="Không có cảnh báo phù hợp." />}
    </div>
  );
}
