import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, g, flash

# --- 1. НАСТРОЙКА ПРИЛОЖЕНИЯ ---
app = Flask(__name__)
# Установите безопасный секретный ключ для работы сессий
app.secret_key = 'your_super_secret_key_12345' 
DATABASE = 'demodb.db'

# --- 2. УТИЛИТЫ ДЛЯ БАЗЫ ДАННЫХ ---
def get_db():
    """Открывает новое соединение с базой данных и регистрирует TRIM."""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ #1: Регистрируем функцию TRIM() для SQL
        # Это помогает игнорировать невидимые пробелы в полях,
        # возникшие при импорте cp1251.
        db.create_function("TRIM", 1, lambda s: s.strip() if isinstance(s, str) else s)
        db.row_factory = sqlite3.Row  
    return db

@app.teardown_appcontext
def close_connection(exception):
    """Закрывает соединение с базой данных в конце запроса."""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# --- 3. КОНТЕКСТНЫЙ ПРОЦЕССОР ---
@app.context_processor
def inject_global_vars():
    """Передает роль пользователя во все шаблоны."""
    return dict(role=session.get('role', 'Гость'))

# --- 4. РОУТЫ ПРИЛОЖЕНИЯ ---

@app.route('/', methods=['GET', 'POST'])
def index():
    """
    Обрабатывает страницу входа (auth.html).
    """
    # Сбрасываем сессию при входе на страницу аутентификации
    session.clear() 
    db = get_db()
    cursor = db.cursor()
    error = None

    if request.method == 'POST':
        
        # Вход как гость (работает после удаления 'required' в auth.html)
        if 'guest_login' in request.form:
            session['role'] = 'Гость'
            session['login'] = 'Гость'
            return redirect(url_for('catalog'))

        # Стандартная попытка логина
        login = request.form.get('login', '').strip()
        password = request.form.get('password', '').strip()

        # Используем TRIM() в SQL для игнорирования пробелов в БД
        cursor.execute("""
            SELECT T1.UserID, T1.Login, T2.RoleName 
            FROM User AS T1
            JOIN Role AS T2 ON T1.RoleID = T2.RoleID 
            WHERE TRIM(T1.Login) = ? AND TRIM(T1.Password) = ?
        """, (login, password))
        
        user = cursor.fetchone()

        if user:
            session['user_id'] = user['UserID']
            session['login'] = user['Login']
            session['role'] = user['RoleName']
            return redirect(url_for('catalog'))
        else:
            error = "Неверный логин или пароль."
            
    return render_template('auth.html', error=error)


@app.route('/logout')
def logout():
    """Выход из системы."""
    session.clear()
    return redirect(url_for('index'))


@app.route('/catalog')
def catalog():
    """
    Обрабатывает страницу каталога товаров с фильтрацией и сортировкой.
    """
    if 'role' not in session:
        return redirect(url_for('index'))

    db = get_db()
    cursor = db.cursor()
    role = session['role']

    # Получение параметров фильтрации и сортировки из URL
    search_text = request.args.get('search', '').strip()
    filter_category = request.args.get('category', 'all').strip()
    filter_discount = request.args.get('discount', 'all').strip()
    sort_by = request.args.get('sort', 'Name').strip()
    
    # 1. Базовый запрос
    query = """
        SELECT 
            P.ProductArticle, P.Name, P.Unit, P.Price, P.Discount, P.Quantity, 
            P.Description, P.Photo,
            TRIM(C.CategoryName) AS CategoryName  -- КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ #2: TRIM для чистоты категории
        FROM Product P
        LEFT JOIN Category C ON P.CategoryID = C.CategoryID
    """
    
    # 2. Формирование WHERE-условия (Фильтры)
    where_clauses = []
    query_params = []
    
    # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ #3: Фильтр по остатку для Гостя и Клиента
    if role in ('Гость', 'Авторизированный клиент'):
        where_clauses.append("P.Quantity > 0")

    # Фильтр по поисковому запросу (по Названию или Описанию)
    if search_text:
        where_clauses.append("(P.Name LIKE ? OR P.Description LIKE ?)")
        query_params.extend([f'%{search_text}%', f'%{search_text}%'])

    # Фильтр по Категории
    if filter_category and filter_category != 'all':
        # Используем TRIM() для сравнения, если в базе есть пробелы
        where_clauses.append("TRIM(C.CategoryName) = ?") 
        query_params.append(filter_category)

    # Фильтр по Скидке
    if filter_discount == 'high':
        where_clauses.append("P.Discount > 15")
    elif filter_discount == 'present':
        where_clauses.append("P.Discount > 0")

    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)
        
    # 3. Формирование ORDER BY-условия (Сортировка)
    sort_map = {
        'Name': 'P.Name COLLATE NOCASE ASC',
        'Price_asc': 'P.Price ASC',
        'Price_desc': 'P.Price DESC',
        'Discount': 'P.Discount DESC'
    }
    order_by = sort_map.get(sort_by, 'P.Name COLLATE NOCASE ASC')
    query += f" ORDER BY {order_by}"

    # 4. Выполнение запроса
    products = cursor.execute(query, query_params).fetchall()
    
    # 5. Получение всех категорий для выпадающего списка
    # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ #4: TRIM для категорий из БД
    categories_db = cursor.execute("SELECT DISTINCT TRIM(CategoryName) AS CategoryName FROM Category ORDER BY CategoryName").fetchall()
    category_list = [c['CategoryName'] for c in categories_db]

    return render_template(
        'catalog.html',
        products=products,
        current_search=search_text,
        current_category=filter_category,
        current_discount=filter_discount,
        current_sort=sort_by,
        categories=["all"] + category_list # Добавляем 'all' для опции "Все категории"
    )

# --- 5. ЗАПУСК ПРИЛОЖЕНИЯ ---
if __name__ == '__main__':
    # Проверка базы данных
    try:
        with app.app_context():
            db = get_db()
            db.execute("SELECT 1 FROM Product LIMIT 1")
    except sqlite3.OperationalError:
        print("\n!!! КРИТИЧЕСКАЯ ОШИБКА: База данных 'demodb.db' не содержит таблицу Product. "
              "Убедитесь, что 'data_import.py' был запущен успешно.")
        exit()
        
    app.run(debug=True)