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

-- =========================
-- INSERT SAMPLE DATA
-- =========================

-- Customers
INSERT INTO customers (Name, Email, Phone, Address) VALUES
('Nguyễn Văn A', 'vana@example.com', '0905123456', '123 Lê Lợi, Hà Nội'),
('Trần Thị B', 'thib@example.com', '0912345678', '456 Trần Hưng Đạo, TP.HCM'),
('Lê Hoàng C', 'hoangc@example.com', '0987654321', '789 Nguyễn Huệ, Đà Nẵng');

-- Categories
INSERT INTO categories (CategoryName, Description) VALUES
('Điện thoại', 'Các sản phẩm smartphone, điện thoại di động'),
('Laptop', 'Máy tính xách tay, laptop'),
('Phụ kiện', 'Phụ kiện điện thoại, laptop');

-- Products
INSERT INTO products (ProductName, CategoryId, Description, Price, Quantity, ImageUrl) VALUES
('iPhone 15 Pro Max', 1, 'Điện thoại Apple mới nhất', 32990000, 10, 'https://example.com/iphone15.jpg'),
('Samsung Galaxy S23 Ultra', 1, 'Flagship Samsung', 28990000, 8, 'https://example.com/s23ultra.jpg'),
('MacBook Air M2', 2, 'Laptop Apple chip M2', 28990000, 5, 'https://example.com/macbookairm2.jpg'),
('Dell XPS 13', 2, 'Laptop cao cấp của Dell', 25990000, 7, 'https://example.com/dellxps13.jpg'),
('Tai nghe AirPods Pro 2', 3, 'Tai nghe không dây chống ồn', 5490000, 20, 'https://example.com/airpodspro2.jpg');

-- Orders
INSERT INTO orders (CustomerId, Status, TotalAmount) VALUES
(1, 'Pending', 32990000),
(2, 'Processing', 34480000),
(3, 'Completed', 5490000);

-- Order details
INSERT INTO order_details (OrderId, ProductId, Quantity, UnitPrice) VALUES
(1, 1, 1, 32990000),
(2, 2, 1, 28990000),
(2, 5, 1, 5490000),
(3, 5, 1, 5490000);

-- Promotions
INSERT INTO promotions (ProductId, DiscountPercent, StartDate, EndDate) VALUES
(1, 10, '2025-09-01', '2025-09-30'),
(3, 15, '2025-09-15', '2025-10-15'),
(5, 20, '2025-09-10', '2025-09-25');

-- Support tickets
INSERT INTO support_tickets (CustomerId, Subject, Message, Status) VALUES
(1, 'Lỗi khi đặt hàng', 'Tôi không thanh toán được bằng thẻ VISA.', 'Open'),
(2, 'Hỏi về bảo hành', 'Laptop Dell XPS 13 bảo hành mấy năm?', 'In Progress'),
(3, 'Giao hàng chậm', 'AirPods Pro 2 tôi đặt chưa thấy giao.', 'Closed');
