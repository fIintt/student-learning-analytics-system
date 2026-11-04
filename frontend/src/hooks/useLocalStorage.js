import { useState } from 'react';

// Giống useState, nhưng lưu thêm dữ liệu vào trình duyệt.
// initialValue có thể là dữ liệu hoặc hàm tạo dữ liệu ban đầu.
export default function useLocalStorage(key, initialValue) {
  function readSavedValue() {
    try {
      const savedValue = localStorage.getItem(key);
      if (savedValue !== null) {
        return JSON.parse(savedValue);
      }
    } catch {
      // Nếu dữ liệu cũ bị hỏng, dùng lại dữ liệu ban đầu.
    }
    if (typeof initialValue === 'function') {
      return initialValue();
    }
    return initialValue;
  }

  const [value, setValue] = useState(readSavedValue);

  function saveValue(nextValueOrFunction) {
    setValue((currentValue) => {
      let nextValue = nextValueOrFunction;
      // React cho phép cập nhật bằng hàm nhận giá trị hiện tại.
      if (typeof nextValueOrFunction === 'function') {
        nextValue = nextValueOrFunction(currentValue);
      }
      localStorage.setItem(key, JSON.stringify(nextValue));
      return nextValue;
    });
  }

  return [value, saveValue];
}
