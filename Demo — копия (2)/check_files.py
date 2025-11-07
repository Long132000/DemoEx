import os
import pandas as pd

def check_files():
    """Проверяет файлы в текущей директории"""
    print("=== ПРОВЕРКА ФАЙЛОВ ===")
    
    files = os.listdir('.')
    print("Все файлы в папке:")
    for file in files:
        print(f"  - {file}")
    
    # Проверяем конкретные файлы
    target_files = [
        'user_import.xlsx - Лист1.csv',
        'Tovar.xlsx - Лист1.csv', 
        'Пункты выдачи_import.xlsx - Лист1.csv',
        'Заказ_import.xlsx - Лист1.csv'
    ]
    
    print("\n=== ПРОВЕРКА ЦЕЛЕВЫХ ФАЙЛОВ ===")
    for file in target_files:
        exists = os.path.exists(file)
        print(f"{file}: {'НАЙДЕН' if exists else 'НЕ НАЙДЕН'}")
        
        if exists:
            try:
                # Пробуем прочитать как Excel
                df = pd.read_excel(file, nrows=3, engine='openpyxl')
                print(f"  Формат: Excel, колонки: {list(df.columns)}")
            except:
                try:
                    # Пробуем прочитать как CSV
                    df = pd.read_csv(file, nrows=3, encoding='utf-8-sig')
                    print(f"  Формат: CSV (utf-8-sig), колонки: {list(df.columns)}")
                except:
                    try:
                        df = pd.read_csv(file, nrows=3, encoding='cp1251')
                        print(f"  Формат: CSV (cp1251), колонки: {list(df.columns)}")
                    except Exception as e:
                        print(f"  Не удалось прочитать: {e}")

if __name__ == '__main__':
    check_files()