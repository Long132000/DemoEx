import sqlite3
import pandas as pd
import csv
import re
import io
import os

# --- КОНСТАНТЫ ИМПОРТА (Возвращаем оригинальные имена .csv) ---
DB_NAME = 'demodb.db'
# Имена файлов, как они были экспортированы из Excel
FILE_TOVAR = 'Tovar.xlsx - Лист1.csv'
FILE_USERS = 'user_import.xlsx - Лист1.csv'
FILE_POINTS = 'Пункты выдачи_import.xlsx - Лист1.csv'
FILE_ORDERS = 'Заказ_import.xlsx - Лист1.csv'

# --- 1. Утилиты для чтения (Принудительное чтение CP1251 с заменой ошибок) ---
def read_csv_robust(filename, sep=',', header_row='infer', quoting=csv.QUOTE_MINIMAL):
    """
    Читает CSV, принудительно используя 'cp1251' с заменой ошибок ('replace')
    и 'python' engine для обработки "грязных" строк.
    """
    print(f"Попытка чтения {filename} (cp1251, replace errors, python engine)...")
    try:
        df = pd.read_csv(
            filename, 
            sep=sep, 
            encoding='cp1251',         # 1. Используем русскую кодировку
            encoding_errors='replace',  # 2. Заменяем "грязные" байты (как 0x98)
            engine='python',          # 3. Используем надежный движок
            on_bad_lines='skip',      # 4. Пропускаем строки с неверным числом полей
            quoting=quoting, 
            header=0 if header_row=='infer' else None
        )
        
        if df.empty or df.columns.empty:
            print(f"Файл {filename} пуст или не удалось прочитать.")
            return pd.DataFrame()

        print(f"Успешно прочитано (cp1251, replace).")
        # Очистка заголовков
        if header_row != None:
            df.columns = [col.strip() for col in df.columns]
        return df
        
    except FileNotFoundError:
        print(f"!!! ОШИБКА: Файл {filename} не найден.")
        return pd.DataFrame()
    except Exception as e:
        print(f"!!! КРИТИЧЕСКАЯ ОШИБКА при чтении файла {filename}: {e}")
        return pd.DataFrame()

# --- 2. SQL Утилиты ---
def get_map(table, id_col, name_col, cursor):
    """Создает словарь {Name: ID} для справочных таблиц, очищая ключи."""
    query = f"SELECT {id_col}, {name_col} FROM {table}"
    data = cursor.execute(query).fetchall()
    return {str(row[1]).strip(): row[0] for row in data if row[1] is not None}

# --- 3. Исполнение скрипта (СХЕМА и СТАТИЧЕСКИЕ ДАННЫЕ) ---
conn = sqlite3.connect(DB_NAME)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

cursor.executescript("""
    -- Удаление таблиц
    DROP TABLE IF EXISTS OrderProduct; DROP TABLE IF EXISTS "Order"; DROP TABLE IF EXISTS Product;
    DROP TABLE IF EXISTS User; DROP TABLE IF EXISTS PickupPoint; DROP TABLE IF EXISTS Category;
    DROP TABLE IF EXISTS Provider; DROP TABLE IF EXISTS Manufacturer; DROP TABLE IF EXISTS Role;
    DROP TABLE IF EXISTS OrderStatus;
    
    -- Создание таблиц
    CREATE TABLE Role (RoleID INTEGER PRIMARY KEY, RoleName TEXT NOT NULL UNIQUE);
    CREATE TABLE User (UserID INTEGER PRIMARY KEY, FIO TEXT, Login TEXT NOT NULL UNIQUE, Password TEXT NOT NULL, RoleID INTEGER NOT NULL, FOREIGN KEY (RoleID) REFERENCES Role(RoleID));
    CREATE TABLE PickupPoint (PointID INTEGER PRIMARY KEY, Address TEXT NOT NULL UNIQUE);
    CREATE TABLE Category (CategoryID INTEGER PRIMARY KEY, CategoryName TEXT NOT NULL UNIQUE);
    CREATE TABLE Provider (ProviderID INTEGER PRIMARY KEY, ProviderName TEXT NOT NULL UNIQUE);
    CREATE TABLE Manufacturer (ManufacturerID INTEGER PRIMARY KEY, ManufacturerName TEXT NOT NULL UNIQUE);
    CREATE TABLE Product (ProductArticle TEXT PRIMARY KEY, Name TEXT, Unit TEXT, Price REAL, Discount INTEGER, Quantity INTEGER, Description TEXT, Photo TEXT, ProviderID INTEGER, ManufacturerID INTEGER, CategoryID INTEGER, FOREIGN KEY (ProviderID) REFERENCES Provider(ProviderID), FOREIGN KEY (ManufacturerID) REFERENCES Manufacturer(ManufacturerID), FOREIGN KEY (CategoryID) REFERENCES Category(CategoryID));
    CREATE TABLE OrderStatus (StatusID INTEGER PRIMARY KEY, StatusName TEXT NOT NULL UNIQUE);
    CREATE TABLE "Order" (OrderID INTEGER PRIMARY KEY, OrderDate DATE, DeliveryDate DATE, PointID INTEGER, ClientFIO TEXT, Code INTEGER, StatusID INTEGER, FOREIGN KEY (PointID) REFERENCES PickupPoint(PointID), FOREIGN KEY (StatusID) REFERENCES OrderStatus(StatusID));
    CREATE TABLE OrderProduct (OrderID INTEGER NOT NULL, ProductArticle TEXT NOT NULL, Quantity INTEGER NOT NULL, PRIMARY KEY (OrderID, ProductArticle), FOREIGN KEY (OrderID) REFERENCES "Order"(OrderID) ON DELETE CASCADE, FOREIGN KEY (ProductArticle) REFERENCES Product(ProductArticle));
    
    -- Инициализация базовых данных
    INSERT OR IGNORE INTO Role (RoleID, RoleName) VALUES (1, 'Администратор'), (2, 'Менеджер'), (3, 'Авторизированный клиент'), (4, 'Гость');
    INSERT OR IGNORE INTO OrderStatus (StatusID, StatusName) VALUES (1, 'Новый'), (2, 'В сборке'), (3, 'Доставлен в ПВЗ'), (4, 'Завершен'), (5, 'Отменен');
""")
conn.commit()

# --- 4. Импорт данных ---
role_map = get_map('Role', 'RoleID', 'RoleName', cursor)

# 4.1. Users
try:
    df_users = read_csv_robust(FILE_USERS, sep=',', quoting=csv.QUOTE_MINIMAL)
    
    if not df_users.empty:
        for index, row in df_users.iterrows():
            login = str(row.get('Логин', '')).strip()
            role_name = str(row.get('Роль сотрудника', '')).strip()
            role_id = role_map.get(role_name, role_map.get('Авторизированный клиент')) 
            
            if login and role_id:
                cursor.execute("""
                    INSERT OR IGNORE INTO User (FIO, Login, Password, RoleID)
                    VALUES (?, ?, ?, ?)
                """, (str(row.get('ФИО', '')).strip(), login, str(row.get('Пароль', '')).strip(), role_id))
        conn.commit()
        print(f"Импорт пользователей из {FILE_USERS} успешен.")
    else:
        print(f"Пропуск импорта пользователей: {FILE_USERS} пуст или нечитаем.")

except Exception as e:
    print(f"Критическая ошибка при импорте пользователей из {FILE_USERS}: {e}")

# 4.2. Points
try:
    # QUOTE_NONE для этого файла, т.к. каждая строка - это одно цитированное поле без заголовка
    df_points = read_csv_robust(FILE_POINTS, sep=',', header_row=None, quoting=csv.QUOTE_NONE)
    
    if not df_points.empty and df_points.shape[1] > 0:
        # Форсируем к строковому типу и очищаем
        addresses = df_points.iloc[:, 0].astype(str).str.strip().str.strip('"')

        for address in addresses:
            if address:
                cursor.execute("INSERT OR IGNORE INTO PickupPoint (Address) VALUES (?)", (address,))
        
        conn.commit()
        print(f"Импорт пунктов выдачи из {FILE_POINTS} успешен.")
    else:
        print(f"Пропуск импорта пунктов выдачи: {FILE_POINTS} пуст или нечитаем.")
        
except Exception as e:
    print(f"Критическая ошибка при импорте пунктов выдачи из {FILE_POINTS}: {e}")

# 4.3. Products and References
try:
    df_tovar = read_csv_robust(FILE_TOVAR, sep=',', quoting=csv.QUOTE_MINIMAL)

    if not df_tovar.empty:
        # Import References
        for col, table, name_col in [
            ('Категория товара', 'Category', 'CategoryName'), 
            ('Поставщик', 'Provider', 'ProviderName'), 
            ('Производитель', 'Manufacturer', 'ManufacturerName')
        ]:
            # Проверяем, существует ли столбец, прежде чем его использовать
            if col in df_tovar.columns:
                unique_values = df_tovar[col].dropna().unique()
                for name in unique_values:
                    cursor.execute(f"INSERT OR IGNORE INTO {table} ({name_col}) VALUES (?)", (str(name).strip(),))
        conn.commit()

        # Get Maps
        category_map = get_map('Category', 'CategoryID', 'CategoryName', cursor)
        provider_map = get_map('Provider', 'ProviderID', 'ProviderName', cursor)
        manufacturer_map = get_map('Manufacturer', 'ManufacturerID', 'ManufacturerName', cursor)

        # Import Products
        for index, row in df_tovar.iterrows():
            try:
                article = str(row.get('Артикул', '')).strip()
                if not article: continue
                    
                price_str = str(row.get('Цена', 0)).replace(',', '.') 
                
                # Безопасное преобразование типов
                price = float(price_str) if price_str and price_str.replace('.', '', 1).isdigit() else 0.0
                discount = int(row.get('Действующая скидка', 0)) if str(row.get('Действующая скидка', 0)).strip().isdigit() else 0
                quantity = int(row.get('Кол-во на складе', 0)) if str(row.get('Кол-во на складе', 0)).strip().isdigit() else 0
                
                cursor.execute("""
                    INSERT OR REPLACE INTO Product 
                    (ProductArticle, Name, Unit, Price, Discount, Quantity, Description, Photo, ProviderID, ManufacturerID, CategoryID)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    article,
                    str(row.get('Наименование товара', '')).strip(),
                    str(row.get('Единица измерения', '')).strip(),
                    price, 
                    discount,
                    quantity,
                    str(row.get('Описание товара', '')).strip(),
                    str(row.get('Фото', '')).strip(),
                    provider_map.get(str(row.get('Поставщик', '')).strip()),
                    manufacturer_map.get(str(row.get('Производитель', '')).strip()),
                    category_map.get(str(row.get('Категория товара', '')).strip())
                ))
            except Exception as inner_e:
                 # print(f"Ошибка при обработке товара {article}: {inner_e}")
                 pass 
        conn.commit()
        print(f"Импорт товаров из {FILE_TOVAR} успешен.")
    else:
        print(f"Пропуск импорта товаров: {FILE_TOVAR} пуст или нечитаем.")

except Exception as e:
    print(f"Критическая ошибка при импорте товаров из {FILE_TOVAR}: {e}")

# 4.4. Orders and OrderProducts
point_map = get_map('PickupPoint', 'PointID', 'Address', cursor)
status_map = get_map('OrderStatus', 'StatusID', 'StatusName', cursor)

try:
    df_orders = read_csv_robust(FILE_ORDERS, sep=',', quoting=csv.QUOTE_MINIMAL)

    if not df_orders.empty:
        for index, row in df_orders.iterrows():
            try:
                # Order details
                point_address_str = str(row.get('Адрес пункта выдачи', '')).strip()
                # Файл заказов содержит ID пункта выдачи
                point_id = int(point_address_str) if point_address_str.isdigit() else None
                
                status_id = status_map.get(str(row.get('Статус заказа', '')).strip())
                code = int(row.get('Код для получения', 0)) if str(row.get('Код для получения', 0)).strip().isdigit() else 0
                
                if not point_id or not status_id or not code: continue 

                cursor.execute("""
                    INSERT INTO "Order" (OrderDate, DeliveryDate, PointID, ClientFIO, Code, StatusID)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    str(row.get('Дата заказа', '')).strip(), str(row.get('Дата доставки', '')).strip(), point_id,
                    str(row.get('ФИО авторизированного клиента', '')).strip(), code, 
                    status_id
                ))
                order_id = cursor.lastrowid

                # OrderProduct details (Парсинг строки "Артикул, Количество, Артикул, Количество")
                article_string = str(row.get('Артикул заказа', '')).strip().strip('"')
                parts = [p.strip() for p in article_string.split(',') if p.strip()]
                
                for i in range(0, len(parts), 2):
                    article = parts[i]
                    quantity_str = parts[i+1]
                    quantity = int(re.sub(r'[^0-9]', '', quantity_str)) 
                        
                    cursor.execute("""
                        INSERT INTO OrderProduct (OrderID, ProductArticle, Quantity)
                        VALUES (?, ?, ?)
                    """, (order_id, article, quantity))

            except Exception as inner_e:
                # print(f"Ошибка при обработке заказа: {inner_e}")
                pass 
        conn.commit()
        print(f"Импорт заказов из {FILE_ORDERS} успешен.")
    else:
        print(f"Пропуск импорта заказов: {FILE_ORDERS} пуст или нечитаем.")

except Exception as e:
    print(f"Критическая ошибка при импорте заказов из {FILE_ORDERS}: {e}")

conn.close()
print(f"\nБаза данных {DB_NAME} успешно создана и заполнена.")