-- ============================================================
-- База данных для ИС "ООО Обувь" (демоэкзамен)
-- Используется SQLite
-- ============================================================

-- 1. Таблица пользователей
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role TEXT NOT NULL,                     -- 'admin', 'manager', 'client', 'guest'
    fio TEXT NOT NULL,
    login TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL
);

-- 2. Таблица товаров
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    unit TEXT DEFAULT 'шт.',
    price REAL NOT NULL,
    supplier TEXT,
    manufacturer TEXT,
    category TEXT,
    discount REAL DEFAULT 0,
    quantity INTEGER DEFAULT 0,
    description TEXT,
    photo TEXT                           -- имя файла изображения
);

-- 3. Таблица заказов
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_number TEXT NOT NULL UNIQUE,
    order_date TEXT NOT NULL,            -- DATE в формате ГГГГ-ММ-ДД
    delivery_date TEXT,
    pickup_address TEXT,
    client_fio TEXT NOT NULL,
    pickup_code TEXT,
    status TEXT DEFAULT 'Новый'         -- 'Новый', 'Завершен'
);

-- 4. Таблица позиций заказа (связь заказов и товаров)
CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    product_article TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (product_article) REFERENCES products(article) ON DELETE RESTRICT
);

-- 5. Индексы для ускорения поиска
CREATE INDEX IF NOT EXISTS idx_products_article ON products(article);
CREATE INDEX IF NOT EXISTS idx_products_name ON products(name);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_orders_client_fio ON orders(client_fio);
CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product ON order_items(product_article);

-- ============================================================
-- (Опционально) Начальные данные можно добавить позже через импорт
-- ============================================================