import { Bell, Menu } from "lucide-react";
export default function Topbar({
  setIsMenuOpen,
  isMenuOpen,
  activePage,
  navigateToPage,
  pendingAlerts,
  role,
  preview,
}) {
  return (
    <header className="topbar">
      <div>
        <button
          className="icon-button mobile-toggle"
          aria-label="Mở menu"
          onClick={() => setIsMenuOpen(!isMenuOpen)}
        >
          <Menu size={20} />
        </button>

        <b>{activePage?.[1] || "Chi tiết sinh viên"}</b>
      </div>
      <div>
        <span className="demo-dot" />{" "}
        <span className="demo-label">
          {preview ? "Xem giao diện tạm" : "API backend"}
        </span>
        <span className="divider" />
        <button
          className="icon-button notification"
          aria-label="Cảnh báo chờ rà soát"
          onClick={() => navigateToPage("alerts")}
        >
          <Bell size={19} />
          {pendingAlerts.length > 0 && <i />}
        </button>
        <span className="avatar mini">{role === "admin" ? "QT" : "GV"}</span>
      </div>
    </header>
  );
}
