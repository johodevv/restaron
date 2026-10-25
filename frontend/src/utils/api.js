const rawApiUrl = import.meta.env.VITE_API_URL || '';
export const BASE_URL = rawApiUrl
  ? (rawApiUrl.endsWith('/api/v1') ? rawApiUrl : `${rawApiUrl.replace(/\/+$/, '')}/api/v1`)
  : '/api/v1';

// Maydon nomlarini o'zbekchaga o'girish (xato xabarlari uchun)
const FIELD_LABELS = {
  username: 'Login',
  password: 'Parol',
  full_name: 'To\'liq ism',
  phone: 'Telefon',
  customer_phone: 'Mijoz telefoni',
  customer_name: 'Mijoz ismi',
  name: 'Nomi',
  price: 'Narxi',
  quantity: 'Soni',
  amount: 'Summa',
  payment_amount: "To'lov summasi",
  email: 'Email',
  number: 'Raqami',
  capacity: 'Sig\'imi',
};

// Pydantic xato turlarini tushunarli matnga aylantirish
function describeValidationError(item) {
  const field = Array.isArray(item.loc)
    ? item.loc.filter((x) => x !== 'body' && x !== 'query' && typeof x === 'string').pop()
    : null;
  const label = (field && FIELD_LABELS[field]) || field || 'Maydon';
  const ctx = item.ctx || {};

  switch (item.type) {
    case 'string_too_short':
      return `${label}: kamida ${ctx.min_length} ta belgi bo'lishi kerak`;
    case 'string_too_long':
      return `${label}: ko'pi bilan ${ctx.max_length} ta belgi bo'lishi mumkin`;
    case 'missing':
      return `${label}: to'ldirilishi shart`;
    case 'greater_than':
      return `${label}: ${ctx.gt} dan katta bo'lishi kerak`;
    case 'greater_than_equal':
      return `${label}: kamida ${ctx.ge} bo'lishi kerak`;
    case 'less_than_equal':
      return `${label}: ko'pi bilan ${ctx.le} bo'lishi mumkin`;
    case 'int_parsing':
    case 'float_parsing':
      return `${label}: raqam kiritilishi kerak`;
    case 'value_error':
      return `${label}: ${item.msg || "noto'g'ri qiymat"}`;
    default:
      return `${label}: ${item.msg || "noto'g'ri qiymat"}`;
  }
}

/**
 * FastAPI xato javobini O'QILADIGAN matnga aylantiradi.
 *
 * Muhim: tekshiruv (422) xatolarida `detail` MASSIV bo'ladi. Ilgari u
 * to'g'ridan-to'g'ri `new Error()` ga berilardi va foydalanuvchi
 * "[object Object]" degan ma'nosiz xabar ko'rardi — shuning uchun
 * formalar "ishlamayapti" bo'lib tuyulardi.
 */
export function formatApiError(errorData) {
  if (!errorData) return null;
  const detail = errorData.detail ?? errorData.message;
  if (!detail) return null;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    const msgs = detail
      .map((d) => (typeof d === 'string' ? d : describeValidationError(d)))
      .filter(Boolean);
    return msgs.length ? msgs.join('\n') : null;
  }
  if (typeof detail === 'object') return detail.msg || JSON.stringify(detail);
  return String(detail);
}

async function executeFetch(url, config, timeoutMs) {
  const controller = new AbortController();
  let timedOut = false;
  const timer = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, timeoutMs);

  if (config.signal) {
    if (config.signal.aborted) {
      controller.abort();
    } else {
      config.signal.addEventListener('abort', () => controller.abort());
    }
  }

  try {
    return await fetch(url, { ...config, signal: controller.signal });
  } catch (err) {
    if (timedOut || err.name === 'AbortError') {
      const timeoutErr = new Error("Server javobi kechikdi. Natija noma'lum — hisobni yangilab tekshiring; qayta urinishda shu amal kaliti saqlanadi.");
      timeoutErr.name = 'TimeoutError';
      timeoutErr.isTimeout = true;
      throw timeoutErr;
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

async function request(endpoint, options = {}) {
  const token = localStorage.getItem('restaron_token');
  const method = (options.method || 'GET').toUpperCase();
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const isIdempotent = Boolean(
    options.idempotent ||
    (method === 'POST' && (
      endpoint.includes('/waiter-create') ||
      endpoint.includes('/add-items') ||
      endpoint.includes('/send-to-kitchen') ||
      endpoint.includes('/checkout') || endpoint === '/orders/'
    )) || (method === 'PATCH' && (endpoint.endsWith('/delta') || /^\/debts\/\d+\/pay$/.test(endpoint))) ||
    (method === 'POST' && /^\/orders\/\d+\/print-bill$/.test(endpoint))
  );

  // A new login changes jti/iat, but an unresolved operation still belongs to
  // the same user. This value only namespaces retries; the server authenticates.
  let operationUser = 'guest';
  try {
    const payload = token?.split('.')[1];
    if (payload) operationUser = String(JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/'))).sub);
  } catch (_) {}
  const operationIdentity = JSON.stringify([BASE_URL, operationUser, method, endpoint, options.body || null]);
  let pendingOperations = {};
  try { pendingOperations = JSON.parse(sessionStorage.getItem('restaron_pending_operations') || '{}'); } catch (_) {}
  const saveOperation = (key) => {
    try {
      const latest = JSON.parse(sessionStorage.getItem('restaron_pending_operations') || '{}');
      if (key) latest[operationIdentity] = key; else delete latest[operationIdentity];
      sessionStorage.setItem('restaron_pending_operations', JSON.stringify(latest));
    } catch (_) {}
  };
  if (isIdempotent && !headers['Idempotency-Key']) {
    headers['Idempotency-Key'] =
      pendingOperations[operationIdentity] || (typeof crypto !== 'undefined' && crypto.randomUUID
        ? crypto.randomUUID()
        : `idemp_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`);
  }
  if (isIdempotent) saveOperation(headers['Idempotency-Key']);

  const config = {
    ...options,
    headers,
  };

  if (options.body && typeof options.body === 'object' && !(options.body instanceof FormData)) {
    config.body = JSON.stringify(options.body);
  }

  const url = endpoint.startsWith('http') ? endpoint : `${BASE_URL}${endpoint}`;
  const isGet = method === 'GET';
  // Peak-load measurements can exceed 25s on a busy SQLite host. This is a
  // recovery window, not a performance claim: retry keeps the same saved key.
  const timeoutMs = isGet ? 15000 : (isIdempotent ? 60000 : 25000);

  let response;
  try {
    response = await executeFetch(url, config, timeoutMs);
  } catch (netErr) {
    if (netErr.isTimeout && !isIdempotent) {
      throw netErr;
    }

    if (!isGet && !isIdempotent) {
      // POST, PATCH, DELETE tarmoq xatosida avtomatik qayta yuborilmaydi (dublikat xavfi)
      throw new Error("Aloqa uzildi. Natija noma'lum — ro'yxatni yangilab tekshiring.");
    }

    // FAQAT GET uchun 2 marta qayta urinish
    let lastErr = netErr;
    response = null;
    for (const delay of [800, 3000]) {
      try {
        await new Promise((r) => setTimeout(r, delay));
        response = await executeFetch(url, config, timeoutMs);
        break;
      } catch (retryErr) {
        lastErr = retryErr;
        if (retryErr.isTimeout) {
          throw retryErr;
        }
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
    if (isIdempotent && response.status < 500) saveOperation(null);
    // 401 javobida (login so'rovidan tashqari) tokenni o'chir va restaron:unauthorized hodisasi yubor
    const isLogin = endpoint.includes('/auth/login') || endpoint.endsWith('/login');
    if (response.status === 401 && !isLogin) {
      localStorage.removeItem('restaron_token');
      window.dispatchEvent(new Event('restaron:unauthorized'));
    }

    let errorDetail = 'Xatolik yuz berdi';
    let errorData = null;
    try {
      errorData = await response.json();
      errorDetail = formatApiError(errorData) || errorDetail;
    } catch (e) {
      // JSON emas — status bo'yicha tushunarli xabar
      if (response.status === 401) errorDetail = "Sessiya tugadi. Qaytadan kiring.";
      else if (response.status === 403) errorDetail = "Bu amal uchun ruxsatingiz yo'q.";
      else if (response.status === 404) errorDetail = "Ma'lumot topilmadi.";
      else if (response.status >= 500) errorDetail = `Server xatosi (${response.status}). Qaytadan urinib ko'ring.`;
    }
    const err = new Error(errorDetail);
    err.status = response.status;
    if (errorData) {
      err.response = { status: response.status, data: errorData };
    } else {
      err.response = { status: response.status };
    }
    throw err;
  }

  if (response.status === 204) {
    if (isIdempotent) saveOperation(null);
    return null;
  }

  const result = await response.json();
  if (isIdempotent) saveOperation(null);
  return result;
}

export const api = {
  get: (endpoint, options = {}) => request(endpoint, { ...options, method: 'GET' }),
  post: (endpoint, body, options = {}) => request(endpoint, { ...options, method: 'POST', body }),
  patch: (endpoint, body, options = {}) => request(endpoint, { ...options, method: 'PATCH', body }),
  delete: (endpoint, options = {}) => request(endpoint, { ...options, method: 'DELETE' }),
};

export default api;
