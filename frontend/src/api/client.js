/**
 * API client for the Trade Intelligence Platform.
 *
 * All requests go through the Vite dev proxy (/api/* → localhost:8000)
 * in development, so no base URL is needed here.
 */

const BASE_URL = '/api';

async function request(path, options = {}) {
  const url = `${BASE_URL}${path}`;
  const config = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  };

  // FormData: let browser set Content-Type (with boundary)
  if (options.body instanceof FormData) {
    delete config.headers['Content-Type'];
  }

  const response = await fetch(url, config);

  if (!response.ok) {
    const error = new Error(`API Error: ${response.status} ${response.statusText}`);
    error.status = response.status;
    error.data = await response.json().catch(() => null);
    throw error;
  }

  return response.json();
}

export const api = {
  get: (path) => request(path, { method: 'GET' }),
  post: (path, data) => request(path, { method: 'POST', body: data instanceof FormData ? data : JSON.stringify(data) }),
  put: (path, data) => request(path, { method: 'PUT', body: JSON.stringify(data) }),
  patch: (path, data) => request(path, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (path) => request(path, { method: 'DELETE' }),
};

export default api;
