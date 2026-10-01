import React, { createContext, useContext, useState, useEffect } from 'react';

// Lotin alifbosidan Kirill alifbosiga avtomatik o'girish (O'zbekcha)
export const latinToCyrillic = (text) => {
  if (!text || typeof text !== 'string') return text || '';

  let res = text;

  // Murakkab harflar (2 ta harfli)
  const map2 = [
    { l: "o'", c: 'ў' },
    { l: "O'", c: 'Ў' },
    { l: "g'", c: 'ғ' },
    { l: "G'", c: 'Ғ' },
    { l: 'sh', c: 'ш' },
    { l: 'Sh', c: 'Ш' },
    { l: 'SH', c: 'Ш' },
    { l: 'ch', c: 'ч' },
    { l: 'Ch', c: 'Ч' },
    { l: 'CH', c: 'Ч' },
    { l: 'yo', c: 'ё' },
    { l: 'Yo', c: 'Ё' },
    { l: 'YO', c: 'Ё' },
    { l: 'yu', c: 'ю' },
    { l: 'Yu', c: 'Ю' },
    { l: 'YU', c: 'Ю' },
    { l: 'ya', c: 'я' },
    { l: 'Ya', c: 'Я' },
    { l: 'YA', c: 'Я' },
    { l: 'ye', c: 'е' },
    { l: 'Ye', c: 'Е' },
    { l: 'YE', c: 'Е' },
  ];

  map2.forEach(({ l, c }) => {
    res = res.replaceAll(l, c);
  });

  // Yagona harflar
  const map1 = {
    a: 'а', A: 'А',
    b: 'б', B: 'Б',
    d: 'д', D: 'Д',
    e: 'э', E: 'Э',
    f: 'ф', F: 'Ф',
    g: 'г', G: 'Г',
    h: 'ҳ', H: 'Ҳ',
    i: 'и', I: 'И',
    j: 'ж', J: 'Ж',
    k: 'к', K: 'К',
    l: 'л', L: 'Л',
    m: 'м', M: 'М',
    n: 'н', N: 'Н',
    o: 'о', O: 'О',
    p: 'п', P: 'П',
    q: 'қ', Q: 'Қ',
    r: 'р', R: 'Р',
    s: 'с', S: 'С',
    t: 'т', T: 'Т',
    u: 'у', U: 'У',
    v: 'в', V: 'В',
    x: 'х', X: 'Х',
    y: 'й', Y: 'Й',
    z: 'з', Z: 'З',
  };

  return res.split('').map((char) => map1[char] || char).join('');
};

// 4 xil til lug'ati: uz (Lotin), oz (Kirill - Салом), ru (Русский), en (English)
const translations = {
  uz: {
    welcome: 'Xush kelibsiz!',
    hello: 'Salom',
    menu: 'Menyu',
    order: 'Buyurtma',
    cart: 'Savat',
    table: 'Stol',
    waiter: 'Ofitsiant',
    callWaiter: 'Ofitsiantni chaqirish',
    bill: 'Hisob cheki',
    total: 'Jami',
    subtotal: 'Oraliq hisob',
    serviceFee: 'Xizmat haqi',
    discount: 'Chegirma',
    pay: "To'lov",
    cash: 'Naqd',
    card: 'Karta',
    click: 'Click / Payme',
    debt: 'Nasiya (Qarz)',
    ready: 'Tayyor',
    preparing: 'Tayyorlanmoqda',
    delivered: 'Yetkazib berildi',
    pending: 'Kutilmoqda',
    searchFood: 'Taomlarni qidirish...',
    addToCart: "Savatga qo'shish",
    viewCart: "Savatni ko'rish",
    emptyCart: "Savatchangiz bo'sh",
    sendToKitchen: 'Oshxonaga yuborish',
    checkout: "To'lov / Hisob",
    settings: 'Sozlamalar',
    language: 'Til',
    kitchen1: '1-Oshxona (Qozon taomlari)',
    kitchen2: '2-Oshxona (Baliq / Somsa)',
    bar: 'Bar / Ichimliklar',
    printerCustomer: '1-Printer (Mijoz kassa cheki)',
    printerKitchen1: '2-Printer (1-Oshxona: Qozon)',
    printerKitchen2: '3-Printer (2-Oshxona: Baliq/Somsa)',
    testPrint: 'Test chop etish',
    save: 'Saqlash',
    close: 'Yopish',
    reviews: 'Fikr va izohlar',
  },
  oz: {
    welcome: 'Хуш келибсиз!',
    hello: 'Салом',
    menu: 'Меню',
    order: 'Буюртма',
    cart: 'Сават',
    table: 'Стол',
    waiter: 'Официант',
    callWaiter: 'Официантни чақириш',
    bill: 'Ҳисоб чеки',
    total: 'Жами',
    subtotal: 'Оралиқ ҳисоб',
    serviceFee: 'Хизмат ҳақи',
    discount: 'Чегирма',
    pay: 'Тўлов',
    cash: 'Нақд',
    card: 'Карта',
    click: 'Click / Payme',
    debt: 'Насия (Қарз)',
    ready: 'Тайёр',
    preparing: 'Тайёрланмоқда',
    delivered: 'Етказиб берилди',
    pending: 'Кутилмоқда',
    searchFood: 'Таомларни қидириш...',
    addToCart: 'Саватга қўшиш',
    viewCart: 'Саватни кўриш',
    emptyCart: 'Саватчангиз бўш',
    sendToKitchen: 'Ошхонага юбориш',
    checkout: 'Тўлов / Ҳисоб',
    settings: 'Созламалар',
    language: 'Тил',
    kitchen1: '1-Ошхона (Қозон таомлари)',
    kitchen2: '2-Ошхона (Балиқ / Сомса)',
    bar: 'Бар / Ичимликлар',
    printerCustomer: '1-Принтер (Мижоз касса чеки)',
    printerKitchen1: '2-Принтер (1-Ошхона: Қозон)',
    printerKitchen2: '3-Принтер (2-Ошхона: Балиқ/Сомса)',
    testPrint: 'Тест чоп этиш',
    save: 'Сақлаш',
    close: 'Ёпиш',
    reviews: 'Фикр ва изоҳлар',
  },
  ru: {
    welcome: 'Добро пожаловать!',
    hello: 'Здравствуйте',
    menu: 'Меню',
    order: 'Заказ',
    cart: 'Корзина',
    table: 'Стол',
    waiter: 'Официант',
    callWaiter: 'Вызвать официанта',
    bill: 'Счет / Чек',
    total: 'Итого',
    subtotal: 'Сумма',
    serviceFee: 'Обслуживание',
    discount: 'Скидка',
    pay: 'Оплата',
    cash: 'Наличные',
    card: 'Карта',
    click: 'Click / Payme',
    debt: 'В долг',
    ready: 'Готово',
    preparing: 'Готовится',
    delivered: 'Доставлено',
    pending: 'В ожидании',
    searchFood: 'Поиск блюд...',
    addToCart: 'В корзину',
    viewCart: 'Посмотреть корзину',
    emptyCart: 'Корзина пуста',
    sendToKitchen: 'На кухню',
    checkout: 'К оплате',
    settings: 'Настройки',
    language: 'Язык',
    kitchen1: '1-Кухня (Казанные блюда)',
    kitchen2: '2-Кухня (Рыба / Самса)',
    bar: 'Бар / Напитки',
    printerCustomer: '1-Принтер (Чек для клиента)',
    printerKitchen1: '2-Принтер (1-Кухня: Казан)',
    printerKitchen2: '3-Принтер (2-Кухня: Рыба/Самса)',
    testPrint: 'Тестовая печать',
    save: 'Сохранить',
    close: 'Закрыть',
    reviews: 'Отзывы',
  },
  en: {
    welcome: 'Welcome!',
    hello: 'Hello',
    menu: 'Menu',
    order: 'Order',
    cart: 'Cart',
    table: 'Table',
    waiter: 'Waiter',
    callWaiter: 'Call Waiter',
    bill: 'Bill / Receipt',
    total: 'Total',
    subtotal: 'Subtotal',
    serviceFee: 'Service Fee',
    discount: 'Discount',
    pay: 'Payment',
    cash: 'Cash',
    card: 'Card',
    click: 'Click / Payme',
    debt: 'Debt / Tab',
    ready: 'Ready',
    preparing: 'Preparing',
    delivered: 'Delivered',
    pending: 'Pending',
    searchFood: 'Search dishes...',
    addToCart: 'Add to Cart',
    viewCart: 'View Cart',
    emptyCart: 'Your cart is empty',
    sendToKitchen: 'Send to Kitchen',
    checkout: 'Checkout',
    settings: 'Settings',
    language: 'Language',
    kitchen1: '1-Kitchen (Cauldron / Hot)',
    kitchen2: '2-Kitchen (Fish / Samsa)',
    bar: 'Bar / Drinks',
    printerCustomer: 'Printer 1 (Customer Bill)',
    printerKitchen1: 'Printer 2 (Kitchen 1: Cauldron)',
    printerKitchen2: 'Printer 3 (Kitchen 2: Fish/Samsa)',
    testPrint: 'Test Print',
    save: 'Save',
    close: 'Close',
    reviews: 'Reviews',
  },
};

const LanguageContext = createContext();

export const LanguageProvider = ({ children }) => {
  const [lang, setLangState] = useState(() => {
    return localStorage.getItem('restaron_language') || 'uz';
  });

  const setLang = (newLang) => {
    if (['uz', 'oz', 'ru', 'en'].includes(newLang)) {
      setLangState(newLang);
      localStorage.setItem('restaron_language', newLang);
    }
  };

  const t = (key) => {
    return translations[lang]?.[key] || translations['uz']?.[key] || key;
  };

  // Taom yoki kategoriya nomini joriy tilda chiqarish yordamchisi
  const getLocalizedName = (item) => {
    if (!item) return '';
    if (lang === 'ru' && item.name_ru) return item.name_ru;
    if (lang === 'en' && item.name_en) return item.name_en;
    if (lang === 'oz') {
      if (item.name_cyrillic) return item.name_cyrillic;
      return latinToCyrillic(item.name || '');
    }
    return item.name || '';
  };

  const getLocalizedDesc = (item) => {
    if (!item) return '';
    if (lang === 'ru' && item.description_ru) return item.description_ru;
    if (lang === 'en' && item.description_en) return item.description_en;
    if (lang === 'oz') {
      if (item.description_cyrillic) return item.description_cyrillic;
      return latinToCyrillic(item.description || '');
    }
    return item.description || '';
  };

  return (
    <LanguageContext.Provider
      value={{
        lang,
        setLang,
        t,
        getLocalizedName,
        getLocalizedDesc,
        availableLanguages: [
          { code: 'uz', label: "O'zbekcha", flag: '🇺🇿' },
          { code: 'oz', label: 'Ўзбекча', flag: '🇺🇿' },
          { code: 'ru', label: 'Русский', flag: '🇷🇺' },
          { code: 'en', label: 'English', flag: '🇬🇧' },
        ],
      }}
    >
      {children}
    </LanguageContext.Provider>
  );
};

export const useLanguage = () => useContext(LanguageContext);
