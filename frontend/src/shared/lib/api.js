const API_BASE = import.meta.env.VITE_API_BASE || '/api';

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const response = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!response.ok) {
    response.clone().json().then(body => console.error('API error details:', body)).catch(() => {});
    const error = new Error(`API error: ${response.status}`);
    error.status = response.status;
    throw error;
  }
  return response.json();
}

export const api = {
  get: (endpoint, { params = {}, signal } = {}) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value != null && value !== '') query.append(key, value);
    });
    const qs = query.toString();
    return request(qs ? `${endpoint}?${qs}` : endpoint, { signal });
  },
};
