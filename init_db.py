import sqlite3
import os
import pandas as pd
from datetime import datetime

DB_PATH = "shoes.db"

# -------------------------------------------------------------------
# 1. Создание таблиц (если их нет)
# -------------------------------------------------------------------

CREATE_TABLES_SQL = """
-- Таблица пользователей
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role TEXT NOT NULL,
    fio TEXT NOT NULL,
    login TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL
);

-- Таблица товаров
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
    photo TEXT
);

-- Таблица заказов
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_number TEXT NOT NULL UNIQUE,
    order_date TEXT NOT NULL,
    delivery_date TEXT,
    pickup_address TEXT,
    client_fio TEXT NOT NULL,
    pickup_code TEXT,
    status TEXT DEFAULT 'Новый'
);

-- Таблица позиций заказа
CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    product_article TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (product_article) REFERENCES products(article) ON DELETE RESTRICT
);

-- Индексы
CREATE INDEX IF NOT EXISTS idx_products_article ON products(article);
CREATE INDEX IF NOT EXISTS idx_products_name ON products(name);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_orders_client_fio ON orders(client_fio);
CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product ON order_items(product_article);
"""

def create_tables(conn):
    """Создаёт таблицы, если их нет."""
    conn.executescript(CREATE_TABLES_SQL)
    conn.commit()
    print("✅ Таблицы созданы (или уже существуют).")

# -------------------------------------------------------------------
# 2. Добавление тестовых пользователей
# -------------------------------------------------------------------

def add_test_users(conn):
    """Добавляет пользователей: admin, manager, client."""
    users = [
        ("admin", "admin123", "Администратор Системы", "admin"),
        ("manager", "manager123", "Менеджер Иванов Иван", "manager"),
        ("client", "client123", "Клиент Петров Петр", "client"),
    ]
    cursor = conn.cursor()
    for login, password, fio, role in users:
        try:
            cursor.execute(
                "INSERT INTO users (role, fio, login, password) VALUES (?, ?, ?, ?)",
                (role, fio, login, password)
            )
        except sqlite3.IntegrityError:
            print(f"⚠️ Пользователь {login} уже существует, пропускаем.")
    conn.commit()
    print("✅ Тестовые пользователи добавлены (admin, manager, client).")

# -------------------------------------------------------------------
# 3. Импорт данных из Excel (опционально)
# -------------------------------------------------------------------

def import_from_excel(conn):
    """
    Импортирует данные из файлов:
        Tovar.xlsx -> products
        user_import.xlsx -> users (если нужно)
        Заказ_import.xlsx -> orders и order_items
        Пункты выдачи_import.xlsx -> отдельная таблица? (пока не используем)
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    cursor = conn.cursor()

    # --- 3.1 Импорт товаров ---
    tovar_path = os.path.join(base_dir, "Tovar.xlsx")
    if os.path.exists(tovar_path):
        df = pd.read_excel(tovar_path)
        print(f"📥 Импорт товаров из {tovar_path} ...")
        for _, row in df.iterrows():
            try:
                cursor.execute("""
                    INSERT INTO products
                    (article, name, unit, price, supplier, manufacturer,
                     category, discount, quantity, description, photo)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    row["Артикул"],
                    row["Наименование товара"],
                    row.get("Единица измерения", "шт."),
                    float(row["Цена"]),
                    row.get("Поставщик", ""),
                    row.get("Производитель", ""),
                    row.get("Категория товара", ""),
                    float(row.get("Действующая скидка", 0)),
                    int(row.get("Кол-во на складе", 0)),
                    row.get("Описание товара", ""),
                    row.get("Фото", "")
                ))
            except sqlite3.IntegrityError:
                # артикул уже существует
                pass
        conn.commit()
        print("✅ Товары импортированы.")
    else:
        print("⚠️ Файл Tovar.xlsx не найден, пропускаем.")

    # --- 3.2 Импорт пользователей (из user_import.xlsx) ---
    users_path = os.path.join(base_dir, "user_import.xlsx")
    if os.path.exists(users_path):
        df = pd.read_excel(users_path)
        print(f"📥 Импорт пользователей из {users_path} ...")
        for _, row in df.iterrows():
            try:
                cursor.execute(
                    "INSERT INTO users (role, fio, login, password) VALUES (?, ?, ?, ?)",
                    (row["Роль сотрудника"], row["ФИО"], row["Логин"], row["Пароль"])
                )
            except sqlite3.IntegrityError:
                pass
        conn.commit()
        print("✅ Пользователи импортированы.")
    else:
        print("⚠️ Файл user_import.xlsx не найден, пропускаем.")

    # --- 3.3 Импорт заказов ---
    orders_path = os.path.join(base_dir, "Заказ_import.xlsx")
    if os.path.exists(orders_path):
        df = pd.read_excel(orders_path)
        print(f"📥 Импорт заказов из {orders_path} ...")
        for _, row in df.iterrows():
            # Номер заказа, артикулы с количествами, даты, адрес, клиент, код, статус
            order_num = row["Номер заказа"]
            order_date = row["Дата заказа"]
            # Если дата в Excel – строка, преобразуем
            if isinstance(order_date, str):
                try:
                    # пробуем парсить разные форматы
                    order_date = pd.to_datetime(order_date, errors='coerce')
                    if pd.isna(order_date):
                        order_date = datetime.now().strftime("%Y-%m-%d")
                    else:
                        order_date = order_date.strftime("%Y-%m-%d")
                except:
                    order_date = datetime.now().strftime("%Y-%m-%d")
            else:
                order_date = order_date.strftime("%Y-%m-%d") if not pd.isna(order_date) else datetime.now().strftime("%Y-%m-%d")
            
            delivery_date = row["Дата доставки"]
            if isinstance(delivery_date, str):
                try:
                    delivery_date = pd.to_datetime(delivery_date, errors='coerce')
                    if pd.isna(delivery_date):
                        delivery_date = ""
                    else:
                        delivery_date = delivery_date.strftime("%Y-%m-%d")
                except:
                    delivery_date = ""
            else:
                delivery_date = delivery_date.strftime("%Y-%m-%d") if not pd.isna(delivery_date) else ""
            
            pickup_address = row["Адрес пункта выдачи"]
            client_fio = row["ФИО авторизированного клиента"]
            pickup_code = row["Код для получения"]
            status = row["Статус заказа"]

            # Вставляем заказ
            cursor.execute("""
                INSERT INTO orders
                (order_number, order_date, delivery_date, pickup_address,
                 client_fio, pickup_code, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (order_num, order_date, delivery_date, pickup_address,
                  client_fio, pickup_code, status))
            order_id = cursor.lastrowid

            # Разбираем артикулы и количества (через запятую)
            # Пример: "А112Т4, 2, F635R4, 2"
            items_str = row["Артикул заказа"]
            if isinstance(items_str, str):
                parts = [p.strip() for p in items_str.split(",")]
                # Предполагаем, что идут пары: артикул, количество, артикул, количество...
                for i in range(0, len(parts)-1, 2):
                    article = parts[i]
                    try:
                        quantity = int(parts[i+1])
                    except:
                        quantity = 1
                    cursor.execute(
                        "INSERT INTO order_items (order_id, product_article, quantity) VALUES (?, ?, ?)",
                        (order_id, article, quantity)
                    )
        conn.commit()
        print("✅ Заказы и их позиции импортированы.")
    else:
        print("⚠️ Файл Заказ_import.xlsx не найден, пропускаем.")

# -------------------------------------------------------------------
# 4. Основной запуск
# -------------------------------------------------------------------

def main():
    # Проверяем, существует ли БД, чтобы не пересоздавать
    db_exists = os.path.exists(DB_PATH)
    conn = sqlite3.connect(DB_PATH)

    if not db_exists:
        print("🆕 Создаём новую базу данных...")
        create_tables(conn)
        add_test_users(conn)
        # Можно сразу импортировать Excel, если нужно
        # import_from_excel(conn)
    else:
        print("📂 База данных уже существует.")
        # Для безопасности, можно создать таблицы (если их нет)
        create_tables(conn)
        # Добавить пользователей, если их нет
        add_test_users(conn)

    conn.close()
    print("✅ Готово! База данных создана/обновлена.")

if __name__ == "__main__":
    main()