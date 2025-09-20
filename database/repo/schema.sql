-- Thông tin khách hàng
CREATE TABLE IF NOT EXISTS customers (
    CustomerId INTEGER PRIMARY KEY AUTOINCREMENT,
    Name TEXT NOT NULL,
    Email TEXT UNIQUE NOT NULL,
    Phone TEXT,
    Address TEXT,
    CreatedAt TEXT DEFAULT (datetime('now')),
    UpdatedAt TEXT DEFAULT (datetime('now'))
);

-- Danh mục sản phẩm (để quản lý nhóm sp, dễ gợi ý / lọc)
CREATE TABLE IF NOT EXISTS categories (
    CategoryId INTEGER PRIMARY KEY AUTOINCREMENT,
    CategoryName TEXT NOT NULL UNIQUE,
    Description TEXT
);

-- Sản phẩm
CREATE TABLE IF NOT EXISTS products (
    ProductId INTEGER PRIMARY KEY AUTOINCREMENT,
    ProductName TEXT NOT NULL,
    CategoryId INTEGER NOT NULL,
    Description TEXT,
    Price REAL NOT NULL CHECK(Price > 0),
    Quantity INTEGER NOT NULL CHECK(Quantity >= 0),
    ImageUrl TEXT, -- link ảnh sản phẩm
    CreatedAt TEXT DEFAULT (datetime('now')),
    UpdatedAt TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (CategoryId) REFERENCES categories (CategoryId)
);

-- Đơn hàng
CREATE TABLE IF NOT EXISTS orders (
    OrderId INTEGER PRIMARY KEY AUTOINCREMENT,
    CustomerId INTEGER NOT NULL,
    OrderDate TEXT DEFAULT (datetime('now')),
    Status TEXT NOT NULL CHECK(Status IN ('Pending', 'Processing', 'Shipped', 'Cancelled', 'Completed')),
    TotalAmount REAL NOT NULL DEFAULT 0,
    FOREIGN KEY (CustomerId) REFERENCES customers (CustomerId)
);

-- Chi tiết đơn hàng
CREATE TABLE IF NOT EXISTS order_details (
    OrderDetailId INTEGER PRIMARY KEY AUTOINCREMENT,
    OrderId INTEGER NOT NULL,
    ProductId INTEGER NOT NULL,
    Quantity INTEGER NOT NULL CHECK(Quantity > 0),
    UnitPrice REAL NOT NULL CHECK(UnitPrice > 0),
    SubTotal REAL GENERATED ALWAYS AS (Quantity * UnitPrice) STORED,
    FOREIGN KEY (OrderId) REFERENCES orders (OrderId),
    FOREIGN KEY (ProductId) REFERENCES products (ProductId)
);

-- Khuyến mãi (để chatbot gợi ý upsell)
CREATE TABLE IF NOT EXISTS promotions (
    PromotionId INTEGER PRIMARY KEY AUTOINCREMENT,
    ProductId INTEGER NOT NULL,
    DiscountPercent REAL CHECK(DiscountPercent >= 0 AND DiscountPercent <= 100),
    StartDate TEXT NOT NULL,
    EndDate TEXT NOT NULL,
    FOREIGN KEY (ProductId) REFERENCES products (ProductId)
);

-- Hỗ trợ khách hàng (chatbot có thể tra cứu lịch sử hỗ trợ)
CREATE TABLE IF NOT EXISTS support_tickets (
    TicketId INTEGER PRIMARY KEY AUTOINCREMENT,
    CustomerId INTEGER NOT NULL,
    Subject TEXT NOT NULL,
    Message TEXT NOT NULL,
    Status TEXT NOT NULL CHECK(Status IN ('Open', 'In Progress', 'Closed')) DEFAULT 'Open',
    CreatedAt TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (CustomerId) REFERENCES customers (CustomerId)
);
