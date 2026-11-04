import { FileText } from 'lucide-react';
export default function Empty({ text, action, label }) {
  return (
    <div className="empty">
      <FileText size={30} />
      <p>{text}</p>
      {action && (
        <button className="button secondary" onClick={action}>
          {label}
        </button>
      )}
    </div>
  );
}
