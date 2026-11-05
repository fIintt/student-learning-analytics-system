import { useId, useState } from 'react';
import { Eye, EyeOff } from 'lucide-react';

export default function PasswordInput({ id, disabled, ...props }) {
  const generatedId = useId();
  const inputId = id || generatedId;
  const [visible, setVisible] = useState(false);
  const action = visible ? 'Ẩn mật khẩu' : 'Hiện mật khẩu';

  return (
    <span className="password-input">
      <input
        {...props}
        id={inputId}
        disabled={disabled}
        type={visible ? 'text' : 'password'}
      />
      <button
        type="button"
        className="password-toggle"
        disabled={disabled}
        aria-label={action}
        title={action}
        aria-controls={inputId}
        aria-pressed={visible}
        onClick={() => setVisible((old) => !old)}
      >
        {visible ? (
          <EyeOff size={19} aria-hidden="true" />
        ) : (
          <Eye size={19} aria-hidden="true" />
        )}
      </button>
    </span>
  );
}
