-- Модуль 1: Создание базы данных (demodb.db)

-- Таблица 1: Справочник ролей
CREATE TABLE Role (
    RoleID INTEGER PRIMARY KEY,
    RoleName TEXT NOT NULL UNIQUE
);

-- Таблица 2: Пользователи
CREATE TABLE User (
    UserID INTEGER PRIMARY KEY,
    FIO TEXT,
    Login TEXT NOT NULL UNIQUE,
    Password TEXT NOT NULL,
    RoleID INTEGER NOT NULL,
    FOREIGN KEY (RoleID) REFERENCES Role(RoleID)
);

-- Таблица 3: Пункты выдачи
CREATE TABLE PickupPoint (
    PointID INTEGER PRIMARY KEY,
    Address TEXT NOT NULL UNIQUE
);

-- Таблица 4-6: Справочники товаров
CREATE TABLE Category (CategoryID INTEGER PRIMARY KEY, CategoryName TEXT NOT NULL UNIQUE);
CREATE TABLE Provider (ProviderID INTEGER PRIMARY KEY, ProviderName TEXT NOT NULL UNIQUE);
CREATE TABLE Manufacturer (ManufacturerID INTEGER PRIMARY KEY, ManufacturerName TEXT NOT NULL UNIQUE);

-- Таблица 7: Товары
CREATE TABLE Product (
    ProductArticle TEXT PRIMARY KEY,
    Name TEXT,
    Unit TEXT,
    Price REAL,
    Discount INTEGER,
    Quantity INTEGER,
    Description TEXT,
    Photo TEXT,
    ProviderID INTEGER,
    ManufacturerID INTEGER,
    CategoryID INTEGER,
    FOREIGN KEY (ProviderID) REFERENCES Provider(ProviderID),
    FOREIGN KEY (ManufacturerID) REFERENCES Manufacturer(ManufacturerID),
    FOREIGN KEY (CategoryID) REFERENCES Category(CategoryID)
);

-- Таблица 8: Справочник статусов заказа
CREATE TABLE OrderStatus (
    StatusID INTEGER PRIMARY KEY,
    StatusName TEXT NOT NULL UNIQUE
);

-- Таблица 9: Основные данные заказа
CREATE TABLE "Order" (
    OrderID INTEGER PRIMARY KEY,
    OrderDate DATE,
    DeliveryDate DATE,
    PointID INTEGER,
    ClientFIO TEXT,
    Code INTEGER,
    StatusID INTEGER,
    FOREIGN KEY (PointID) REFERENCES PickupPoint(PointID),
    FOREIGN KEY (StatusID) REFERENCES OrderStatus(StatusID)
);

-- Таблица 10: Состав заказа (Многим-ко-многим)
CREATE TABLE OrderProduct (
    OrderID INTEGER NOT NULL,
    ProductArticle TEXT NOT NULL,
    Quantity INTEGER NOT NULL,
    PRIMARY KEY (OrderID, ProductArticle),
    FOREIGN KEY (OrderID) REFERENCES "Order"(OrderID) ON DELETE CASCADE,
    FOREIGN KEY (ProductArticle) REFERENCES Product(ProductArticle)
);

-- Инициализация базовых данных
INSERT OR IGNORE INTO Role (RoleID, RoleName) VALUES 
(1, 'Администратор'), 
(2, 'Менеджер'), 
(3, 'Авторизированный клиент');

INSERT OR IGNORE INTO OrderStatus (StatusID, StatusName) VALUES 
(1, 'Новый'), 
(2, 'В пути'), 
(3, 'Завершен'), 
(4, 'Отменен');