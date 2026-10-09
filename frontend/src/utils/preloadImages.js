/**
 * Rasmlarni fonda oldindan yuklash.
 *
 * Muammo: menyuda kategoriyani almashtirganda o'sha kategoriyaning
 * rasmlari ENDI yuklana boshlardi — mijoz bir necha soniya bo'sh
 * kataklarga qarab turardi.
 *
 * Yechim: menyu ma'lumoti kelgach, BARCHA kategoriyalarning rasmlari
 * fonda sekin-asta brauzer keshiga tortiladi. Kategoriya bosilganda
 * rasm allaqachon tayyor bo'ladi va darhol chiqadi.
 *
 * Bir vaqtda hammasini tortmaymiz — aks holda birinchi ekran sekin
 * ochiladi. Shuning uchun navbat bilan, cheklangan sonda yuklanadi.
 */

const warmed = new Set();

export function preloadImages(urls, { concurrency = 3, delayMs = 150 } = {}) {
  if (typeof window === 'undefined') return () => {};

  const list = (urls || [])
    .filter((u) => typeof u === 'string' && u && !warmed.has(u));
  if (list.length === 0) return () => {};

  let cancelled = false;
  let index = 0;

  const next = () => {
    if (cancelled || index >= list.length) return;
    const url = list[index++];
    warmed.add(url);
    const img = new Image();
    // Boshqa, muhimroq so'rovlarga xalaqit bermasin.
    try {
      img.decoding = 'async';
      if ('fetchPriority' in img) img.fetchPriority = 'low';
    } catch {
      /* eski brauzer — muhim emas */
    }
    const done = () => {
      if (cancelled) return;
      window.setTimeout(next, delayMs);
    };
    img.onload = done;
    img.onerror = done;
    img.src = url;
  };

  // Birinchi ekran chizilib bo'lgach boshlaymiz.
  const start = () => {
    for (let i = 0; i < concurrency; i++) next();
  };
  if ('requestIdleCallback' in window) {
    window.requestIdleCallback(start, { timeout: 1500 });
  } else {
    window.setTimeout(start, 400);
  }

  return () => {
    cancelled = true;
  };
}

/** Kategoriyalar ro'yxatidan barcha rasm manzillarini yig'ish */
export function collectImageUrls(groups) {
  const out = [];
  (groups || []).forEach((g) => {
    (g.items || []).forEach((it) => {
      if (it && it.image_url) out.push(it.image_url);
    });
  });
  return out;
}

export default preloadImages;
