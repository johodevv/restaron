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
      errorDetail = formatApiError(errorData) || errorDetail;
    } catch (e) {
      // JSON emas — status bo'yicha tushunarli xabar
      if (response.status === 401) errorDetail = "Sessiya tugadi. Qaytadan kiring.";
      else if (response.status === 403) errorDetail = "Bu amal uchun ruxsatingiz yo'q.";
      else if (response.status === 404) errorDetail = "Ma'lumot topilmadi.";
      else if (response.status >= 500) errorDetail = `Server xatosi (${response.status}). Qaytadan urinib ko'ring.`;
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
