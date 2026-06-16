import tkinter as tk
from tkinter import simpledialog, messagebox, ttk, filedialog
import pymysql
import os
from PIL import Image
import io
import base64

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------- ФУНКЦИИ ФАЙЛОВ ----------
def get_picture_path():
    """Ищет заглушку picture.png в папке скрипта или рабочей директории. 
    Если не находит — создает её."""
    for folder in [BASE_DIR, os.getcwd()]:
        path = os.path.join(folder, 'picture.png')
        if os.path.isfile(path):
            return path
            
    path = os.path.join(BASE_DIR, 'picture.png')
    try:
        img = Image.new('RGB', (60, 60), color='gray')
        img.save(path)
        return path
    except Exception as e:
        print(f"Не удалось создать заглушку picture.png: {e}")
    return None

def get_product_photo_path(db_path):
    """Ищет изображение товара в папке скрипта или рабочей директории."""
    if not db_path:
        return None
    if os.path.isabs(db_path):
        if os.path.isfile(db_path):
            return db_path
        return None
        
    for folder in [BASE_DIR, os.getcwd()]:
        path = os.path.join(folder, db_path)
        if os.path.isfile(path):
            return path
    return None

def pil_to_tk_photo(img):
    """Конвертирует PIL фотографию 
    в стандартный tk.PhotoImage чтобы отображалась"""
    try:
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return tk.PhotoImage(data=img_base64)
    except Exception as e:
        print(f"Ошибка конвертации в PhotoImage: {e}")
        return None


# ================== БАЗА ДАННЫХ ==================
class DB:
    def __init__(self):
        self.conn = pymysql.connect(
            host="localhost", user="root", password="",
            database="store_db", cursorclass=pymysql.cursors.DictCursor
        )
        self.cur = self.conn.cursor()

    def login(self, u, p):
        self.cur.execute("SELECT role, full_name FROM users WHERE username=%s AND password=%s", (u, p))
        r = self.cur.fetchone()
        return r if r else None

    def get_categories(self):
        self.cur.execute("SELECT id, name FROM categories")
        return self.cur.fetchall()

    def get_manufacturers(self):
        self.cur.execute("SELECT id, name FROM manufacturers")
        return self.cur.fetchall()

    def get_suppliers(self):
        self.cur.execute("SELECT id, name FROM suppliers")
        return self.cur.fetchall()

    def get_products(self, search='', sort='', supplier_id=None, category_id=None):
        sql = """SELECT p.id, p.name, p.price, p.stock, p.discount, p.photo_path,
                        c.name AS cat_name, s.name AS sup_name
                 FROM products p
                 LEFT JOIN categories c ON p.category_id = c.id
                 LEFT JOIN suppliers s ON p.supplier_id = s.id
                 WHERE 1=1"""
        params = []
        if search:
            sql += " AND (p.name LIKE %s OR c.name LIKE %s OR s.name LIKE %s)"
            params.extend(['%'+search+'%']*3)
        if supplier_id:
            sql += " AND p.supplier_id = %s"
            params.append(supplier_id)
        if category_id:
            sql += " AND p.category_id = %s"
            params.append(category_id)
        if sort == 'asc':
            sql += " ORDER BY p.stock ASC"
        elif sort == 'desc':
            sql += " ORDER BY p.stock DESC"
        self.cur.execute(sql, params)
        return self.cur.fetchall()

    def get_product(self, pid):
        self.cur.execute("SELECT * FROM products WHERE id=%s", (pid,))
        return self.cur.fetchone()

    def add_product(self, data):
        self.cur.execute("""INSERT INTO products (name, price, stock, category_id, manufacturer_id,
                            supplier_id, unit, discount, description, photo_path)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", data)
        self.conn.commit()

    def update_product(self, pid, data):
        self.cur.execute("""UPDATE products SET name=%s, price=%s, stock=%s,
                            category_id=%s, manufacturer_id=%s, supplier_id=%s,
                            unit=%s, discount=%s, description=%s, photo_path=%s
                            WHERE id=%s""", (*data, pid))
        self.conn.commit()

    def delete_product(self, pid):
        self.cur.execute("SELECT COUNT(*) AS cnt FROM orders WHERE product_id=%s", (pid,))
        if self.cur.fetchone()['cnt'] > 0:
            raise Exception("Товар присутствует в заказах")
        self.cur.execute("DELETE FROM products WHERE id=%s", (pid,))
        self.conn.commit()

    def add_order(self, username, product_id, quantity):
        self.cur.execute("INSERT INTO orders (username, product_id, quantity) VALUES (%s,%s,%s)",
                         (username, product_id, quantity))
        self.cur.execute("UPDATE products SET stock = stock - %s WHERE id=%s", (quantity, product_id))
        self.conn.commit()

    def get_orders(self, username=None):
        if username:
            self.cur.execute("""SELECT o.id, p.name, o.quantity, o.order_date, o.status
                                FROM orders o JOIN products p ON o.product_id = p.id
                                WHERE o.username=%s ORDER BY o.order_date DESC""", (username,))
        else:
            self.cur.execute("""SELECT o.id, p.name, o.quantity, o.order_date, o.status
                                FROM orders o JOIN products p ON o.product_id = p.id
                                ORDER BY o.order_date DESC""")
        return self.cur.fetchall()

    def update_order_status(self, order_id, status):
        self.cur.execute("UPDATE orders SET status=%s WHERE id=%s", (status, order_id))
        self.conn.commit()


# ================== ПРИЛОЖЕНИЕ ==================
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Магазин обуви — панель управления")
        self.root.geometry("1300x700")
        self.root.configure(bg='#eaeef2')
        self.db = DB()
        self.edit_window_open = False
        self.photo_cache = {}   # храним ссылки на PhotoImage
        self.login_screen()

    def clear(self):
        for w in self.root.winfo_children():
            w.destroy()

    # ---------- ЭКРАН ВХОДА ----------
    def login_screen(self):
        self.clear()
        self.root.configure(bg='#eaeef2')
        main_frame = tk.Frame(self.root, bg='#eaeef2')
        main_frame.place(relx=0.5, rely=0.4, anchor='center')

        frame = tk.Frame(main_frame, bg='#ffffff', bd=2, relief='groove')
        frame.pack(padx=30, pady=30)

        tk.Label(frame, text="Добро пожаловать", font=('Segoe UI', 18, 'bold'),
                 bg='#ffffff', fg='#333333').pack(pady=(15,10))
        tk.Label(frame, text="Имя пользователя:", bg='#ffffff', fg='#333333').pack(anchor='w', padx=10)
        self.entry_u = tk.Entry(frame, width=30, bg='#f7f7f7', fg='black', insertbackground='black')
        self.entry_u.pack(padx=10, pady=2)
        tk.Label(frame, text="Пароль:", bg='#ffffff', fg='#333333').pack(anchor='w', padx=10)
        self.entry_p = tk.Entry(frame, show="*", width=30, bg='#f7f7f7', fg='black', insertbackground='black')
        self.entry_p.pack(padx=10, pady=2)

        btn_frame = tk.Frame(frame, bg='#ffffff')
        btn_frame.pack(pady=12)
        tk.Button(btn_frame, text="Вход", width=12, command=self.do_login,
                  bg='#d9e1ec', fg='black', font=('Segoe UI', 10)).pack(side='left', padx=5)
        tk.Button(btn_frame, text="Гостевой вход", width=12, command=self.guest_screen,
                  bg='#d9e1ec', fg='black', font=('Segoe UI', 10)).pack(side='left', padx=5)

    def do_login(self):
        user = self.db.login(self.entry_u.get(), self.entry_p.get())
        if not user:
            messagebox.showerror("Ошибка", "Неверный логин или пароль")
            return
        self.username = self.entry_u.get()
        self.role = user['role']
        self.full_name = user['full_name']
        self.show_main()

    def guest_screen(self):
        self.role = 'guest'
        self.username = ''
        self.full_name = 'Гость'
        self.show_main()

    # ---------- ГЛАВНОЕ ОКНО ----------
    def show_main(self):
        self.clear()
        self.root.configure(bg='#eaeef2')
        self.photo_cache.clear()

        # Верхняя панель
        top = tk.Frame(self.root, bg='#d9e1ec', height=50)
        top.pack(fill='x', side='top')
        welcome = f"Добро пожаловать, {self.full_name} ({self.role})"
        tk.Label(top, text=welcome, bg='#d9e1ec', fg='#333333',
                 font=('Segoe UI', 12, 'bold')).pack(side='left', padx=15, pady=10)
        tk.Button(top, text="Выйти", command=self.login_screen,
                  bg='#f0a0a0', fg='black', font=('Segoe UI', 9)).pack(side='right', padx=15, pady=10)

        # Центр
        center = tk.Frame(self.root, bg='#eaeef2')
        center.pack(fill='both', expand=True, padx=10, pady=10)

        # Фильтры
        filter_frame = tk.Frame(center, bg='#ffffff', bd=1, relief='flat')
        filter_frame.pack(fill='x', pady=(0,10))

        row1 = tk.Frame(filter_frame, bg='#ffffff')
        row1.pack(pady=5)

        tk.Label(row1, text="Поиск:", bg='#ffffff', fg='#333333').pack(side='left', padx=(10,2))
        self.search_var = tk.StringVar()
        search_entry = tk.Entry(row1, textvariable=self.search_var, width=20, bg='#f7f7f7', fg='black')
        search_entry.pack(side='left', padx=2)
        tk.Button(row1, text="Найти", command=self.refresh_products,
                  bg='#d9e1ec', fg='black').pack(side='left', padx=5)

        tk.Label(row1, text="Категория:", bg='#ffffff', fg='#333333').pack(side='left', padx=(15,2))
        self.combo_cat = ttk.Combobox(row1, state='readonly', width=15)
        self.combo_cat.pack(side='left', padx=2)
        categories = self.db.get_categories()
        self.cat_dict = {c['name']: c['id'] for c in categories}
        self.combo_cat['values'] = ['Все'] + list(self.cat_dict.keys())
        self.combo_cat.current(0)
        self.combo_cat.bind('<<ComboboxSelected>>', lambda e: self.refresh_products())

        tk.Label(row1, text="Поставщик:", bg='#ffffff', fg='#333333').pack(side='left', padx=(15,2))
        self.combo_sup = ttk.Combobox(row1, state='readonly', width=15)
        self.combo_sup.pack(side='left', padx=2)
        suppliers = self.db.get_suppliers()
        self.sup_dict = {s['name']: s['id'] for s in suppliers}
        self.combo_sup['values'] = ['Все'] + list(self.sup_dict.keys())
        self.combo_sup.current(0)
        self.combo_sup.bind('<<ComboboxSelected>>', lambda e: self.refresh_products())

        tk.Label(row1, text="Сортировка:", bg='#ffffff', fg='#333333').pack(side='left', padx=(15,2))
        self.sort_var = tk.StringVar(value='Без сортировки')
        sort_combo = ttk.Combobox(row1, textvariable=self.sort_var, state='readonly', width=15,
                                  values=['Без сортировки', 'Остаток ↑', 'Остаток ↓'])
        sort_combo.pack(side='left', padx=2)
        sort_combo.bind('<<ComboboxSelected>>', lambda e: self.refresh_products())

        # ---------- ПАНЕЛЬ КНОПОК ----------
        # Упаковываем её СНАЧАЛА в самый низ окна, чтобы она гарантированно отображалась на экране
        btn_panel = tk.Frame(center, bg='#eaeef2')
        btn_panel.pack(side='bottom', fill='x', pady=(10, 0))

        if self.role == 'admin':
            tk.Button(btn_panel, text="Добавить товар", command=self.add_product_form,
                      bg='#c1d9b7', fg='black', font=('Segoe UI', 9)).pack(side='left', padx=5)
            tk.Button(btn_panel, text="Изменить", command=self.edit_selected,
                      bg='#f7d98c', fg='black', font=('Segoe UI', 9)).pack(side='left', padx=5)
            tk.Button(btn_panel, text="Удалить", command=self.delete_selected,
                      bg='#f7b2a1', fg='black', font=('Segoe UI', 9)).pack(side='left', padx=5)
            tk.Button(btn_panel, text="Заказы", command=lambda: self.show_orders_window(None),
                      bg='#aac7e0', fg='black', font=('Segoe UI', 9)).pack(side='left', padx=5)
        elif self.role == 'manager':
            tk.Button(btn_panel, text="Изменить", command=self.edit_selected,
                      bg='#f7d98c', fg='black', font=('Segoe UI', 9)).pack(side='left', padx=5)
            tk.Button(btn_panel, text="Заказы", command=lambda: self.show_orders_window(None),
                      bg='#aac7e0', fg='black', font=('Segoe UI', 9)).pack(side='left', padx=5)
        elif self.role == 'user':
            tk.Button(btn_panel, text="Купить", command=self.buy_selected,
                      bg='#b7d7b0', fg='black', font=('Segoe UI', 9)).pack(side='left', padx=5)
            tk.Button(btn_panel, text="Мои заказы", command=lambda: self.show_orders_window(self.username),
                      bg='#aac7e0', fg='black', font=('Segoe UI', 9)).pack(side='left', padx=5)

        # ---------- ТАБЛИЦА ТОВАРОВ ----------
        # Упаковываем её во вторую очередь — она займет всё свободное пространство по центру
        tree_frame = tk.Frame(center, bg='#eaeef2')
        tree_frame.pack(side='top', fill='both', expand=True)

        # Конфигурируем высоту строк напрямую в стандартный стиль Treeview
        style = ttk.Style()
        style.configure('Treeview', rowheight=55)

        # Столбец Фото убираем из списка columns, так как это будет системный столбец #0
        columns = ('ID', 'Название', 'Цена', 'Остаток', 'Скидка', 'Категория', 'Поставщик')
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='tree headings', height=18)
        
        # Настраиваем системный столбец #0 под отображение картинок (Фото)
        self.tree.heading('#0', text='Фото')
        self.tree.column('#0', width=100, anchor='center')
        
        # Настраиваем остальные стандартные столбцы
        self.tree.heading('ID', text='ID')
        self.tree.column('ID', width=50, anchor='center')
        self.tree.heading('Название', text='Название')
        self.tree.column('Название', width=200)
        self.tree.heading('Цена', text='Цена')
        self.tree.column('Цена', width=80, anchor='center')
        self.tree.heading('Остаток', text='Остаток')
        self.tree.column('Остаток', width=80, anchor='center')
        self.tree.heading('Скидка', text='Скидка')
        self.tree.column('Скидка', width=70, anchor='center')
        self.tree.heading('Категория', text='Категория')
        self.tree.column('Категория', width=120, anchor='center')
        self.tree.heading('Поставщик', text='Поставщик')
        self.tree.column('Поставщик', width=140, anchor='center')

        scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        self.refresh_products()
        if self.role in ('admin', 'manager'):
            self.tree.bind('<Double-1>', lambda e: self.edit_selected())

    # ---------- ОБНОВЛЕНИЕ ТАБЛИЦЫ С ФОТО ----------
    def refresh_products(self):
        # Очищаем таблицу
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Очищаем кэш картинок
        self.photo_cache.clear()

        search = self.search_var.get().strip()
        sort = self.sort_var.get()
        sort_map = {'Без сортировки': 'none', 'Остаток ↑': 'asc', 'Остаток ↓': 'desc'}
        sort_sql = sort_map.get(sort, 'none')

        cat_name = self.combo_cat.get()
        cat_id = None if cat_name == 'Все' else self.cat_dict.get(cat_name)

        sup_name = self.combo_sup.get()
        sup_id = None if sup_name == 'Все' else self.sup_dict.get(sup_name)

        products = self.db.get_products(search, sort_sql, sup_id, cat_id)

        # Выбираем доступный фильтр сглаживания
        try:
            resample_filter = Image.Resampling.LANCZOS
        except AttributeError:
            try:
                resample_filter = Image.LANCZOS
            except AttributeError:
                resample_filter = Image.BICUBIC

        # Загружаем заглушку с использованием функции поиска
        self.default_img = None
        picture_path = get_picture_path()
        if picture_path and os.path.isfile(picture_path):
            try:
                img = Image.open(picture_path).resize((50, 50), resample_filter)
                self.default_img = pil_to_tk_photo(img)
            except Exception as e:
                print(f"Ошибка загрузки picture.png: {e}")

        for p in products:
            photo_img = None
            db_path = p.get('photo_path')
            full_photo_path = get_product_photo_path(db_path)

            if full_photo_path and os.path.isfile(full_photo_path):
                try:
                    img = Image.open(full_photo_path).resize((50, 50), resample_filter)
                    photo_img = pil_to_tk_photo(img)
                except Exception as e:
                    print(f"Ошибка загрузки {full_photo_path}: {e}")
                    photo_img = self.default_img
            else:
                photo_img = self.default_img

            # Сохраняем ссылку в кэш, чтобы избежать сборки мусора
            if photo_img:
                self.photo_cache[p['id']] = photo_img

            tags = ()
            if p['stock'] == 0:
                tags = ('outofstock',)
            elif p['discount'] > 15:
                tags = ('discount',)

            # Кортеж значений строго соответствует 7 колонкам (без Фото)
            values = (p['id'], p['name'], f"{p['price']:.2f}", p['stock'],
                      f"{p['discount']}%", p['cat_name'] or '-', p['sup_name'] or '-')

            insert_kwargs = {'values': values, 'tags': tags, 'text': ''}
            if photo_img is not None:
                insert_kwargs['image'] = photo_img

            self.tree.insert('', 'end', **insert_kwargs)

        self.tree.tag_configure('outofstock', background='#ffd9d9')
        self.tree.tag_configure('discount', background='#d9ffd9')

    # ---------- РАБОТА С ВЫБРАННЫМ ТОВАРОМ ----------
    def get_selected_id(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Предупреждение", "Выберите товар в таблице")
            return None
        # ID всегда на первом месте в values (индекс 0)
        return int(self.tree.item(selected[0], 'values')[0])

    def edit_selected(self):
        pid = self.get_selected_id()
        if pid:
            self.edit_product_form(pid)

    def delete_selected(self):
        pid = self.get_selected_id()
        if pid and messagebox.askyesno("Подтверждение", "Удалить выбранный товар?"):
            try:
                self.db.delete_product(pid)
                self.refresh_products()
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))

    def buy_selected(self):
        pid = self.get_selected_id()
        if not pid:
            return
        prod = self.db.get_product(pid)
        if not prod:
            return
        if prod['stock'] <= 0:
            messagebox.showwarning("Нет в наличии", "Товар отсутствует")
            return
        qty = simpledialog.askinteger("Покупка", f"{prod['name']}\nВ наличии: {prod['stock']}",
                                      minvalue=1, maxvalue=prod['stock'])
        if qty:
            self.db.add_order(self.username, prod['id'], qty)
            self.refresh_products()
            messagebox.showinfo("Успех", "Заказ оформлен")

    # ---------- ФОРМЫ ДОБАВЛЕНИЯ/РЕДАКТИРОВАНИЯ ----------
    def add_product_form(self):
        if self.edit_window_open:
            messagebox.showwarning("Предупреждение", "Окно редактирования уже открыто")
            return
        self.edit_window_open = True
        self.open_editor("Новый товар")

    def edit_product_form(self, pid):
        if self.edit_window_open:
            messagebox.showwarning("Предупреждение", "Окно редактирования уже открыто")
            return
        prod = self.db.get_product(pid)
        if not prod:
            messagebox.showerror("Ошибка", "Товар не найден")
            return
        self.edit_window_open = True
        self.open_editor("Редактирование", prod)

    def open_editor(self, title, prod=None):
        win = tk.Toplevel(self.root)
        win.title(title)
        win.geometry("520x650")
        win.configure(bg='#f0f4f8')
        win.protocol("WM_DELETE_WINDOW", lambda: self._close_editor(win))

        main = tk.Frame(win, bg='#f0f4f8')
        main.pack(fill='both', expand=True, padx=15, pady=15)

        fields = [
            ('Название', 'entry'),
            ('Стоимость (руб)', 'entry'),
            ('Остаток (шт)', 'entry'),
            ('Скидка, %', 'entry'),
            ('Единица измерения', 'entry'),
            ('Категория', 'combobox'),
            ('Производитель', 'combobox'),
            ('Источник (поставщик)', 'combobox'),
            ('Описание', 'entry'),
        ]
        self.editor_entries = {}
        row = 0
        for label, typ in fields:
            tk.Label(main, text=label, bg='#f0f4f8', fg='#333333', font=('Segoe UI', 9)).grid(row=row, column=0, sticky='w', pady=2)
            if typ == 'entry':
                ent = tk.Entry(main, width=35, bg='white', fg='black', insertbackground='black')
                ent.grid(row=row, column=1, pady=2, sticky='w')
                self.editor_entries[label] = ent
            else:
                cb = ttk.Combobox(main, state='readonly', width=33)
                cb.grid(row=row, column=1, pady=2, sticky='w')
                self.editor_entries[label] = cb
            row += 1

        cats = self.db.get_categories()
        self.editor_cat_dict = {c['name']: c['id'] for c in cats}
        self.editor_entries['Категория']['values'] = list(self.editor_cat_dict.keys())

        mans = self.db.get_manufacturers()
        self.editor_man_dict = {m['name']: m['id'] for m in mans}
        self.editor_entries['Производитель']['values'] = list(self.editor_man_dict.keys())

        sups = self.db.get_suppliers()
        self.editor_sup_dict = {s['name']: s['id'] for s in sups}
        self.editor_entries['Источник (поставщик)']['values'] = list(self.editor_sup_dict.keys())

        # Фото
        tk.Label(main, text="Фото", bg='#f0f4f8', fg='#333333').grid(row=row, column=0, sticky='w', pady=2)
        photo_frame = tk.Frame(main, bg='#f0f4f8')
        photo_frame.grid(row=row, column=1, sticky='w', pady=2)
        self.photo_var = tk.StringVar()
        tk.Button(photo_frame, text="Выбрать файл", command=self.select_photo,
                  bg='#d9e1ec', fg='black').pack(side='left')
        tk.Label(photo_frame, textvariable=self.photo_var, bg='#f0f4f8', fg='#333333', width=25).pack(side='left', padx=5)

        if prod:
            self.editor_entries['Название'].insert(0, prod['name'])
            self.editor_entries['Стоимость (руб)'].insert(0, str(prod['price']))
            self.editor_entries['Остаток (шт)'].insert(0, str(prod['stock']))
            self.editor_entries['Скидка, %'].insert(0, str(prod['discount']))
            self.editor_entries['Единица измерения'].insert(0, prod.get('unit', 'шт.'))
            self.editor_entries['Описание'].insert(0, prod.get('description', ''))
            cat_name = next((c['name'] for c in cats if c['id'] == prod['category_id']), '')
            if cat_name:
                self.editor_entries['Категория'].set(cat_name)
            man_name = next((m['name'] for m in mans if m['id'] == prod['manufacturer_id']), '')
            if man_name:
                self.editor_entries['Производитель'].set(man_name)
            sup_name = next((s['name'] for s in sups if s['id'] == prod['supplier_id']), '')
            if sup_name:
                self.editor_entries['Источник (поставщик)'].set(sup_name)
            if prod.get('photo_path'):
                self.photo_var.set(prod['photo_path'])
            self.editing_product_id = prod['id']
        else:
            self.editing_product_id = None

        tk.Button(main, text="Сохранить", command=self.save_product_editor,
                  bg='#b7d7b0', fg='black', width=15).grid(row=row+1, column=0, columnspan=2, pady=20)

    def select_photo(self):
        path = filedialog.askopenfilename(filetypes=[("Изображения", "*.png *.jpg *.jpeg")])
        if path:
            self.photo_var.set(path)

    def save_product_editor(self):
        try:
            name = self.editor_entries['Название'].get().strip()
            price = float(self.editor_entries['Стоимость (руб)'].get())
            stock = int(self.editor_entries['Остаток (шт)'].get())
            discount = float(self.editor_entries['Скидка, %'].get())
            unit = self.editor_entries['Единица измерения'].get().strip() or 'шт.'
            description = self.editor_entries['Описание'].get().strip()
            if price < 0 or stock < 0 or discount < 0 or discount > 100:
                raise ValueError("Некорректные значения")

            cat_name = self.editor_entries['Категория'].get()
            man_name = self.editor_entries['Производитель'].get()
            sup_name = self.editor_entries['Источник (поставщик)'].get()
            cat_id = self.editor_cat_dict.get(cat_name)
            man_id = self.editor_man_dict.get(man_name)
            sup_id = self.editor_sup_dict.get(sup_name)
            if not cat_id or not man_id or not sup_id:
                raise ValueError("Выберите категорию, производителя и поставщика")

            new_photo = self.photo_var.get()
            if new_photo and os.path.isfile(new_photo):
                img = Image.open(new_photo)
                try:
                    resample_filter = Image.Resampling.LANCZOS
                except AttributeError:
                    try:
                        resample_filter = Image.LANCZOS
                    except AttributeError:
                        resample_filter = Image.BICUBIC
                img.thumbnail((300, 200), resample_filter)
                
                images_dir = os.path.join(BASE_DIR, "images")
                os.makedirs(images_dir, exist_ok=True)
                dst = os.path.join(images_dir, os.path.basename(new_photo))
                img.save(dst)
                
                if self.editing_product_id:
                    old = self.db.get_product(self.editing_product_id).get('photo_path')
                    if old:
                        if not os.path.isabs(old):
                            old = os.path.join(BASE_DIR, old)
                        if os.path.isfile(old) and os.path.abspath(old) != os.path.abspath(dst):
                            os.remove(old)
                # В базе данных сохраняем относительный путь для портативности
                new_photo = os.path.join("images", os.path.basename(new_photo))
            elif self.editing_product_id:
                old = self.db.get_product(self.editing_product_id).get('photo_path')
                new_photo = old if old else None
            else:
                new_photo = None

            data = (name, price, stock, cat_id, man_id, sup_id, unit, discount, description, new_photo)
            if self.editing_product_id:
                self.db.update_product(self.editing_product_id, data)
            else:
                self.db.add_product(data)
            for w in self.root.winfo_children():
                if isinstance(w, tk.Toplevel):
                    w.destroy()
            self.edit_window_open = False
            self.refresh_products()
            messagebox.showinfo("Успех", "Товар сохранён")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def _close_editor(self, win):
        self.edit_window_open = False
        win.destroy()

    # ---------- СИСТЕМЫ ЗАКАЗОВ С ПЕРЕВОДОМ СТАТУСОВ ----------
    def show_orders_window(self, username):
        """Открывает окно управления заказами с переводом статусов на русский язык.
        Доступ к изменению статусов открыт для Менеджера и Администратора."""
        win = tk.Toplevel(self.root)
        win.title("Заказы")
        win.geometry("700x450")
        win.configure(bg='#f5f6f8')

        # Словари для двустороннего перевода статусов
        status_translate = {
            'pending': 'Ожидает',
            'processing': 'В обработке',
            'completed': 'Завершён',
            'cancelled': 'Отменён'
        }
        status_reverse = {v: k for k, v in status_translate.items()}

        # ---------- ПАНЕЛЬ ИЗМЕНЕНИЯ СТАТУСА ----------
        # Сначала упаковываем нижнюю панель управления вниз всплывающего окна (side='bottom'),
        # чтобы она гарантированно отображалась на экранах с любым разрешением
        if self.role in ('manager', 'admin') and username is None:
            btn_frame = tk.Frame(win, bg='#e9ecf0')
            btn_frame.pack(side='bottom', fill='x', padx=5, pady=5)
            tk.Label(btn_frame, text="Новый статус:", bg='#e9ecf0').pack(side='left', padx=5)
            status_combo = ttk.Combobox(btn_frame, state='readonly', width=15,
                                        values=list(status_translate.values()))
            status_combo.pack(side='left', padx=5)

            def change_status():
                sel = tree.focus()
                if not sel:
                    messagebox.showwarning("Не выбрано", "Выберите заказ")
                    return
                new_status_ru = status_combo.get()
                if not new_status_ru:
                    return
                # Получаем английский эквивалент для сохранения в БД
                new_status_en = status_reverse.get(new_status_ru)
                if not new_status_en:
                    messagebox.showerror("Ошибка", "Неизвестный статус")
                    return

                self.db.update_order_status(int(sel), new_status_en)
                
                # Очистка и повторное заполнение списка
                for item in tree.get_children():
                    tree.delete(item)
                for o in self.db.get_orders(username):
                    status_ru = status_translate.get(o['status'], o['status'])
                    tree.insert("", "end", iid=str(o['id']),
                                values=(o['id'], o['name'], o['quantity'], o['order_date'], status_ru))

            tk.Button(btn_frame, text="Применить", command=change_status, bg='#c0d0e0').pack(side='left', padx=5)

        # ---------- ТАБЛИЦА ЗАКАЗОВ ----------
        # Упаковываем таблицу во вторую очередь во весь оставшийся экран (side='top', expand=True)
        columns = ("ID", "Товар", "Кол-во", "Дата", "Статус")
        tree = ttk.Treeview(win, columns=columns, show="headings", height=15)
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=120, anchor='center')
        tree.pack(side='top', fill='both', expand=True, padx=5, pady=5)

        # Вывод данных с переводом на русский язык
        orders = self.db.get_orders(username)
        for o in orders:
            status_ru = status_translate.get(o['status'], o['status'])
            tree.insert("", "end", iid=str(o['id']),
                        values=(o['id'], o['name'], o['quantity'], o['order_date'], status_ru))


# ================== ЗАПУСК ==================
if __name__ == '__main__':
    get_picture_path()
    root = tk.Tk()
    App(root)
    root.mainloop()