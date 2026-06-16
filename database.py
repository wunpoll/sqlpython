import sqlite3
from typing import Optional, List, Dict, Any

DB_PATH = "shoes.db"  # или путь к вашему файлу БД


def get_connection() -> sqlite3.Connection:
    """Возвращает подключение к БД."""
    return sqlite3.connect(DB_PATH)


# ---------- ПОЛЬЗОВАТЕЛИ (авторизация) ----------

def get_user(login: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Проверяет логин и пароль, возвращает словарь с полями:
    id, role, fio, login, password
    или None, если не найден.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, role, fio, login, password FROM users WHERE login = ? AND password = ?",
        (login, password)
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "id": row[0],
            "role": row[1],
            "fio": row[2],
            "login": row[3],
            "password": row[4]
        }
    return None


# ---------- ТОВАРЫ (CRUD + поиск/фильтр/сортировка) ----------

def get_products(
    search: str = "",
    category: str = "",
    manufacturer: str = "",
    supplier: str = "",
    sort: str = "name_asc"
) -> List[Dict[str, Any]]:
    """
    Возвращает список товаров с учётом:
      - поиска по артикулу или названию (search)
      - фильтров по категории, производителю, поставщику
      - сортировки: name_asc, name_desc, price_asc, price_desc, article_asc
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Базовый запрос
    query = """
        SELECT id, article, name, unit, price, supplier, manufacturer,
               category, discount, quantity, description, photo
        FROM products
        WHERE 1=1
    """
    params = []

    # Поиск
    if search:
        query += " AND (article LIKE ? OR name LIKE ?)"
        like = f"%{search}%"
        params.extend([like, like])

    # Фильтры
    if category:
        query += " AND category = ?"
        params.append(category)
    if manufacturer:
        query += " AND manufacturer = ?"
        params.append(manufacturer)
    if supplier:
        query += " AND supplier = ?"
        params.append(supplier)

    # Сортировка
    sort_map = {
        "name_asc": "name ASC",
        "name_desc": "name DESC",
        "price_asc": "price ASC",
        "price_desc": "price DESC",
        "article_asc": "article ASC",
    }
    order = sort_map.get(sort, "name ASC")
    query += f" ORDER BY {order}"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    # Преобразуем в список словарей
    columns = ["id", "article", "name", "unit", "price", "supplier",
               "manufacturer", "category", "discount", "quantity", "description", "photo"]
    return [dict(zip(columns, row)) for row in rows]


def get_product_by_id(product_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        columns = ["id", "article", "name", "unit", "price", "supplier",
                   "manufacturer", "category", "discount", "quantity", "description", "photo"]
        return dict(zip(columns, row))
    return None


def add_product(data: Dict[str, Any]) -> int:
    """
    Добавляет товар. data содержит поля:
    article, name, unit, price, supplier, manufacturer,
    category, discount, quantity, description, photo
    Возвращает id нового товара.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO products
        (article, name, unit, price, supplier, manufacturer,
         category, discount, quantity, description, photo)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["article"], data["name"], data["unit"], data["price"],
        data["supplier"], data["manufacturer"], data["category"],
        data["discount"], data["quantity"], data["description"], data["photo"]
    ))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id


def update_product(product_id: int, data: Dict[str, Any]) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE products SET
            article=?, name=?, unit=?, price=?, supplier=?,
            manufacturer=?, category=?, discount=?, quantity=?,
            description=?, photo=?
        WHERE id=?
    """, (
        data["article"], data["name"], data["unit"], data["price"],
        data["supplier"], data["manufacturer"], data["category"],
        data["discount"], data["quantity"], data["description"], data["photo"],
        product_id
    ))
    conn.commit()
    conn.close()


def delete_product(product_id: int) -> bool:
    """
    Удаляет товар, если он не присутствует в заказах.
    Возвращает True, если удаление успешно, иначе False.
    """
    conn = get_connection()
    cursor = conn.cursor()
    # Проверяем, есть ли товар в заказах (в таблице order_items)
    cursor.execute("SELECT COUNT(*) FROM order_items WHERE product_article = (SELECT article FROM products WHERE id=?)", (product_id,))
    count = cursor.fetchone()[0]
    if count > 0:
        conn.close()
        return False
    cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()
    return True


# ---------- ВСПОМОГАТЕЛЬНЫЕ СПИСКИ ДЛЯ ФИЛЬТРОВ ----------

def get_categories() -> List[str]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT category FROM products ORDER BY category")
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]


def get_manufacturers() -> List[str]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT manufacturer FROM products ORDER BY manufacturer")
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]


def get_suppliers() -> List[str]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT supplier FROM products ORDER BY supplier")
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]


# ---------- ЗАКАЗЫ (упрощённый CRUD) ----------

def get_orders() -> List[Dict[str, Any]]:
    """
    Возвращает список заказов с полями:
    id, order_number, order_date, delivery_date, pickup_address,
    client_fio, pickup_code, status
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, order_number, order_date, delivery_date,
               pickup_address, client_fio, pickup_code, status
        FROM orders
        ORDER BY id DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    columns = ["id", "order_number", "order_date", "delivery_date",
               "pickup_address", "client_fio", "pickup_code", "status"]
    return [dict(zip(columns, row)) for row in rows]


def get_order_by_id(order_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, order_number, order_date, delivery_date,
               pickup_address, client_fio, pickup_code, status
        FROM orders WHERE id = ?
    """, (order_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        columns = ["id", "order_number", "order_date", "delivery_date",
                   "pickup_address", "client_fio", "pickup_code", "status"]
        return dict(zip(columns, row))
    return None


def add_order(data: Dict[str, Any]) -> int:
    """
    Добавляет заказ. data содержит:
    order_number, order_date, delivery_date, pickup_address,
    client_fio, pickup_code, status
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO orders
        (order_number, order_date, delivery_date, pickup_address,
         client_fio, pickup_code, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        data["order_number"], data["order_date"], data["delivery_date"],
        data["pickup_address"], data["client_fio"], data["pickup_code"],
        data["status"]
    ))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id


def update_order(order_id: int, data: Dict[str, Any]) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE orders SET
            order_number=?, order_date=?, delivery_date=?,
            pickup_address=?, client_fio=?, pickup_code=?, status=?
        WHERE id=?
    """, (
        data["order_number"], data["order_date"], data["delivery_date"],
        data["pickup_address"], data["client_fio"], data["pickup_code"],
        data["status"], order_id
    ))
    conn.commit()
    conn.close()


def delete_order(order_id: int) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM orders WHERE id = ?", (order_id,))
    conn.commit()
    conn.close()


# ---------- КЛИЕНТЫ ДЛЯ ВЫПАДАЮЩЕГО СПИСКА В ЗАКАЗАХ ----------

def get_clients() -> List[str]:
    """
    Возвращает список ФИО клиентов из таблицы users (роль 'Авторизированный клиент')
    или из заказов. Для простоты возьмём из заказов.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT client_fio FROM orders ORDER BY client_fio")
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows] if rows else []


# ---------- СТАТУСЫ ЗАКАЗОВ (захардкожены) ----------

ORDER_STATUSES = ["Новый", "Завершен"]


# ---------- ДОПОЛНИТЕЛЬНО: ПОИСК АРТИКУЛОВ ДЛЯ ПРОВЕРКИ УДАЛЕНИЯ ----------

def get_article_by_id(product_id: int) -> Optional[str]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT article FROM products WHERE id = ?", (product_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None