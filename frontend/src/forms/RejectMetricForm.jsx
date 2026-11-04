export default function RejectMetricForm({ changeMetricStatus, modal, setModal }) {
  async function handleRejectMetric(event) {
    event.preventDefault();
    const note = new FormData(event.target).get('note').trim();
    if (!note) {
      return;
    }
    await changeMetricStatus(modal.item, 'rejected', note);
  }
  return (
    <form onSubmit={handleRejectMetric}>
      <label>
        Lý do từ chối *<textarea name="note" required />
      </label>
      <button className="button">Xác nhận từ chối</button>
    </form>
  );
}
