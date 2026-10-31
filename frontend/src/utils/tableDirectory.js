const clean = value => String(value || '').toLocaleLowerCase().replace(/[‘’ʻʼ`]/g, "'").trim();
export const tableStatus = table => String(table.status || '').toLowerCase();
export const tableZone = table => String(table.room || '').trim();
export const NO_ZONE = '__nozone__';

export function tableDirectory(tables, zones, { query = '', zone = '', status = '' } = {}) {
  const text = clean(query).replace(/^#/, '');
  const words = text.split(/\s+/).filter(Boolean);
  const active = tables.filter(table => table.is_active !== false);
  const searched = active.filter(table => words.every(word =>
    clean(`${table.number} stol ${table.name || ''} ${tableZone(table)}`).includes(word)));
  const inZone = searched.filter(table => !zone || (zone === NO_ZONE ? !tableZone(table) : tableZone(table) === zone));
  const counts = { all: inZone.length, available: 0, occupied: 0, reserved: 0, maintenance: 0 };
  inZone.forEach(table => { const key = tableStatus(table); if (key in counts) counts[key]++; });
  const names = [...new Set([...zones.map(item => item.name.trim()), ...active.map(tableZone).filter(Boolean)])];
  const zoneOptions = names.map(name => ({ value: name, label: name, count: active.filter(table => tableZone(table) === name).length }));
  if (active.some(table => !tableZone(table))) zoneOptions.push({ value: NO_ZONE, label: 'Zonasiz', count: active.filter(table => !tableZone(table)).length });
  const matches = inZone.filter(table => !status || tableStatus(table) === status).sort((a, b) =>
    (String(b.number) === text ? 1 : 0) - (String(a.number) === text ? 1 : 0) || Number(a.number) - Number(b.number) || a.id - b.id);
  const groups = zoneOptions.map(option => ({ ...option, items: matches.filter(table =>
    option.value === NO_ZONE ? !tableZone(table) : tableZone(table) === option.value) })).filter(group => group.items.length);
  return { active, matches, groups, counts, zoneOptions };
}

// The occupied view spans all areas, but keeps the complete area navigation.
export function tablePickerDirectory(tables, zone, occupiedOnly = false) {
  const directory = tableDirectory(tables, [], { zone: occupiedOnly ? '' : zone });
  const isOccupied = table => table.is_occupied || tableStatus(table) === 'occupied';
  return {
    ...directory,
    matches: occupiedOnly ? directory.matches.filter(isOccupied) : directory.matches,
    occupiedCount: directory.active.filter(isOccupied).length,
  };
}

export function normalizeQrBaseUrl(value) {
  const url = new URL(String(value).trim());
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.search || url.hash) {
    throw new Error('http yoki https manzil kiriting. Manzilda login, parol, ? yoki # bo‘lmasin.');
  }
  return url.href.replace(/\/+$/, '');
}

export function qrAddressKind(value) {
  try {
    const host = new URL(normalizeQrBaseUrl(value)).hostname.toLowerCase();
    if (host === 'localhost' || host === '[::1]' || /^127\./.test(host)) return 'loopback';
    if (/\.trycloudflare\.com$/.test(host)) return 'temporary';
    if (/^(10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)/.test(host)) return 'local';
    return 'public';
  } catch { return 'invalid'; }
}

export function resolveQrBaseUrl(saved, lanInfo, origin) {
  const candidates = [saved, lanInfo?.public_url, lanInfo?.suggested_frontend_url, origin];
  // A previously chosen domain must survive a transient local URL during startup.
  const chosen = candidates.find(value => value && qrAddressKind(value) === 'public') ||
    candidates.find(value => value && qrAddressKind(value) !== 'invalid') || origin;
  return normalizeQrBaseUrl(chosen);
}
