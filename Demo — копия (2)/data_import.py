import sqlite3
import pandas as pd
import os

# --- 1. КОНСТАНТЫ И ФАЙЛЫ ---
DATABASE = 'demodb.db'
# Файлы для импорта: (имя_файла, имя_ключевого_столбца)
IMPORT_FILES = {
    'users': ('user_import.xlsx - Лист1.csv', 'Роль сотрудника'),
    'products': ('Tovar.xlsx - Лист1.csv', 'Артикул'), 
    'points': ('Пункты выдачи_import.xlsx - Лист1.csv', None), 
    'orders': ('Заказ_import.xlsx - Лист1.csv', 'Номер заказа'), 
}

# --- 2. УТИЛИТЫ ДЛЯ БАЗЫ ДАННЫХ ---

def create_tables(db):
    """Создает необходимые таблицы в базе данных."""
    cursor = db.cursor()
    
    # Таблицы для ролей и пользователей
    cursor.execute("CREATE TABLE IF NOT EXISTS Role (RoleID INTEGER PRIMARY KEY AUTOINCREMENT, RoleName TEXT UNIQUE NOT NULL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS User (UserID INTEGER PRIMARY KEY AUTOINCREMENT, FullName TEXT NOT NULL, Login TEXT UNIQUE NOT NULL, Password TEXT NOT NULL, RoleID INTEGER, FOREIGN KEY (RoleID) REFERENCES Role(RoleID))")
    
    # Таблицы для каталога и связей
    cursor.execute("CREATE TABLE IF NOT EXISTS Category (CategoryID INTEGER PRIMARY KEY AUTOINCREMENT, CategoryName TEXT UNIQUE NOT NULL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS Supplier (SupplierID INTEGER PRIMARY KEY AUTOINCREMENT, SupplierName TEXT UNIQUE NOT NULL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS Manufacturer (ManufacturerID INTEGER PRIMARY KEY AUTOINCREMENT, ManufacturerName TEXT UNIQUE NOT NULL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS Product (ProductID INTEGER PRIMARY KEY AUTOINCREMENT, ProductArticle TEXT UNIQUE NOT NULL, Name TEXT NOT NULL, Unit TEXT, Price REAL, Discount INTEGER, Quantity INTEGER, Description TEXT, Photo TEXT, CategoryID INTEGER, SupplierID INTEGER, ManufacturerID INTEGER, FOREIGN KEY (CategoryID) REFERENCES Category(CategoryID), FOREIGN KEY (SupplierID) REFERENCES Supplier(SupplierID), FOREIGN KEY (ManufacturerID) REFERENCES Manufacturer(ManufacturerID))")
    
    # Таблицы для заказов и пунктов выдачи
    cursor.execute("CREATE TABLE IF NOT EXISTS PickupPoint (PointID INTEGER PRIMARY KEY AUTOINCREMENT, Address TEXT UNIQUE NOT NULL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS OrderStatus (StatusID INTEGER PRIMARY KEY AUTOINCREMENT, StatusName TEXT UNIQUE NOT NULL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS \"Order\" (OrderID INTEGER PRIMARY KEY, OrderDate DATE, DeliveryDate DATE, PickupCode TEXT, UserID INTEGER, PointID INTEGER, StatusID INTEGER, FOREIGN KEY (UserID) REFERENCES User(UserID), FOREIGN KEY (PointID) REFERENCES PickupPoint(PointID), FOREIGN KEY (StatusID) REFERENCES OrderStatus(StatusID))")
    cursor.execute("CREATE TABLE IF NOT EXISTS OrderProduct (OrderProductID INTEGER PRIMARY KEY AUTOINCREMENT, OrderID INTEGER, ProductArticle TEXT, Quantity INTEGER, FOREIGN KEY (OrderID) REFERENCES \"Order\"(OrderID), FOREIGN KEY (ProductArticle) REFERENCES Product(ProductArticle))")
    
    db.commit()

# --- 3. ФУНКЦИИ ИМПОРТА ДАННЫХ ---

def read_file_safe(file_path, header=0):
    """
    Умная функция для чтения файлов - пробует разные форматы
    """
    # Сначала пробуем как Excel
    try:
        print(f"Попытка чтения {file_path} как Excel...")
        df = pd.read_excel(file_path, header=header, engine='openpyxl')
        if not df.empty:
            print(f"Успешно прочитано как Excel. Колонок: {len(df.columns)}")
            return df
    except Exception as e:
        print(f"Не удалось прочитать как Excel: {e}")
    
    # Если не получилось, пробуем как CSV с разными кодировками и разделителями
    encodings = ['utf-8-sig', 'cp1251', 'utf-8']
    separators = [',', ';', '\t']
    
    for encoding in encodings:
        for sep in separators:
            try:
                print(f"Попытка чтения {file_path} как CSV (enc={encoding}, sep={repr(sep)})...")
                df = pd.read_csv(file_path, encoding=encoding, sep=sep, header=header, engine='python')
                if not df.empty and len(df.columns) > 1:
                    print(f"Успешно прочитано как CSV. Колонок: {len(df.columns)}")
                    return df
            except Exception as e:
                continue
    
    print(f"Не удалось прочитать файл {file_path} ни одним способом")
    return None

def import_roles_and_users(db, file_path):
    """Импортирует роли и пользователей."""
    df = read_file_safe(file_path)
    if df is None or df.empty:
        print(f"Не удалось загрузить данные из {file_path}")
        return
    
    # Пробуем разные варианты названий столбцов
    possible_role_columns = ['Роль сотрудника', 'Роль', 'Role']
    possible_name_columns = ['ФИО', 'ФИО сотрудника', 'FullName', 'Name']
    possible_login_columns = ['Логин', 'Login', 'UserLogin']
    possible_password_columns = ['Пароль', 'Password', 'UserPassword']
    
    # Находим правильные названия столбцов
    role_col = None
    name_col = None
    login_col = None
    password_col = None
    
    for col in possible_role_columns:
        if col in df.columns:
            role_col = col
            break
    
    for col in possible_name_columns:
        if col in df.columns:
            name_col = col
            break
            
    for col in possible_login_columns:
        if col in df.columns:
            login_col = col
            break
            
    for col in possible_password_columns:
        if col in df.columns:
            password_col = col
            break
    
    if not all([role_col, name_col, login_col, password_col]):
        print(f"Не все необходимые колонки найдены в файле {file_path}")
        print(f"Доступные колонки: {list(df.columns)}")
        return
    
    cursor = db.cursor()
    
    try:
        # 1. Заполнение таблицы Role
        roles = df[role_col].astype(str).str.strip().unique()
        for role in roles:
            if role and role != 'nan': 
                cursor.execute("INSERT OR IGNORE INTO Role (RoleName) VALUES (?)", (role,))
        db.commit()
        
        # Кэширование RoleID
        role_map = {}
        for name in roles:
            if name and name != 'nan':
                result = cursor.execute("SELECT RoleID FROM Role WHERE RoleName=?", (name,)).fetchone()
                if result:
                    role_map[name] = result[0]
        
        # 2. Заполнение таблицы User
        inserted_count = 0
        for index, row in df.iterrows():
            role_name = str(row[role_col]).strip()
            if not role_name or role_name == 'nan':
                continue
                
            user_data = (
                str(row[name_col]).strip(),
                str(row[login_col]).strip(),
                str(row[password_col]).strip(),
                role_map.get(role_name)
            )
            
            # Проверяем, что все данные есть
            if all(user_data[:3]):  # Проверяем ФИО, Логин, Пароль
                cursor.execute("""
                    INSERT OR IGNORE INTO User (FullName, Login, Password, RoleID) 
                    VALUES (?, ?, ?, ?)
                """, user_data)
                inserted_count += cursor.rowcount
            
        db.commit()
        print(f"Импорт пользователей из {file_path} успешен. Вставлено {inserted_count} записей.")
    except Exception as e:
        print(f"Ошибка при импорте пользователей: {e}")
        db.rollback()

def import_pickup_points(db, file_path):
    """Импортирует пункты выдачи."""
    df = read_file_safe(file_path, header=None)
    if df is None or df.empty:
        print(f"Не удалось загрузить данные из {file_path}")
        return

    cursor = db.cursor()
    inserted_count = 0
    
    try:
        # Пробуем разные столбцы для адреса
        for col_index in range(min(3, len(df.columns))):
            for index, row in df.iterrows():
                address = str(row[col_index]).strip().strip('"').strip("'")
                if address and address != 'nan' and len(address) > 3:
                    cursor.execute("INSERT OR IGNORE INTO PickupPoint (Address) VALUES (?)", (address,))
                    inserted_count += cursor.rowcount
        
        db.commit()
        print(f"Импорт пунктов выдачи из {file_path} успешен. Вставлено {inserted_count} записей.")
    except Exception as e:
        print(f"Ошибка при импорте пунктов выдачи: {e}")
        db.rollback()

def import_products(db, file_path):
    """Импортирует товары, категории, поставщиков и производителей."""
    df = read_file_safe(file_path)
    if df is None or df.empty:
        print(f"Не удалось загрузить данные из {file_path}")
        return
    
    inserted_rows = 0
    total_rows = 0
    
    # --- Вспомогательные функции для безопасного импорта ---
    def get_or_create_id(table_name, name_column, name_value, cache_map, cursor, db):
        if not name_value: return None
        name_value = name_value.strip()
        if not name_value: return None
        if name_value not in cache_map:
            cursor.execute(f"INSERT OR IGNORE INTO {table_name} ({name_column}) VALUES (?)", (name_value,))
            db.commit() 
            id_val = cursor.execute(f"SELECT {table_name}ID FROM {table_name} WHERE {name_column}=?", (name_value,)).fetchone()
            if id_val:
                cache_map[name_value] = id_val[0]
                return id_val[0]
            return None
        return cache_map[name_value]

    def safe_float(val):
        try:
            return float(str(val).replace(',', '.').strip())
        except ValueError:
            return 0.0

    def safe_int(val):
        try:
            return int(safe_float(val))
        except (ValueError, TypeError):
            return 0
    # --- Конец вспомогательных функций ---

    # Подготовка словарей для кэширования ID
    category_map = {}
    supplier_map = {}
    manufacturer_map = {}
    
    try:
        cursor = db.cursor()
        
        for index, row in df.iterrows():
            total_rows += 1
            
            # 1. Получение связанных ID 
            try:
                category_name = str(row['Категория товара']).strip()
                supplier_name = str(row['Поставщик']).strip()
                manufacturer_name = str(row['Производитель']).strip()
                
                category_id = get_or_create_id('Category', 'CategoryName', category_name, category_map, cursor, db)
                supplier_id = get_or_create_id('Supplier', 'SupplierName', supplier_name, supplier_map, cursor, db)
                manufacturer_id = get_or_create_id('Manufacturer', 'ManufacturerName', manufacturer_name, manufacturer_map, cursor, db)
            except KeyError as e:
                print(f"Ошибка ключа: {e}. Пропускаем строку {index}.")
                continue
            
            # Пропускаем, если не удалось установить связь
            if not all([category_id, supplier_id, manufacturer_id]):
                print(f"Не удалось получить ID для категории, поставщика или производителя в строке {index}. Пропускаем.")
                continue

            # 2. Очистка и преобразование данных товара
            try:
                article = str(row['Артикул']).strip()
                
                price = safe_float(row['Цена'])
                discount = safe_int(row['Действующая скидка'])
                quantity = safe_int(row['Кол-во на складе'])

                product_data = (
                    article, 
                    str(row['Наименование товара']).strip(), 
                    str(row['Единица измерения']).strip(), 
                    price, 
                    discount, 
                    quantity, 
                    str(row['Описание товара']).strip(), 
                    str(row['Фото']).strip(),
                    category_id, supplier_id, manufacturer_id
                )
            except KeyError as e:
                print(f"Ошибка ключа в данных товара: {e}. Пропускаем строку {index}.")
                continue

            # 3. Вставка товара
            cursor.execute("""
                INSERT OR IGNORE INTO Product (
                    ProductArticle, Name, Unit, Price, Discount, Quantity, 
                    Description, Photo, CategoryID, SupplierID, ManufacturerID
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, product_data)
            
            inserted_rows += 1
            
        db.commit()
        print(f"Импорт товаров из {file_path} успешен. Вставлено {inserted_rows}/{total_rows} строк.")
        
    except Exception as e:
        print(f"Ошибка при импорте товаров: {e}")
        db.rollback()

def import_orders(db, file_path):
    """Импортирует заказы и детали заказов."""
    df = read_file_safe(file_path)
    if df is None or df.empty:
        print(f"Не удалось загрузить данные из {file_path}")
        return
    
    cursor = db.cursor()
    inserted_count = 0
    
    try:
        # Кэширование ID
        user_map = {row[0].strip(): row[1] 
                    for row in cursor.execute("SELECT FullName, UserID FROM User").fetchall()}
        
        # 1. Заполнение таблицы OrderStatus
        COL_STATUS = 'Статус заказа'
        if COL_STATUS not in df.columns:
            raise KeyError(f"Колонка '{COL_STATUS}' не найдена в файле заказов. Доступные: {list(df.columns)}")

        statuses = df[COL_STATUS].str.strip().unique()
        for status in statuses:
            if status:
                cursor.execute("INSERT OR IGNORE INTO OrderStatus (StatusName) VALUES (?)", (status,))
        db.commit()
        status_map = {name: cursor.execute("SELECT StatusID FROM OrderStatus WHERE StatusName=?", (name,)).fetchone()[0]
                      for name in statuses if name}

        # 2. Заполнение таблицы Order и OrderProduct
        for index, row in df.iterrows():
            
            user_fullname = str(row['ФИО авторизированного клиента']).strip()
            # Адрес пункта выдачи - это PointID, которое уже импортировано. 
            point_id = int(str(row['Адрес пункта выдачи']).strip()) 
            status_name = str(row[COL_STATUS]).strip()
            
            user_id = user_map.get(user_fullname)
            status_id = status_map.get(status_name)
            
            # Пропускаем, если не нашли связанных данных
            if not user_id or not status_id: 
                print(f"Не найден user_id или status_id для заказа {row['Номер заказа']}. Пропускаем.")
                continue 
            
            # Вставка Заказа
            order_data = (
                int(row['Номер заказа']),
                str(row['Дата заказа']).strip(),
                str(row['Дата доставки']).strip(),
                str(row['Код для получения']).strip(),
                user_id,
                point_id, 
                status_id
            )
            cursor.execute("""
                INSERT OR IGNORE INTO "Order" (OrderID, OrderDate, DeliveryDate, PickupCode, UserID, PointID, StatusID)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, order_data)
            
            inserted_count += cursor.rowcount
            order_id = int(row['Номер заказа'])

            # Парсинг Артикулов заказа
            # Артикул заказа - это строка вида: "Артикул1, Количество1, Артикул2, Количество2, ..."
            articles_quantities = str(row['Артикул заказа']).split(',')
            
            for i in range(0, len(articles_quantities), 2):
                if i + 1 < len(articles_quantities):
                    article = articles_quantities[i].strip().strip('"') # Очистка от кавычек
                    quantity = articles_quantities[i+1].strip().strip('"')
                    
                    try:
                        quantity_int = int(quantity)
                        cursor.execute("""
                            INSERT INTO OrderProduct (OrderID, ProductArticle, Quantity)
                            VALUES (?, ?, ?)
                        """, (order_id, article, quantity_int))
                    except ValueError:
                        pass # Игнорируем неверные пары Артикул/Количество

        db.commit()
        print(f"Импорт заказов из {file_path} успешен. Вставлено {inserted_count} заказов.")
    except Exception as e:
        print(f"Ошибка при импорте заказов: {e}")
        db.rollback()

# --- 4. ОСНОВНАЯ ФУНКЦИЯ ЗАПУСКА ---

def main():
    """Главная функция для создания базы данных и импорта данных."""
    # Сначала проверим, какие файлы есть в папке
    print("=== Поиск файлов в текущей директории ===")
    files_in_dir = os.listdir('.')
    csv_files = [f for f in files_in_dir if 'csv' in f.lower() or 'xlsx' in f.lower()]
    print("Найдены файлы:", csv_files)
    
    # Удаляем старую базу, чтобы начать с чистого листа
    if os.path.exists(DATABASE):
        os.remove(DATABASE)
        
    conn = None
    try:
        conn = sqlite3.connect(DATABASE)
        conn.create_function("TRIM", 1, lambda s: s.strip() if isinstance(s, str) else s)

        # 1. Создание таблиц
        print("\n=== Создание таблиц ===")
        create_tables(conn)
        
        # 2. Последовательный импорт данных
        print("\n=== Импорт данных ===")
        
        # Проверяем существование файлов перед импортом
        for file_type, (filename, _) in IMPORT_FILES.items():
            if os.path.exists(filename):
                print(f"Файл {filename} найден")
            else:
                print(f"ВНИМАНИЕ: Файл {filename} не найден!")
        
        import_roles_and_users(conn, IMPORT_FILES['users'][0])
        import_pickup_points(conn, IMPORT_FILES['points'][0])
        import_products(conn, IMPORT_FILES['products'][0])
        import_orders(conn, IMPORT_FILES['orders'][0])
        
        print(f"\nБаза данных {DATABASE} успешно создана и заполнена.")
        
    except sqlite3.Error as e:
        print(f"Критическая ошибка при работе с базой данных: {e}")
    except Exception as e:
        print(f"Непредвиденная ошибка: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    main()