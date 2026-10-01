const rawApiUrl = import.meta.env.VITE_API_URL || '';
export const BASE_URL = rawApiUrl
  ? (rawApiUrl.endsWith('/api/v1') ? rawApiUrl : `${rawApiUrl.replace(/\/+$/, '')}/api/v1`)
  : '/api/v1';

async function request(endpoint, options = {}) {
  const token = localStorage.getItem('restaron_token');
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const config = {
    ...options,
    headers,
  };

  if (options.body && typeof options.body === 'object' && !(options.body instanceof FormData)) {
    config.body = JSON.stringify(options.body);
  }

  const url = endpoint.startsWith('http') ? endpoint : `${BASE_URL}${endpoint}`;
  let response;
  try {
    response = await fetch(url, config);
  } catch (netErr) {
    // 1-marta avtomatik qayta urinish (Wi-Fi yoki backend uyg'onish kechikishi uchun)
    try {
      await new Promise((r) => setTimeout(r, 600));
      response = await fetch(url, config);
    } catch (secondErr) {
      console.warn('Backend aloqasida uzilish:', secondErr);
      throw new Error("Server bilan aloqa vaqtincha uzildi. Backend (port 8000) ishlayotganini yoki Wi-Fi tarmog'ini tekshiring.");
    }
  }

  if (!response.ok) {
    let errorDetail = 'Xatolik yuz berdi';
    try {
      const errorData = await response.json();
      errorDetail = errorData.detail || errorData.message || errorDetail;
    } catch (e) {
      // not JSON
    }
    throw new Error(errorDetail);
  }

  if (response.status === 204) {
    return null;
  }

  return await response.json();
}

export const api = {
  get: (endpoint) => request(endpoint, { method: 'GET' }),
  post: (endpoint, body) => request(endpoint, { method: 'POST', body }),
  patch: (endpoint, body) => request(endpoint, { method: 'PATCH', body }),
  delete: (endpoint) => request(endpoint, { method: 'DELETE' }),
};

export default api;
