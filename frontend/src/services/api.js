// Mọi request dùng chung URL, Bearer token và cách đọc lỗi.
export const API_URL = (
  import.meta.env?.VITE_API_URL || 'http://127.0.0.1:8000/api/v1'
).replace(/\/$/, '');

export async function request(
  path,
  { token, method = 'GET', body, signal, blob = false } = {},
) {
  const headers = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body && !(body instanceof FormData)) headers['Content-Type'] = 'application/json';
  let response;
  try {
    response = await fetch(API_URL + path, {
      method,
      headers,
      signal,
      body: body instanceof FormData ? body : body ? JSON.stringify(body) : undefined,
    });
  } catch (error) {
    if (error.name === 'AbortError') throw error;
    throw new Error('Không kết nối được backend. Kiểm tra server và VITE_API_URL.');
  }
  if (response.ok && blob) return response.blob();
  const text = await response.text();
  let data;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = null;
  }
  if (!response.ok) {
    const detail = data?.detail ?? data?.message ?? data?.error?.message;
    const message =
      typeof detail === 'string'
        ? detail
        : Array.isArray(detail)
          ? detail
              .map((item) => item.msg || item.message || JSON.stringify(item))
              .join('; ')
          : `Yêu cầu thất bại (${response.status}).`;
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }
  return data;
}

// API phân trang: lấy đủ trang trước khi lọc hoặc thống kê toàn phạm vi.
export async function allPages(path, options = {}) {
  const items = [];
  for (let page = 1; ; page++) {
    const separator = path.includes('?') ? '&' : '?';
    const data = await request(`${path}${separator}page=${page}&size=200`, options);
    if (!Array.isArray(data?.items))
      throw new Error('API trả danh sách không đúng cấu trúc.');
    items.push(...data.items);
    if (items.length >= data.total) {
      // Các trang có thể dịch chuyển khi dữ liệu đổi: loại bản ghi lặp theo khóa.
      const unique = new Map();
      for (const item of items) {
        const key =
          item.id ??
          (item.academic_year != null
            ? `${item.academic_year}:${item.semester}`
            : JSON.stringify(item));
        unique.set(key, item);
      }
      return [...unique.values()];
    }
    if (!data.items.length) throw new Error('Phân trang API không đầy đủ. Hãy tải lại.');
  }
}

export function saveDownload(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
