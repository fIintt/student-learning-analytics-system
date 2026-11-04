import { ChevronRight } from 'lucide-react';
import { navigationItems } from '../config/navigation';
export default function Sidebar({
  isMenuOpen,
  navigateToPage,
  canEdit,
  currentPage,
  pendingAlerts,
  setModal,
  role,
  session,
}) {
  return (
    <aside className={isMenuOpen ? 'sidebar mobile-open' : 'sidebar'}>
      <a
        className="brand"
        href="#"
        onClick={(event) => {
          event.preventDefault();
          navigateToPage('overview');
        }}
      >
        <img
          className="brand-logo"
          src="/images/neu-logo.png"
          alt="Logo Đại học Kinh tế Quốc dân"
        />
        <b>Nhóm 6</b>
      </a>

      <nav>
        {navigationItems
          .filter(
            (item) =>
              (item[0] !== 'imports' || canEdit) &&
              (!['accounts', 'teachers'].includes(item[0]) || role === 'admin'),
          )
          .map(([key, title, Icon]) => (
            <button
              className={currentPage === key ? 'nav-item active' : 'nav-item'}
              key={key}
              onClick={() => navigateToPage(key)}
            >
              <Icon size={19} />
              {title}
              {key === 'alerts' && pendingAlerts.length > 0 && (
                <span className="count">{pendingAlerts.length}</span>
              )}
            </button>
          ))}
      </nav>
      <div className="sidebar-bottom">
        <button
          className="account"
          onClick={() =>
            setModal({
              type: 'account',
            })
          }
        >
          <span className="avatar dark">
            {role === 'admin' ? 'QT' : role === 'reviewer' ? 'GV' : 'SV'}
          </span>
          <span>
            <strong>
              {role === 'admin'
                ? 'Quản trị viên'
                : role === 'reviewer'
                  ? 'Giáo viên rà soát'
                  : 'Sinh viên'}
            </strong>
            <small>{session.username || session.email}</small>
          </span>
          <ChevronRight size={15} />
        </button>
      </div>
    </aside>
  );
}
