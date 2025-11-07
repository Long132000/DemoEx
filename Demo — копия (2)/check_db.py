import sqlite3
DATABASE = 'demodb.db'

conn = sqlite3.connect(DATABASE)
cursor = conn.cursor()

print("=== ПРОВЕРКА БАЗЫ ДАННЫХ ===")

# Проверяем таблицы
tables = ['User', 'Role', 'Product', 'Category', 'Supplier', 'Manufacturer', 'PickupPoint', 'Order', 'OrderStatus', 'OrderProduct']
for table in tables:
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"{table}: {count} записей")
    except Exception as e:
        print(f"{table}: ошибка - {e}")

print("\n=== ПРОВЕРКА ТОВАРОВ ===")
cursor.execute("SELECT COUNT(*) FROM Product WHERE Quantity > 0")
available_count = cursor.fetchone()[0]
print(f"Товаров в наличии (Quantity > 0): {available_count}")

print("\n=== ПРОВЕРКА ПОЛЬЗОВАТЕЛЕЙ И РОЛЕЙ ===")
cursor.execute("SELECT RoleName, COUNT(*) FROM User JOIN Role ON User.RoleID = Role.RoleID GROUP BY RoleName")
for role, count in cursor.fetchall():
    print(f"Роль '{role}': {count} пользователей")

print("\n=== ПРОВЕРКА ЗАКАЗОВ ===")
cursor.execute("SELECT StatusName, COUNT(*) FROM \"Order\" JOIN OrderStatus ON \"Order\".StatusID = OrderStatus.StatusID GROUP BY StatusName")
for status, count in cursor.fetchall():
    print(f"Статус '{status}': {count} заказов")

conn.close()