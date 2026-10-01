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
    // Qayta urinish: Wi-Fi uzilishi yoki bepul hostingdagi backend "uyqudan"
    // uyg'onishi uchun (Render free tier ~30-60 soniya ketishi mumkin).
    let lastErr = netErr;
    response = null;
    for (const delay of [800, 3000]) {
      try {
        await new Promise((r) => setTimeout(r, delay));
        response = await fetch(url, config);
        break;
      } catch (retryErr) {
        lastErr = retryErr;
      }
    }
    if (!response) {
      console.warn('Backend aloqasida uzilish:', lastErr, '| URL:', url);
      const isMixed =
        window.location.protocol === 'https:' && url.startsWith('http://');
      if (isMixed) {
        throw new Error(
          "Sayt https orqali ochilgan, lekin API manzili http:// — brauzer bunday so'rovni bloklaydi. " +
          "VITE_API_URL ni https manzilga o'zgartiring yoki saytni backend manzilidan oching."
        );
      }
      throw new Error(
        `Server bilan aloqa yo'q (${url}). Backend ishlayotganini, manzil to'g'riligini va Wi-Fi tarmog'ini tekshiring.`
      );
    }
  }

  // SPA fallback (masalan Vercel) API so'roviga HTML qaytarsa, quyidagi
  // response.json() tushunarsiz "Unexpected token '<'" xatosini beradi.
  // Shuning uchun buni alohida, aniq xabar bilan ushlaymiz.
  const contentType = response.headers.get('content-type') || '';
  if (response.ok && contentType.includes('text/html')) {
    throw new Error(
      `API manzili noto'g'ri sozlangan: ${url} manzilidan JSON o'rniga HTML sahifa qaytdi. ` +
      "Frontend backend'ga ulanmagan — VITE_API_URL ni tekshiring."
    );
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
