import { allPages } from './api.js';

// Một API lỗi không làm mất dữ liệu từ những API khác.
export async function loadCollections(paths, options) {
  const entries = Object.entries(paths);
  const results = await Promise.allSettled(
    entries.map(([, path]) => allPages(path, options)),
  );
  const data = {};
  const errors = {};
  results.forEach((result, index) => {
    const key = entries[index][0];
    if (result.status === 'fulfilled') data[key] = result.value;
    else {
      if (result.reason.status === 401 || result.reason.name === 'AbortError')
        throw result.reason;
      data[key] = [];
      errors[key] = result.reason.message;
    }
  });
  return { data, errors };
}
