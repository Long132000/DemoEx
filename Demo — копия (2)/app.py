import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from datetime import datetime

# --- 1. КОНСТАНТЫ И СТИЛИ (Прил_3_ОЗ...) ---
DB_NAME = 'demodb.db'
FONT_FAMILY = "Times New Roman"

COLOR_PRIMARY = "#FFFFFF"   # Основной фон (Белый)
COLOR_SECONDARY = "#7FFF00" # Дополнительный фон (Лайм)
COLOR_ACCENT = "#00FA9A"    # Акцентирование (Бледно-зеленый)
COLOR_DISCOUNT_HIGH = "#2E8B57" # Скидка > 15% (Темно-зеленый)

# --- 2. ФУНКЦИИ РАБОТЫ С БД ---

def execute_query(query, params=(), fetch_one=False):
    """Общая функция для выполнения запросов к БД."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        if query.strip().upper().startswith(('INSERT', 'UPDATE', 'DELETE')):
            conn.commit()
            return True, cursor.lastrowid
        if fetch_one:
            return cursor.fetchone()
        return cursor.fetchall()
    except sqlite3.Error as e:
        # В реальном приложении: print(f"DB Error: {e}")
        return False, None
    finally:
        conn.close()

def authenticate_user(login, password):
    """Проверяет учетные данные и возвращает имя роли."""
    query = """
    SELECT T1.RoleName
    FROM Role AS T1
    INNER JOIN User AS T2
      ON T1.RoleID = T2.RoleID
    WHERE T2.Login = ? AND T2.Password = ?
    """
    result = execute_query(query, (login, password), fetch_one=True)
    return result[0] if result else None

# Вспомогательные функции для получения справочников
def get_all_suppliers():
    return execute_query("SELECT ProviderID, ProviderName FROM Provider")
def get_all_manufacturers():
    return execute_query("SELECT ManufacturerID, ManufacturerName FROM Manufacturer")
def get_all_categories():
    return execute_query("SELECT CategoryID, CategoryName FROM Category")
def get_all_statuses():
    return execute_query("SELECT StatusID, StatusName FROM OrderStatus")
def get_all_pickup_points():
    return execute_query("SELECT PointID, Address FROM PickupPoint")
def get_product_by_article(article):
    query = """
    SELECT T1.*, T2.CategoryName, T3.ProviderName, T4.ManufacturerName
    FROM Product AS T1
    INNER JOIN Category AS T2 ON T1.CategoryID = T2.CategoryID
    INNER JOIN Provider AS T3 ON T1.ProviderID = T3.ProviderID
    INNER JOIN Manufacturer AS T4 ON T1.ManufacturerID = T4.ManufacturerID
    WHERE T1.ProductArticle = ?
    """
    return execute_query(query, (article,), fetch_one=True)
def get_order_details(order_id):
    order_query = 'SELECT * FROM "Order" WHERE OrderID = ?'
    products_query = 'SELECT T1.ProductArticle, T1.Quantity, T2.Name FROM OrderProduct AS T1 INNER JOIN Product AS T2 ON T1.ProductArticle = T2.ProductArticle WHERE T1.OrderID = ?'
    order = execute_query(order_query, (order_id,), fetch_one=True)
    products = execute_query(products_query, (order_id,))
    return order, products

# --- 3. ОКНА CRUD (АДМИНИСТРАТОР) ---

class ProductCRUDWindow(tk.Toplevel):
    def __init__(self, master, article=None, catalog_ref=None):
        super().__init__(master)
        self.title("Редактирование/Добавление товара")
        self.geometry("450x550")
        self.configure(bg=COLOR_PRIMARY)
        self.article = article
        self.catalog_ref = catalog_ref

        self.data = get_product_by_article(article) if article else None
        self._setup_style()
        self._setup_widgets()
        if self.data:
            self._load_data()

    def _setup_style(self):
        style = ttk.Style(self)
        style.configure('.', font=(FONT_FAMILY, 10))
        style.configure('TFrame', background=COLOR_PRIMARY)
        style.configure('TLabel', background=COLOR_PRIMARY)
        style.configure('TButton', background=COLOR_ACCENT, foreground='black')

    def _setup_widgets(self):
        frame = ttk.Frame(self, padding="15")
        frame.pack(expand=True, fill='both')

        fields = [
            ("Артикул:", "Article", 'entry', not bool(self.data)),
            ("Название:", "Name", 'entry'),
            ("Цена:", "Price", 'entry'),
            ("Скидка (%):", "Discount", 'entry'),
            ("Кол-во на складе:", "Quantity", 'entry'),
            ("Описание:", "Description", 'entry'),
            ("Фото (путь):", "Photo", 'entry'),
            ("Поставщик:", "ProviderName", 'combo', get_all_suppliers()),
            ("Производитель:", "ManufacturerName", 'combo', get_all_manufacturers()),
            ("Категория:", "CategoryName", 'combo', get_all_categories()),
        ]

        self.entries = {}
        for i, (label_text, key, widget_type, *args) in enumerate(fields):
            ttk.Label(frame, text=label_text).grid(row=i, column=0, sticky='w', pady=5)
            
            if widget_type == 'entry':
                entry = ttk.Entry(frame, width=35)
                entry.grid(row=i, column=1, sticky='ew', pady=5, padx=5)
                if not args or args[0] == False:
                     entry.configure(state='readonly')
                self.entries[key] = entry
            
            elif widget_type == 'combo':
                data = args[0]
                names = [row[1] for row in data]
                combo = ttk.Combobox(frame, values=names, width=33, state="readonly")
                combo.grid(row=i, column=1, sticky='ew', pady=5, padx=5)
                combo.data_map = {row[1]: row[0] for row in data}
                self.entries[key] = combo

        ttk.Button(frame, text="СОХРАНИТЬ", command=self._save_data).grid(row=len(fields), column=0, columnspan=2, pady=15, sticky='ew')
        frame.grid_columnconfigure(1, weight=1)

    def _load_data(self):
        for key, widget in self.entries.items():
            if key == "Article": continue
            value = self.data.get(key)
            if isinstance(widget, ttk.Combobox):
                widget.set(value)
            elif value is not None:
                widget.delete(0, tk.END)
                widget.insert(0, str(value))
        
        self.entries['Article'].configure(state='normal')
        self.entries['Article'].delete(0, tk.END)
        self.entries['Article'].insert(0, str(self.data['ProductArticle']))
        self.entries['Article'].configure(state='readonly')
        
    def _save_data(self):
        data = {}
        for key, widget in self.entries.items():
            if isinstance(widget, ttk.Entry):
                data[key] = widget.get()
            elif isinstance(widget, ttk.Combobox):
                selected_name = widget.get()
                data[key.replace('Name', 'ID')] = widget.data_map.get(selected_name)
        
        if not all([data['Article'], data['Name'], data['Price'], data['Discount'], data['Quantity']]):
            return messagebox.showerror("Ошибка", "Заполните все обязательные поля!")
            
        try:
            float(data['Price']), int(data['Discount']), int(data['Quantity'])
        except ValueError:
            return messagebox.showerror("Ошибка", "Цена, Скидка и Количество должны быть числами.")

        if self.article:
            query = """
            UPDATE Product SET Name=?, Unit='шт.', Price=?, Discount=?, Quantity=?, Description=?, Photo=?, ProviderID=?, ManufacturerID=?, CategoryID=? 
            WHERE ProductArticle=?
            """
            params = (data['Name'], float(data['Price']), int(data['Discount']), int(data['Quantity']), data['Description'], data['Photo'], data['ProviderID'], data['ManufacturerID'], data['CategoryID'], self.article)
        else:
            query = """
            INSERT INTO Product (ProductArticle, Name, Unit, Price, Discount, Quantity, Description, Photo, ProviderID, ManufacturerID, CategoryID)
            VALUES (?, ?, 'шт.', ?, ?, ?, ?, ?, ?, ?, ?)
            """
            params = (data['Article'], data['Name'], float(data['Price']), int(data['Discount']), int(data['Quantity']), data['Description'], data['Photo'], data['ProviderID'], data['ManufacturerID'], data['CategoryID'])
        
        success, _ = execute_query(query, params)
        
        if success:
            messagebox.showinfo("Успех", "Данные товара успешно сохранены.")
            if self.catalog_ref:
                self.catalog_ref.load_products()
            self.destroy()
        else:
            messagebox.showerror("Ошибка", "Ошибка сохранения данных в БД. Проверьте Артикул на уникальность (при добавлении).")


class OrderCRUDWindow(tk.Toplevel):
    def __init__(self, master, order_id=None, orders_ref=None):
        super().__init__(master)
        self.title(f"{'Редактирование' if order_id else 'Добавление'} заказа")
        self.geometry("800x600")
        self.configure(bg=COLOR_PRIMARY)
        self.order_id = order_id
        self.orders_ref = orders_ref
        
        self.order_data, self.product_list = get_order_details(order_id) if order_id else (None, [])
        self.product_list = [dict(item) for item in self.product_list]
        self.all_products_raw = execute_query("SELECT ProductArticle, Name FROM Product")
        self.product_map = {row['Name']: row['ProductArticle'] for row in self.all_products_raw}
        
        self._setup_style()
        self._setup_widgets()
        
    def _setup_style(self):
        style = ttk.Style(self)
        style.configure('.', font=(FONT_FAMILY, 10))
        style.configure('TFrame', background=COLOR_PRIMARY)
        style.configure('TLabel', background=COLOR_PRIMARY)
        style.configure('TButton', background=COLOR_ACCENT, foreground='black')

    def _setup_widgets(self):
        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(side='left', fill='y')

        fields = [
            ("ФИО клиента:", "ClientFIO", 'entry'),
            ("Код получения:", "Code", 'entry'),
            ("Дата заказа (ГГГГ-ММ-ДД):", "OrderDate", 'entry'),
            ("Дата доставки (ГГГГ-ММ-ДД):", "DeliveryDate", 'entry'),
            ("Статус:", "StatusID", 'combo', get_all_statuses()),
            ("Пункт выдачи:", "PointID", 'combo', get_all_pickup_points()),
        ]

        self.entries = {}
        for i, (label_text, key, widget_type, *args) in enumerate(fields):
            ttk.Label(main_frame, text=label_text).grid(row=i, column=0, sticky='w', pady=5)
            
            if widget_type == 'entry':
                entry = ttk.Entry(main_frame, width=25)
                entry.grid(row=i, column=1, sticky='ew', pady=5, padx=5)
                self.entries[key] = entry
            
            elif widget_type == 'combo':
                data = args[0]
                names = [row[1] for row in data]
                combo = ttk.Combobox(main_frame, values=names, width=23, state="readonly")
                combo.grid(row=i, column=1, sticky='ew', pady=5, padx=5)
                combo.data_map = {row[1]: row[0] for row in data}
                combo.id_to_name_map = {row[0]: row[1] for row in data}
                self.entries[key] = combo
                
        ttk.Button(main_frame, text="СОХРАНИТЬ ЗАКАЗ", command=self._save_order, style='TButton').grid(row=len(fields), column=0, columnspan=2, pady=15, sticky='ew')
        
        if self.order_id:
             ttk.Button(main_frame, text="УДАЛИТЬ ЗАКАЗ", command=self._delete_order, style='TButton').grid(row=len(fields) + 1, column=0, columnspan=2, pady=5, sticky='ew')

        # Состав заказа
        products_frame = ttk.Frame(self, padding="15")
        products_frame.pack(side='right', fill='both', expand=True)
        ttk.Label(products_frame, text="СОСТАВ ЗАКАЗА", font=(FONT_FAMILY, 12, 'bold')).pack(pady=10)

        self.products_tree = ttk.Treeview(products_frame, columns=('article', 'name', 'quantity'), show='headings')
        self.products_tree.heading('article', text='Артикул')
        self.products_tree.heading('name', text='Название')
        self.products_tree.heading('quantity', text='Кол-во')
        self.products_tree.pack(fill='both', expand=True)

        add_frame = ttk.Frame(products_frame)
        add_frame.pack(fill='x', pady=10)
        
        ttk.Label(add_frame, text="Товар:").pack(side='left')
        self.product_combo = ttk.Combobox(add_frame, values=list(self.product_map.keys()), width=30)
        self.product_combo.pack(side='left', padx=5)
        
        ttk.Label(add_frame, text="Кол-во:").pack(side='left')
        self.quantity_entry = ttk.Entry(add_frame, width=5)
        self.quantity_entry.insert(0, "1")
        self.quantity_entry.pack(side='left', padx=5)
        
        ttk.Button(add_frame, text="+", command=self._add_product_to_list, style='TButton').pack(side='left', padx=5)
        ttk.Button(add_frame, text="-", command=self._remove_product_from_list, style='TButton').pack(side='left')
        
        if self.order_id:
            self._load_data()
        else:
            self._update_products_tree()

    def _load_data(self):
        if self.order_data:
            for key, widget in self.entries.items():
                value = self.order_data.get(key)
                if isinstance(widget, ttk.Combobox):
                    widget.set(widget.id_to_name_map.get(value))
                elif value is not None:
                    widget.delete(0, tk.END)
                    widget.insert(0, str(value))
        
        self._update_products_tree()

    def _update_products_tree(self):
        for i in self.products_tree.get_children():
            self.products_tree.delete(i)
        
        for item in self.product_list:
            self.products_tree.insert('', 'end', 
                                      values=(item['ProductArticle'], item['Name'], item['Quantity']),
                                      tags=(item['ProductArticle'],))

    def _add_product_to_list(self):
        product_name = self.product_combo.get()
        quantity_str = self.quantity_entry.get()
        
        try:
            quantity = int(quantity_str)
        except ValueError:
            return messagebox.showerror("Ошибка", "Количество должно быть числом.")
            
        if product_name not in self.product_map or quantity <= 0:
            return messagebox.showerror("Ошибка", "Выберите товар и введите корректное количество.")
            
        article = self.product_map[product_name]
        
        exists = False
        for item in self.product_list:
            if item['ProductArticle'] == article:
                item['Quantity'] += quantity
                exists = True
                break
        
        if not exists:
            self.product_list.append({
                'ProductArticle': article,
                'Name': product_name,
                'Quantity': quantity
            })
            
        self._update_products_tree()

    def _remove_product_from_list(self):
        selected_item = self.products_tree.focus()
        if selected_item:
            article_to_remove = self.products_tree.item(selected_item)['tags'][0]
            self.product_list = [item for item in self.product_list if item['ProductArticle'] != article_to_remove]
            self._update_products_tree()
        else:
            messagebox.showwarning("Внимание", "Выберите товар для удаления.")

    def _save_order(self):
        data = {}
        for key, widget in self.entries.items():
            if isinstance(widget, ttk.Entry):
                data[key] = widget.get()
            elif isinstance(widget, ttk.Combobox):
                data[key] = widget.data_map.get(widget.get())
        
        if not all([data['ClientFIO'], data['OrderDate'], data['DeliveryDate'], data['StatusID'], data['PointID']]) or not self.product_list:
            return messagebox.showerror("Ошибка", "Заполните все основные поля и добавьте хотя бы один товар.")

        # Сохранение/Обновление основной таблицы Order
        if self.order_id:
            query = """
            UPDATE "Order" SET ClientFIO=?, Code=?, OrderDate=?, DeliveryDate=?, StatusID=?, PointID=? 
            WHERE OrderID=?
            """
            params = (data['ClientFIO'], data['Code'], data['OrderDate'], data['DeliveryDate'], data['StatusID'], data['PointID'], self.order_id)
            success, _ = execute_query(query, params)
            new_order_id = self.order_id
        else:
            query = """
            INSERT INTO "Order" (ClientFIO, Code, OrderDate, DeliveryDate, StatusID, PointID)
            VALUES (?, ?, ?, ?, ?, ?)
            """
            params = (data['ClientFIO'], data['Code'], data['OrderDate'], data['DeliveryDate'], data['StatusID'], data['PointID'])
            success, new_order_id = execute_query(query, params)
        
        if success:
            # Обновление состава заказа (OrderProduct)
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            try:
                cursor.execute('DELETE FROM OrderProduct WHERE OrderID = ?', (new_order_id,))
                insert_data = [(new_order_id, item['ProductArticle'], item['Quantity']) for item in self.product_list]
                cursor.executemany('INSERT INTO OrderProduct (OrderID, ProductArticle, Quantity) VALUES (?, ?, ?)', insert_data)
                conn.commit()
                
                messagebox.showinfo("Успех", "Данные заказа успешно сохранены.")
                if self.orders_ref:
                    self.orders_ref.load_orders()
                self.destroy()
            except sqlite3.Error as e:
                conn.rollback()
                messagebox.showerror("Ошибка", f"Ошибка сохранения состава заказа: {e}")
            finally:
                conn.close()
        else:
            messagebox.showerror("Ошибка", "Ошибка сохранения основных данных заказа.")

    def _delete_order(self):
        if messagebox.askyesno("Подтверждение", f"Вы уверены, что хотите удалить заказ ID: {self.order_id}?"):
            if execute_query("DELETE FROM \"Order\" WHERE OrderID = ?", (self.order_id,)):
                messagebox.showinfo("Успех", "Заказ удален.")
                if self.orders_ref:
                    self.orders_ref.load_orders()
                self.destroy()
            else:
                messagebox.showerror("Ошибка", "Не удалось удалить заказ.")
                
# --- 4. ОСНОВНЫЕ ОКНА ПРИЛОЖЕНИЯ ---

class AuthWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Окно входа - ООО «Обувь»")
        self.geometry("350x250")
        self.configure(bg=COLOR_PRIMARY)
        self.master = master

        style = ttk.Style(self)
        style.configure('.', font=(FONT_FAMILY, 10))
        style.configure('TFrame', background=COLOR_PRIMARY)
        style.configure('TButton', background=COLOR_ACCENT, foreground='black')

        frame = ttk.Frame(self, padding="20")
        frame.pack(expand=True, fill='both')

        ttk.Label(frame, text="АВТОРИЗАЦИЯ", font=(FONT_FAMILY, 14, 'bold'), background=COLOR_SECONDARY).pack(pady=10, fill='x')

        ttk.Label(frame, text="Логин:").pack(pady=5, anchor='w')
        self.login_entry = ttk.Entry(frame, width=30, font=(FONT_FAMILY, 10))
        self.login_entry.pack(pady=2)

        ttk.Label(frame, text="Пароль:").pack(pady=5, anchor='w')
        self.password_entry = ttk.Entry(frame, width=30, show='*', font=(FONT_FAMILY, 10))
        self.password_entry.pack(pady=2)

        ttk.Button(frame, text="ВОЙТИ", command=self.login, style='Accent.TButton').pack(pady=10)
        ttk.Button(frame, text="ПРОДОЛЖИТЬ КАК ГОСТЬ", command=self.open_guest_catalog, style='TButton').pack(pady=5)
        
        style.map('Accent.TButton', background=[('active', COLOR_ACCENT)])

    def login(self):
        login = self.login_entry.get()
        password = self.password_entry.get()
        
        # Для Администратора используйте логин/пароль из user_import:
        # 94d5ous@gmail.com / uzWC67
        
        role = authenticate_user(login, password)

        if role:
            self.destroy()
            CatalogWindow(self.master, role) 
        else:
            messagebox.showerror("Ошибка входа", "Неверный логин или пароль.")

    def open_guest_catalog(self):
        self.destroy()
        CatalogWindow(self.master, "Гость")


class CatalogWindow(tk.Toplevel):
    def __init__(self, master, role):
        super().__init__(master)
        self.title(f"Каталог товаров - Роль: {role}")
        self.geometry("1000x700")
        self.configure(bg=COLOR_PRIMARY)
        self.role = role

        style = ttk.Style(self)
        style.configure('.', font=(FONT_FAMILY, 10))
        style.configure('TFrame', background=COLOR_PRIMARY)
        style.configure('TButton', background=COLOR_ACCENT, foreground='black')
        
        self.search_entry = None
        self.category_var = tk.StringVar(self)
        self.sort_var = tk.StringVar(self)

        self.create_widgets()
        self.load_products()

    def create_widgets(self):
        top_frame = ttk.Frame(self, padding="10")
        top_frame.pack(fill='x')
        
        if self.role in ['Менеджер', 'Администратор']:
            ttk.Label(top_frame, text="Поиск:").pack(side='left', padx=(0, 5))
            self.search_entry = ttk.Entry(top_frame, width=20, font=(FONT_FAMILY, 10))
            self.search_entry.pack(side='left', padx=5)
            self.search_entry.bind('<Return>', lambda e: self.load_products())
            
            categories = ["Все категории"] + [row[1] for row in get_all_categories()]
            self.category_var.set("Все категории")
            category_menu = ttk.OptionMenu(top_frame, self.category_var, self.category_var.get(), *categories, command=lambda e: self.load_products())
            category_menu.pack(side='left', padx=5)
            
            self.sort_var.set("По возрастанию скидки")
            sort_options = ["По возрастанию скидки", "По убыванию скидки"]
            sort_menu = ttk.OptionMenu(top_frame, self.sort_var, self.sort_var.get(), *sort_options, command=lambda e: self.load_products())
            sort_menu.pack(side='left', padx=5)

            if self.role == 'Администратор':
                ttk.Button(top_frame, text="ДОБАВИТЬ ТОВАР", command=self.open_product_crud, style='TButton').pack(side='right', padx=5)
                
            ttk.Button(top_frame, text="ЗАКАЗЫ", command=self.open_orders_window, style='TButton').pack(side='right', padx=15)
        
        self.products_frame = ttk.Frame(self, padding="10")
        self.products_frame.pack(expand=True, fill='both')
        
    def load_products(self):
        for widget in self.products_frame.winfo_children():
            widget.destroy()

        category_filter = self.category_var.get() if self.role in ['Менеджер', 'Администратор'] and self.category_var.get() != "Все категории" else None
        search_query = self.search_entry.get() if self.role in ['Менеджер', 'Администратор'] and self.search_entry else None
        sort_order = 'DESC' if self.role in ['Менеджер', 'Администратор'] and self.sort_var.get() == "По убыванию скидки" else 'ASC'
        
        products = self._get_products_from_db(self.role, category_filter, sort_order, search_query)
        
        for i, product in enumerate(products):
            item_frame = ttk.Frame(self.products_frame, relief=tk.SOLID, borderwidth=1, padding=5)
            item_frame.grid(row=i, column=0, sticky='ew', padx=5, pady=5)
            
            background_color = COLOR_PRIMARY
            if product['Discount'] > 15:
                background_color = COLOR_DISCOUNT_HIGH
                style_name = f'Discount{i}.TFrame'
                style = ttk.Style(self)
                style.configure(style_name, background=background_color)
                item_frame.configure(style=style_name)

            ttk.Label(item_frame, text="[Фото]", width=10, background=background_color).pack(side='left', padx=10)

            info_text = (
                f"Название: {product['Name']} | Артикул: {product['ProductArticle']}\n"
                f"Описание: {product['Description'][:50]}...\n"
                f"Категория: {product['CategoryName']}\n"
                f"Цена: {product['Price'] * (1 - product['Discount'] / 100):.2f} руб. (Скидка: {product['Discount']}%)"
            )
            ttk.Label(item_frame, text=info_text, justify='left', background=background_color).pack(side='left', fill='x', expand=True)
            
            if self.role == 'Администратор':
                crud_frame = ttk.Frame(item_frame, background=background_color)
                crud_frame.pack(side='right')
                ttk.Button(crud_frame, text="Ред.", command=lambda art=product['ProductArticle']: self.open_product_crud(art), style='TButton', width=5).pack(pady=2)
                ttk.Button(crud_frame, text="Удал.", command=lambda art=product['ProductArticle']: self.delete_product(art), style='TButton', width=5).pack(pady=2)

        self.products_frame.grid_columnconfigure(0, weight=1)

    def _get_products_from_db(self, role_name, category_filter=None, sort_order='ASC', search_query=None):
        base_query = """
        SELECT 
            T1.ProductArticle, T1.Name, T1.Price, T1.Discount, T1.Quantity, T1.Description, T1.Photo, 
            T3.CategoryName
        FROM Product AS T1
        INNER JOIN Category AS T3 ON T1.CategoryID = T3.CategoryID
        """
        conditions, params, order_by = [], [], ""
        
        if role_name in ['Менеджер', 'Администратор']:
            if category_filter:
                conditions.append("T3.CategoryName = ?")
                params.append(category_filter)
                
            if search_query:
                conditions.append("(T1.Name LIKE ? OR T1.Description LIKE ?)")
                params.extend([f'%{search_query}%', f'%{search_query}%'])
                
            order_by = f"ORDER BY T1.Discount {sort_order}"
        
        if conditions:
            base_query += " WHERE " + " AND ".join(conditions)
            
        final_query = base_query + " " + order_by
        
        return execute_query(final_query, params)

    def open_product_crud(self, product_article=None):
        ProductCRUDWindow(self.master, article=product_article, catalog_ref=self)

    def delete_product(self, article):
        if messagebox.askyesno("Подтверждение", f"Вы уверены, что хотите удалить товар {article}?"):
            if execute_query("DELETE FROM Product WHERE ProductArticle=?", (article,)):
                 messagebox.showinfo("Успех", "Товар удален.")
            else:
                 messagebox.showerror("Ошибка", "Не удалось удалить товар. Проверьте, не связан ли он с заказами.")
            self.load_products()

    def open_orders_window(self):
        OrdersWindow(self.master, self.role)


class OrdersWindow(tk.Toplevel):
    def __init__(self, master, role):
        super().__init__(master)
        self.title(f"Список Заказов - Роль: {role}")
        self.geometry("1100x600")
        self.configure(bg=COLOR_PRIMARY)
        self.role = role

        style = ttk.Style(self)
        style.configure('TButton', background=COLOR_ACCENT, foreground='black')
        
        top_frame = ttk.Frame(self, padding=10)
        top_frame.pack(fill='x')

        if self.role == 'Администратор':
            ttk.Button(top_frame, text="ДОБАВИТЬ ЗАКАЗ", command=self.open_order_crud, style='TButton').pack(side='right', padx=5)
            
        ttk.Button(top_frame, text="ОБНОВИТЬ", command=self.load_orders, style='TButton').pack(side='left', padx=5)

        self.tree = ttk.Treeview(self, columns=('status', 'point', 'date_order', 'date_delivery', 'articles'), show='headings')
        self.tree.heading('status', text='Статус заказа')
        self.tree.heading('point', text='Адрес пункта выдачи')
        self.tree.heading('date_order', text='Дата заказа')
        self.tree.heading('date_delivery', text='Дата доставки')
        self.tree.heading('articles', text='Состав заказа')
        
        self.tree.column('status', width=100)
        self.tree.column('point', width=150)
        self.tree.column('date_order', width=120)
        self.tree.column('date_delivery', width=120)
        self.tree.column('articles', width=450)
        
        self.tree.pack(expand=True, fill='both', padx=10, pady=5)
        
        if self.role == 'Администратор':
            self.tree.bind('<Double-1>', self.on_order_select)
        
        self.load_orders()

    def load_orders(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
            
        query = """
        SELECT 
            T1.OrderID,
            T4.StatusName,
            T3.Address,
            T1.OrderDate,
            T1.DeliveryDate,
            GROUP_CONCAT(T2.ProductArticle || ' (' || T2.Quantity || ' шт.)', ' / ') AS ArticlesList
        FROM "Order" AS T1
        INNER JOIN OrderProduct AS T2 ON T1.OrderID = T2.OrderID
        INNER JOIN PickupPoint AS T3 ON T1.PointID = T3.PointID
        INNER JOIN OrderStatus AS T4 ON T1.StatusID = T4.StatusID
        GROUP BY T1.OrderID
        ORDER BY T1.OrderID DESC;
        """
        orders = execute_query(query)
        
        if orders:
            for order in orders:
                self.tree.insert('', 'end', 
                                 iid=order['OrderID'], 
                                 values=(
                                     order['StatusName'],
                                     order['Address'],
                                     order['OrderDate'],
                                     order['DeliveryDate'],
                                     order['ArticlesList']
                                 ))
                                 
    def on_order_select(self, event):
        selected_item = self.tree.focus()
        if selected_item:
            order_id = self.tree.item(selected_item)['iid']
            self.open_order_crud(order_id)
            
    def open_order_crud(self, order_id=None):
        OrderCRUDWindow(self.master, order_id=order_id, orders_ref=self)
        
# --- 5. ЗАПУСК ПРИЛОЖЕНИЯ ---

if __name__ == '__main__':
    root = tk.Tk()
    root.withdraw()
    
    root.option_add("*Font", (FONT_FAMILY, 10))

    AuthWindow(root)
    
    root.mainloop()