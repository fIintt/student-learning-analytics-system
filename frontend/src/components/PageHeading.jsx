import { Plus, Upload, Download } from 'lucide-react';
export default function PageHeading({
  currentPage,
  activePage,
  handleExportReport,
  canEdit,
  setModal,
}) {
  return (
    <div className="page-heading">
      <div>
        <h1>
          {currentPage === 'overview'
            ? 'Tổng quan học tập'
            : activePage?.[1] || 'Hồ sơ sinh viên'}
        </h1>
      </div>
      <div className="heading-actions">
        {currentPage === 'overview' || currentPage === 'students' ? (
          <button className="button secondary" onClick={handleExportReport}>
            <Download size={16} />
            Xuất báo cáo
          </button>
        ) : currentPage === 'metrics' && canEdit ? (
          <button
            className="button"
            onClick={() =>
              setModal({
                type: 'metric',
              })
            }
          >
            <Plus size={16} />
            Tạo công thức
          </button>
        ) : currentPage === 'imports' && canEdit ? (
          <button
            className="button"
            onClick={() =>
              setModal({
                type: 'upload',
              })
            }
          >
            <Upload size={16} />
            Nhập dữ liệu
          </button>
        ) : null}
      </div>
    </div>
  );
}
