import { createRoot } from 'react-dom/client';
import App from './App';
import './style.css';

// Điểm bắt đầu: gắn ứng dụng React vào thẻ #root trong index.html.
createRoot(document.getElementById('root')).render(<App />);
