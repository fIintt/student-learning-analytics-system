// Thẻ thống kê chỉ hiển thị tên và giá trị.
export default function StatCard({ title, value }) {
  return (
    <section className="stat">
      <div>
        <span>{title}</span>
      </div>
      <strong>{value}</strong>
    </section>
  );
}
