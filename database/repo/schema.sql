-- Xóa bảng cũ nếu tồn tại (để tránh lỗi khi chạy lại)
DROP TABLE IF EXISTS order_details;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS support_tickets;
DROP TABLE IF EXISTS promotions;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS categories;
DROP TABLE IF EXISTS customers;

-- Thông tin khách hàng
CREATE TABLE customers (
    CustomerId INTEGER PRIMARY KEY AUTOINCREMENT,
    Name TEXT NOT NULL,
    Email TEXT UNIQUE NOT NULL,
    Phone TEXT,
    Address TEXT,
    CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    UpdatedAt DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Danh mục sản phẩm
CREATE TABLE categories (
    CategoryId INTEGER PRIMARY KEY AUTOINCREMENT,
    CategoryName TEXT NOT NULL UNIQUE,
    Description TEXT,
    CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Sản phẩm
CREATE TABLE products (
    ProductId INTEGER PRIMARY KEY AUTOINCREMENT,
    ProductName TEXT NOT NULL,
    CategoryId INTEGER NOT NULL,
    Description TEXT,
    Price DECIMAL(15,2) NOT NULL CHECK(Price > 0),
    Quantity INTEGER NOT NULL CHECK(Quantity >= 0) DEFAULT 0,
    ImageUrl TEXT,
    IsActive BOOLEAN DEFAULT TRUE,
    CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    UpdatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (CategoryId) REFERENCES categories(CategoryId) ON DELETE RESTRICT
);

-- Đơn hàng
CREATE TABLE orders (
    OrderId INTEGER PRIMARY KEY AUTOINCREMENT,
    CustomerId INTEGER NOT NULL,
    OrderDate DATETIME DEFAULT CURRENT_TIMESTAMP,
    Status TEXT NOT NULL CHECK(Status IN ('Pending', 'Processing', 'Shipped', 'Delivered', 'Cancelled', 'Completed')) DEFAULT 'Pending',
    TotalAmount DECIMAL(15,2) NOT NULL DEFAULT 0 CHECK(TotalAmount >= 0),
    ShippingAddress TEXT,
    PaymentMethod TEXT CHECK(PaymentMethod IN ('Cash', 'Credit Card', 'Debit Card', 'Bank Transfer', 'E-Wallet')),
    Notes TEXT,
    FOREIGN KEY (CustomerId) REFERENCES customers(CustomerId) ON DELETE RESTRICT
);

-- Chi tiết đơn hàng
CREATE TABLE order_details (
    OrderDetailId INTEGER PRIMARY KEY AUTOINCREMENT,
    OrderId INTEGER NOT NULL,
    ProductId INTEGER NOT NULL,
    Quantity INTEGER NOT NULL CHECK(Quantity > 0),
    UnitPrice DECIMAL(15,2) NOT NULL CHECK(UnitPrice > 0),
    DiscountAmount DECIMAL(15,2) DEFAULT 0 CHECK(DiscountAmount >= 0),
    SubTotal DECIMAL(15,2) GENERATED ALWAYS AS ((Quantity * UnitPrice) - DiscountAmount) STORED,
    FOREIGN KEY (OrderId) REFERENCES orders(OrderId) ON DELETE CASCADE,
    FOREIGN KEY (ProductId) REFERENCES products(ProductId) ON DELETE RESTRICT,
    UNIQUE(OrderId, ProductId)
);

-- Khuyến mãi
CREATE TABLE promotions (
    PromotionId INTEGER PRIMARY KEY AUTOINCREMENT,
    PromotionName TEXT NOT NULL,
    ProductId INTEGER,
    CategoryId INTEGER,
    DiscountPercent DECIMAL(5,2) CHECK(DiscountPercent >= 0 AND DiscountPercent <= 100),
    DiscountAmount DECIMAL(15,2) CHECK(DiscountAmount >= 0),
    StartDate DATETIME NOT NULL,
    EndDate DATETIME NOT NULL,
    IsActive BOOLEAN DEFAULT TRUE,
    MinOrderAmount DECIMAL(15,2) DEFAULT 0,
    MaxDiscountAmount DECIMAL(15,2),
    CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ProductId) REFERENCES products(ProductId) ON DELETE CASCADE,
    FOREIGN KEY (CategoryId) REFERENCES categories(CategoryId) ON DELETE CASCADE,
    CHECK (StartDate < EndDate),
    CHECK ((ProductId IS NOT NULL AND CategoryId IS NULL) OR (ProductId IS NULL AND CategoryId IS NOT NULL) OR (ProductId IS NULL AND CategoryId IS NULL)),
    CHECK ((DiscountPercent IS NOT NULL AND DiscountAmount IS NULL) OR (DiscountPercent IS NULL AND DiscountAmount IS NOT NULL))
);

-- Hỗ trợ khách hàng
CREATE TABLE support_tickets (
    TicketId INTEGER PRIMARY KEY AUTOINCREMENT,
    CustomerId INTEGER NOT NULL,
    Subject TEXT NOT NULL,
    Message TEXT NOT NULL,
    Status TEXT NOT NULL CHECK(Status IN ('Open', 'In Progress', 'Waiting Customer', 'Resolved', 'Closed')) DEFAULT 'Open',
    Priority TEXT CHECK(Priority IN ('Low', 'Medium', 'High', 'Urgent')) DEFAULT 'Medium',
    AssignedTo TEXT,
    Resolution TEXT,
    CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    UpdatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    ResolvedAt DATETIME,
    FOREIGN KEY (CustomerId) REFERENCES customers(CustomerId) ON DELETE RESTRICT
);

-- Trigger để cập nhật UpdatedAt tự động
CREATE TRIGGER update_customers_timestamp 
    AFTER UPDATE ON customers
    FOR EACH ROW
BEGIN
    UPDATE customers SET UpdatedAt = CURRENT_TIMESTAMP WHERE CustomerId = NEW.CustomerId;
END;

CREATE TRIGGER update_products_timestamp 
    AFTER UPDATE ON products
    FOR EACH ROW
BEGIN
    UPDATE products SET UpdatedAt = CURRENT_TIMESTAMP WHERE ProductId = NEW.ProductId;
END;

CREATE TRIGGER update_support_tickets_timestamp 
    AFTER UPDATE ON support_tickets
    FOR EACH ROW
BEGIN
    UPDATE support_tickets SET UpdatedAt = CURRENT_TIMESTAMP WHERE TicketId = NEW.TicketId;
END;

-- Trigger để cập nhật tổng tiền đơn hàng
CREATE TRIGGER update_order_total_after_insert
    AFTER INSERT ON order_details
    FOR EACH ROW
BEGIN
    UPDATE orders 
    SET TotalAmount = (
        SELECT COALESCE(SUM(SubTotal), 0) 
        FROM order_details 
        WHERE OrderId = NEW.OrderId
    )
    WHERE OrderId = NEW.OrderId;
END;

CREATE TRIGGER update_order_total_after_update
    AFTER UPDATE ON order_details
    FOR EACH ROW
BEGIN
    UPDATE orders 
    SET TotalAmount = (
        SELECT COALESCE(SUM(SubTotal), 0) 
        FROM order_details 
        WHERE OrderId = NEW.OrderId
    )
    WHERE OrderId = NEW.OrderId;
END;

CREATE TRIGGER update_order_total_after_delete
    AFTER DELETE ON order_details
    FOR EACH ROW
BEGIN
    UPDATE orders 
    SET TotalAmount = (
        SELECT COALESCE(SUM(SubTotal), 0) 
        FROM order_details 
        WHERE OrderId = OLD.OrderId
    )
    WHERE OrderId = OLD.OrderId;
END;

-- ===== BỔ SUNG QUẢN LÝ LỊCH SỬ TRÒ CHUYỆN VÀ SESSION =====
-- Thêm vào database hiện tại mà không thay đổi cấu trúc cũ

-- Bảng quản lý session trò chuyện
CREATE TABLE chat_sessions (
    SessionId INTEGER PRIMARY KEY AUTOINCREMENT,
    CustomerId INTEGER NOT NULL,
    SessionName TEXT DEFAULT 'New Chat',
    IsActive BOOLEAN DEFAULT TRUE,
    CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    UpdatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    LastMessageAt DATETIME,
    MessageCount INTEGER DEFAULT 0,
    FOREIGN KEY (CustomerId) REFERENCES customers(CustomerId) ON DELETE CASCADE
);

-- Bảng lưu trữ tin nhắn với vector embeddings
CREATE TABLE chat_messages (
    MessageId INTEGER PRIMARY KEY AUTOINCREMENT,
    SessionId INTEGER NOT NULL,
    MessageType TEXT NOT NULL CHECK(MessageType IN ('human', 'ai', 'system', 'tool', 'summary')),
    Content TEXT NOT NULL,
    ContentEmbedding BLOB, -- Vector embedding của nội dung tin nhắn
    EmbeddingModel TEXT, -- Model embedding được sử dụng
    ToolCalls TEXT, -- JSON string để lưu thông tin tool calls
    ToolCallId TEXT,
    IsVisible BOOLEAN DEFAULT TRUE, -- Có hiển thị trong lịch sử không
    IsSummarized BOOLEAN DEFAULT FALSE, -- Đã được tóm tắt chưa
    CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (SessionId) REFERENCES chat_sessions(SessionId) ON DELETE CASCADE
);

-- Bảng tóm tắt conversation với vector embeddings
CREATE TABLE conversation_summaries (
    SummaryId INTEGER PRIMARY KEY AUTOINCREMENT,
    SessionId INTEGER NOT NULL,
    SummaryContent TEXT NOT NULL,
    SummaryEmbedding BLOB, -- Vector embedding của summary (binary format)
    EmbeddingModel TEXT DEFAULT 'text-embedding-ada-002', -- Model được sử dụng
    EmbeddingDimension INTEGER DEFAULT 1536, -- Số chiều của vector
    MessageRangeStart INTEGER NOT NULL, -- MessageId đầu tiên được tóm tắt
    MessageRangeEnd INTEGER NOT NULL,   -- MessageId cuối cùng được tóm tắt
    MessageCount INTEGER NOT NULL DEFAULT 0, -- Số lượng messages được tóm tắt
    KeyTopics TEXT, -- JSON array các chủ đề chính
    SentimentScore REAL, -- Điểm cảm xúc của cuộc hội thoại (-1 to 1)
    CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (SessionId) REFERENCES chat_sessions(SessionId) ON DELETE CASCADE,
    FOREIGN KEY (MessageRangeStart) REFERENCES chat_messages(MessageId),
    FOREIGN KEY (MessageRangeEnd) REFERENCES chat_messages(MessageId)
);

-- Bảng cấu hình session (tùy chọn nâng cao)
CREATE TABLE session_configs (
    ConfigId INTEGER PRIMARY KEY AUTOINCREMENT,
    SessionId INTEGER NOT NULL,
    SystemPrompt TEXT,
    MaxMemoryLength INTEGER DEFAULT 20,
    AutoSummarize BOOLEAN DEFAULT TRUE,
    Language TEXT DEFAULT 'vi',
    CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    UpdatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (SessionId) REFERENCES chat_sessions(SessionId) ON DELETE CASCADE
);

-- ===== BẢNG HỖ TRỢ VECTOR EMBEDDINGS =====

-- Bảng lưu trữ semantic clusters của conversations
CREATE TABLE conversation_clusters (
    ClusterId INTEGER PRIMARY KEY AUTOINCREMENT,
    ClusterName TEXT NOT NULL,
    ClusterEmbedding BLOB NOT NULL, -- Vector trung tâm của cluster
    EmbeddingModel TEXT NOT NULL,
    Description TEXT,
    SessionCount INTEGER DEFAULT 0,
    CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    UpdatedAt DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Bảng mapping sessions vào clusters
CREATE TABLE session_clusters (
    SessionId INTEGER NOT NULL,
    ClusterId INTEGER NOT NULL,
    SimilarityScore REAL NOT NULL, -- Độ tương tự (0-1)
    AssignedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (SessionId, ClusterId),
    FOREIGN KEY (SessionId) REFERENCES chat_sessions(SessionId) ON DELETE CASCADE,
    FOREIGN KEY (ClusterId) REFERENCES conversation_clusters(ClusterId) ON DELETE CASCADE
);

-- Bảng lưu trữ knowledge base từ conversations
CREATE TABLE knowledge_base (
    KnowledgeId INTEGER PRIMARY KEY AUTOINCREMENT,
    Title TEXT NOT NULL,
    Content TEXT NOT NULL,
    ContentEmbedding BLOB NOT NULL,
    EmbeddingModel TEXT NOT NULL,
    SourceType TEXT CHECK(SourceType IN ('conversation', 'manual', 'document')) DEFAULT 'conversation',
    SourceSessionId INTEGER, -- Nếu từ conversation
    Category TEXT,
    Tags TEXT, -- JSON array
    UseCount INTEGER DEFAULT 0, -- Số lần được sử dụng
    LastUsedAt DATETIME,
    IsActive BOOLEAN DEFAULT TRUE,
    CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    UpdatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (SourceSessionId) REFERENCES chat_sessions(SessionId) ON DELETE SET NULL
);

-- Bảng lưu semantic search cache
CREATE TABLE semantic_search_cache (
    CacheId INTEGER PRIMARY KEY AUTOINCREMENT,
    QueryText TEXT NOT NULL,
    QueryEmbedding BLOB NOT NULL,
    EmbeddingModel TEXT NOT NULL,
    SearchResults TEXT NOT NULL, -- JSON array kết quả
    HitCount INTEGER DEFAULT 1,
    CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    LastUsedAt DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ===== INDEX CHO VECTOR OPERATIONS =====
CREATE INDEX idx_conversation_summaries_embedding_model ON conversation_summaries(EmbeddingModel);
CREATE INDEX idx_chat_messages_embedding_model ON chat_messages(EmbeddingModel);
CREATE INDEX idx_chat_messages_summarized ON chat_messages(IsSummarized, SessionId);
CREATE INDEX idx_knowledge_base_category ON knowledge_base(Category, IsActive);
CREATE INDEX idx_knowledge_base_embedding_model ON knowledge_base(EmbeddingModel);
CREATE INDEX idx_semantic_search_cache_query ON semantic_search_cache(QueryText);
CREATE INDEX idx_session_clusters_similarity ON session_clusters(SimilarityScore DESC);

-- ===== TRIGGERS ĐỂ TỰ ĐỘNG CẬP NHẬT =====

-- Trigger cập nhật thông tin session khi có tin nhắn mới
CREATE TRIGGER update_session_on_new_message
    AFTER INSERT ON chat_messages
    FOR EACH ROW
    WHEN NEW.MessageType IN ('human', 'ai')  -- Chỉ đếm tin nhắn chính
BEGIN
    UPDATE chat_sessions 
    SET 
        LastMessageAt = NEW.CreatedAt,
        MessageCount = MessageCount + 1,
        UpdatedAt = CURRENT_TIMESTAMP
    WHERE SessionId = NEW.SessionId;
END;

-- Trigger cập nhật cluster count
CREATE TRIGGER update_cluster_session_count_insert
    AFTER INSERT ON session_clusters
    FOR EACH ROW
BEGIN
    UPDATE conversation_clusters 
    SET SessionCount = SessionCount + 1,
        UpdatedAt = CURRENT_TIMESTAMP
    WHERE ClusterId = NEW.ClusterId;
END;

CREATE TRIGGER update_cluster_session_count_delete
    AFTER DELETE ON session_clusters
    FOR EACH ROW
BEGIN
    UPDATE conversation_clusters 
    SET SessionCount = SessionCount - 1,
        UpdatedAt = CURRENT_TIMESTAMP
    WHERE ClusterId = OLD.ClusterId;
END;

-- Trigger cập nhật knowledge base usage
CREATE TRIGGER update_knowledge_usage
    AFTER UPDATE OF UseCount ON knowledge_base
    FOR EACH ROW
    WHEN NEW.UseCount > OLD.UseCount
BEGIN
    UPDATE knowledge_base 
    SET LastUsedAt = CURRENT_TIMESTAMP 
    WHERE KnowledgeId = NEW.KnowledgeId;
END;

-- Trigger cập nhật cache hit count
CREATE TRIGGER update_cache_hit_count
    AFTER UPDATE OF HitCount ON semantic_search_cache
    FOR EACH ROW
    WHEN NEW.HitCount > OLD.HitCount
BEGIN
    UPDATE semantic_search_cache 
    SET LastUsedAt = CURRENT_TIMESTAMP 
    WHERE CacheId = NEW.CacheId;
END;

-- Trigger cập nhật UpdatedAt cho session configs
CREATE TRIGGER update_session_configs_timestamp 
    AFTER UPDATE ON session_configs
    FOR EACH ROW
BEGIN
    UPDATE session_configs SET UpdatedAt = CURRENT_TIMESTAMP WHERE ConfigId = NEW.ConfigId;
END;

-- Trigger cập nhật UpdatedAt cho chat_sessions
CREATE TRIGGER update_chat_sessions_timestamp 
    AFTER UPDATE ON chat_sessions
    FOR EACH ROW
BEGIN
    UPDATE chat_sessions SET UpdatedAt = CURRENT_TIMESTAMP WHERE SessionId = NEW.SessionId;
END;

-- ===== VIEW ĐỂ TRUY VẤN DỄ DÀNG =====

-- View để xem session với thông tin khách hàng
CREATE VIEW session_overview AS
SELECT 
    cs.SessionId,
    cs.SessionName,
    cs.IsActive,
    cs.CreatedAt,
    cs.UpdatedAt,
    cs.LastMessageAt,
    cs.MessageCount,
    c.Name as CustomerName,
    c.Email as CustomerEmail
FROM chat_sessions cs
JOIN customers c ON cs.CustomerId = c.CustomerId;

-- View để xem tin nhắn với thông tin session
CREATE VIEW message_details AS
SELECT 
    cm.MessageId,
    cm.SessionId,
    cm.MessageType,
    cm.Content,
    cm.CreatedAt,
    cs.SessionName,
    c.Name as CustomerName
FROM chat_messages cm
JOIN chat_sessions cs ON cm.SessionId = cs.SessionId
JOIN customers c ON cs.CustomerId = c.CustomerId
WHERE cm.IsVisible = TRUE
ORDER BY cm.CreatedAt;

-- ===== STORED PROCEDURES (Sử dụng trong Python) =====

-- Function để tạo session mới (thực hiện trong Python)
-- def create_new_session(customer_id, session_name=None):
--     if not session_name:
--         session_name = f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}"
--     # INSERT INTO chat_sessions...

-- Function để lấy lịch sử chat (thực hiện trong Python)  
-- def get_chat_history(session_id, limit=50):
--     # SELECT từ chat_messages với limit

-- Function để tóm tắt và cleanup old messages (thực hiện trong Python)
-- def summarize_old_messages(session_id, keep_recent=10):
--     # Logic tóm tắt tin nhắn cũ

-- ===== DỮ LIỆU MẪU =====

-- Tạo một số session mẫu (giả sử đã có customers)
INSERT INTO chat_sessions (CustomerId, SessionName, IsActive, CreatedAt) VALUES 
(1, 'Hỏi về sản phẩm', TRUE, '2024-01-15 10:00:00'),
(1, 'Hỗ trợ đặt hàng', FALSE, '2024-01-16 14:30:00'),
(2, 'Khiếu nại sản phẩm', TRUE, '2024-01-17 09:15:00');

-- Tạo cấu hình session mặc định
INSERT INTO session_configs (SessionId, SystemPrompt, MaxMemoryLength, AutoSummarize) VALUES 
(1, 'Bạn là trợ lý AI hỗ trợ khách hàng về sản phẩm.', 20, TRUE),
(2, 'Bạn là trợ lý AI hỗ trợ đặt hàng.', 15, TRUE),
(3, 'Bạn là trợ lý AI xử lý khiếu nại.', 25, TRUE);

-- Tạo một số tin nhắn mẫu
INSERT INTO chat_messages (SessionId, MessageType, Content, CreatedAt) VALUES 
(1, 'human', 'Xin chào, tôi muốn hỏi về sản phẩm laptop', '2024-01-15 10:01:00'),
(1, 'ai', 'Xin chào! Tôi có thể giúp bạn tìm hiểu về các sản phẩm laptop. Bạn đang quan tâm đến loại laptop nào?', '2024-01-15 10:01:30'),
(1, 'human', 'Tôi cần laptop cho công việc văn phòng', '2024-01-15 10:02:00'),
(1, 'ai', 'Để laptop phù hợp cho công việc văn phòng, tôi khuyên bạn nên xem các dòng laptop có cấu hình ổn định...', '2024-01-15 10:02:30');

-- ===== QUERY MẪU ĐỂ SỬ DỤNG VỚI VECTOR EMBEDDINGS =====

-- Lấy tất cả session của một khách hàng
-- SELECT * FROM session_overview WHERE CustomerEmail = 'customer@email.com' ORDER BY UpdatedAt DESC;

-- Lấy lịch sử chat của một session với embeddings
-- SELECT MessageType, Content, 
--        CASE WHEN ContentEmbedding IS NOT NULL THEN 'Yes' ELSE 'No' END as HasEmbedding,
--        CreatedAt 
-- FROM chat_messages 
-- WHERE SessionId = 1 AND IsVisible = TRUE ORDER BY CreatedAt;

-- Lấy session đang hoạt động gần nhất của khách hàng  
-- SELECT * FROM chat_sessions WHERE CustomerId = 1 AND IsActive = TRUE ORDER BY UpdatedAt DESC LIMIT 1;

-- Tìm kiếm semantic trong knowledge base (cần implement trong Python)
-- SELECT KnowledgeId, Title, Content, UseCount
-- FROM knowledge_base 
-- WHERE IsActive = TRUE
-- ORDER BY [cosine_similarity với query vector] DESC LIMIT 5;

-- Lấy summaries có embedding của một session
-- SELECT SummaryId, SummaryContent, KeyTopics, SentimentScore,
--        CASE WHEN SummaryEmbedding IS NOT NULL THEN 'Yes' ELSE 'No' END as HasEmbedding
-- FROM conversation_summaries 
-- WHERE SessionId = 1 ORDER BY CreatedAt;

-- Lấy clusters tương tự cho một session
-- SELECT cc.ClusterName, cc.Description, sc.SimilarityScore
-- FROM session_clusters sc
-- JOIN conversation_clusters cc ON sc.ClusterId = cc.ClusterId
-- WHERE sc.SessionId = 1
-- ORDER BY sc.SimilarityScore DESC;

-- Thống kê embedding coverage
-- SELECT 
--     (SELECT COUNT(*) FROM chat_messages WHERE ContentEmbedding IS NOT NULL) as MessagesWithEmbedding,
--     (SELECT COUNT(*) FROM chat_messages) as TotalMessages,
--     (SELECT COUNT(*) FROM conversation_summaries WHERE SummaryEmbedding IS NOT NULL) as SummariesWithEmbedding,
--     (SELECT COUNT(*) FROM conversation_summaries) as TotalSummaries;

-- =========================
-- INSERT SAMPLE DATA
-- =========================

-- Customers (20 khách hàng)
INSERT INTO customers (Name, Email, Phone, Address) VALUES
('Nguyễn Văn An', 'vanan@gmail.com', '0905123456', '123 Lê Lợi, Quận 1, TP.HCM'),
('Trần Thị Bình', 'thibinhh@gmail.com', '0912345678', '456 Trần Hưng Đạo, Quận 5, TP.HCM'),
('Lê Hoàng Cường', 'hoangcuong@gmail.com', '0987654321', '789 Nguyễn Huệ, Hải Châu, Đà Nẵng'),
('Phạm Thị Dung', 'thidung@gmail.com', '0966123456', '321 Hoàng Diệu, Ba Đình, Hà Nội'),
('Võ Minh Đức', 'minhduc@gmail.com', '0977456789', '654 Lý Thường Kiệt, Quận 10, TP.HCM'),
('Đỗ Thị Hoa', 'thihoa@gmail.com', '0988789123', '987 Hai Bà Trưng, Đống Đa, Hà Nội'),
('Bùi Văn Khang', 'vankhang@gmail.com', '0911222333', '159 Pasteur, Quận 3, TP.HCM'),
('Lý Thị Mai', 'thimai@gmail.com', '0922333444', '753 Nguyễn Văn Cừ, Long Biên, Hà Nội'),
('Hoàng Văn Nam', 'vannam@gmail.com', '0933444555', '246 Lê Duẩn, Thanh Khê, Đà Nẵng'),
('Phan Thị Oanh', 'thioahn@gmail.com', '0944555666', '135 Điện Biên Phủ, Bình Thạnh, TP.HCM'),
('Ngô Văn Phúc', 'vanphuc@gmail.com', '0955666777', '468 Xô Viết Nghệ Tĩnh, Bình Thạnh, TP.HCM'),
('Vũ Thị Quỳnh', 'thiquynh@gmail.com', '0966777888', '579 Cách Mạng Tháng 8, Quận 3, TP.HCM'),
('Đặng Văn Sơn', 'vanson@gmail.com', '0977888999', '680 Nguyễn Thị Minh Khai, Quận 1, TP.HCM'),
('Lưu Thị Tâm', 'thitam@gmail.com', '0988999111', '791 Võ Văn Tần, Quận 3, TP.HCM'),
('Cao Văn Tùng', 'vantung@gmail.com', '0999111222', '802 Nam Kỳ Khởi Nghĩa, Quận 3, TP.HCM'),
('Bùi Thị Uyên', 'thiuyen@gmail.com', '0911333555', '913 Lê Văn Sỹ, Tân Bình, TP.HCM'),
('Trịnh Văn Vinh', 'vanvinh@gmail.com', '0922444666', '024 Nguyễn Đình Chiểu, Quận 1, TP.HCM'),
('Dương Thị Xuân', 'thixuan@gmail.com', '0933555777', '135 Hai Bà Trưng, Quận 1, TP.HCM'),
('Phùng Văn Yên', 'vanyen@gmail.com', '0944666888', '246 Lê Lợi, Quận 1, TP.HCM'),
('Lê Thị Zoan', 'thizoan@gmail.com', '0955777999', '357 Nguyễn Trãi, Quận 5, TP.HCM');

-- Categories (10 danh mục)
INSERT INTO categories (CategoryName, Description) VALUES
('Điện thoại', 'Smartphone và điện thoại di động các loại'),
('Laptop', 'Máy tính xách tay, laptop gaming, văn phòng'),
('Tablet', 'Máy tính bảng iPad, Android tablet'),
('Phụ kiện điện thoại', 'Ốp lưng, cường lực, sạc dự phòng'),
('Phụ kiện laptop', 'Túi laptop, chuột, bàn phím, webcam'),
('Tai nghe - Loa', 'Tai nghe, loa bluetooth, loa gaming'),
('Đồng hồ thông minh', 'Smartwatch, vòng đeo tay thông minh'),
('Camera - Máy ảnh', 'Máy ảnh DSLR, mirrorless, action cam'),
('Gaming', 'Thiết bị gaming, tay cầm, ghế gaming'),
('Smart Home', 'Thiết bị nhà thông minh, IoT');

-- Products (50 sản phẩm)
INSERT INTO products (ProductName, CategoryId, Description, Price, Quantity, ImageUrl) VALUES
-- Điện thoại (CategoryId = 1)
('iPhone 15 Pro Max 256GB', 1, 'iPhone mới nhất với chip A17 Pro, camera 48MP', 32990000, 15, 'https://example.com/iphone15promax.jpg'),
('Samsung Galaxy S24 Ultra', 1, 'Flagship Samsung với S Pen, camera 200MP', 31990000, 12, 'https://example.com/s24ultra.jpg'),
('iPhone 14 Pro 128GB', 1, 'iPhone 14 Pro với Dynamic Island', 26990000, 20, 'https://example.com/iphone14pro.jpg'),
('Xiaomi 14 Ultra', 1, 'Flagship Xiaomi camera Leica', 24990000, 8, 'https://example.com/xiaomi14ultra.jpg'),
('Samsung Galaxy S23 FE', 1, 'Samsung Galaxy S23 Fan Edition', 13990000, 25, 'https://example.com/s23fe.jpg'),
('iPhone 13 128GB', 1, 'iPhone 13 giá tốt nhất', 17990000, 30, 'https://example.com/iphone13.jpg'),
('OPPO Find X7 Ultra', 1, 'OPPO flagship với camera Hasselblad', 22990000, 10, 'https://example.com/findx7ultra.jpg'),
('Vivo X100 Pro', 1, 'Vivo flagship camera ZEISS', 19990000, 18, 'https://example.com/vivox100pro.jpg'),

-- Laptop (CategoryId = 2)
('MacBook Air M3 13 inch', 2, 'MacBook Air chip M3 mới nhất', 28990000, 8, 'https://example.com/macbookairm3.jpg'),
('MacBook Pro 14 inch M3', 2, 'MacBook Pro 14 inch chip M3 Pro', 52990000, 5, 'https://example.com/macbookpro14.jpg'),
('Dell XPS 13 Plus', 2, 'Laptop cao cấp Intel Core i7', 35990000, 12, 'https://example.com/dellxps13plus.jpg'),
('ASUS ROG Zephyrus G14', 2, 'Laptop gaming AMD Ryzen 9', 42990000, 7, 'https://example.com/rogg14.jpg'),
('HP Spectre x360', 2, 'Laptop 2-in-1 cao cấp', 38990000, 6, 'https://example.com/spectrex360.jpg'),
('Lenovo ThinkPad X1 Carbon', 2, 'Laptop doanh nhân cao cấp', 45990000, 9, 'https://example.com/thinkpadx1.jpg'),
('MSI Gaming Katana 15', 2, 'Laptop gaming giá rẻ RTX 4050', 22990000, 15, 'https://example.com/msikatana15.jpg'),

-- Tablet (CategoryId = 3)
('iPad Pro 12.9 inch M2', 3, 'iPad Pro mạnh nhất với chip M2', 29990000, 10, 'https://example.com/ipadprom2.jpg'),
('iPad Air 5th Gen', 3, 'iPad Air với chip M1', 16990000, 15, 'https://example.com/ipadair5.jpg'),
('Samsung Galaxy Tab S9 Ultra', 3, 'Tablet Android cao cấp nhất', 26990000, 8, 'https://example.com/tabs9ultra.jpg'),
('iPad 10th Gen', 3, 'iPad cơ bản giá tốt', 10990000, 20, 'https://example.com/ipad10th.jpg'),

-- Phụ kiện điện thoại (CategoryId = 4)
('Ốp lưng iPhone 15 Pro Silicone', 4, 'Ốp lưng chính hãng Apple', 1290000, 100, 'https://example.com/iplsilicone.jpg'),
('Cường lực iPhone 15 Pro', 4, 'Kính cường lực bảo vệ màn hình', 290000, 200, 'https://example.com/tempered15pro.jpg'),
('Sạc dự phòng Anker 20000mAh', 4, 'Pin sạc dự phòng sạc nhanh 67W', 1990000, 50, 'https://example.com/anker20k.jpg'),
('Cáp Lightning MFi', 4, 'Cáp sạc iPhone chính hãng MFi', 590000, 80, 'https://example.com/lightningmfi.jpg'),
('Đế sạc không dây MagSafe', 4, 'Đế sạc không dây iPhone MagSafe', 2490000, 30, 'https://example.com/magsafe.jpg'),

-- Tai nghe - Loa (CategoryId = 6)
('AirPods Pro 2nd Gen', 6, 'Tai nghe không dây chống ồn Apple', 5990000, 25, 'https://example.com/airpodspro2.jpg'),
('Sony WH-1000XM5', 6, 'Tai nghe chống ồn tốt nhất', 7990000, 15, 'https://example.com/sonywh1000xm5.jpg'),
('AirPods 3rd Gen', 6, 'AirPods thế hệ 3 spatial audio', 4290000, 30, 'https://example.com/airpods3.jpg'),
('JBL Charge 5', 6, 'Loa bluetooth chống nước IP67', 3590000, 20, 'https://example.com/jblcharge5.jpg'),
('Bose QuietComfort 45', 6, 'Tai nghe chống ồn Bose', 6990000, 12, 'https://example.com/boseqc45.jpg'),

-- Đồng hồ thông minh (CategoryId = 7)
('Apple Watch Series 9', 7, 'Apple Watch mới nhất', 9990000, 18, 'https://example.com/watchseries9.jpg'),
('Apple Watch SE 2nd Gen', 7, 'Apple Watch giá rẻ', 6990000, 25, 'https://example.com/watchse2.jpg'),
('Samsung Galaxy Watch 6', 7, 'Đồng hồ Samsung cao cấp', 7990000, 15, 'https://example.com/galaxywatch6.jpg'),
('Garmin Forerunner 965', 7, 'Đồng hồ chạy bộ chuyên nghiệp', 14990000, 8, 'https://example.com/forerunner965.jpg'),

-- Camera (CategoryId = 8)
('Canon EOS R6 Mark II', 8, 'Máy ảnh mirrorless chuyên nghiệp', 54990000, 5, 'https://example.com/canonr6mk2.jpg'),
('Sony Alpha A7 IV', 8, 'Máy ảnh full-frame Sony', 59990000, 4, 'https://example.com/sonya7iv.jpg'),
('GoPro Hero 12', 8, 'Action camera quay 5.3K', 9990000, 20, 'https://example.com/gopro12.jpg'),
('DJI Action 4', 8, 'Action camera DJI 4K/120fps', 8990000, 15, 'https://example.com/djiaction4.jpg'),

-- Gaming (CategoryId = 9)
('PlayStation 5', 9, 'Máy chơi game Sony PS5', 13990000, 8, 'https://example.com/ps5.jpg'),
('Xbox Series X', 9, 'Máy chơi game Microsoft', 12990000, 10, 'https://example.com/xboxseriesx.jpg'),
('Nintendo Switch OLED', 9, 'Máy chơi game cầm tay Nintendo', 8990000, 15, 'https://example.com/switcholed.jpg'),
('Razer DeathAdder V3 Pro', 9, 'Chuột gaming không dây Razer', 3990000, 25, 'https://example.com/deathadderv3.jpg'),
('SteelSeries Arctis 7P', 9, 'Tai nghe gaming không dây', 4990000, 18, 'https://example.com/arctis7p.jpg'),

-- Smart Home (CategoryId = 10)
('HomePod mini', 10, 'Loa thông minh Apple', 2490000, 20, 'https://example.com/homepodmini.jpg'),
('Amazon Echo Dot 5th Gen', 10, 'Loa thông minh Amazon Alexa', 1290000, 30, 'https://example.com/echodot5.jpg'),
('Philips Hue Starter Kit', 10, 'Bộ đèn thông minh Philips', 4990000, 12, 'https://example.com/philipshue.jpg'),
('Ring Video Doorbell 4', 10, 'Chuông cửa thông minh có camera', 4590000, 15, 'https://example.com/ringdoorbell4.jpg'),
('TP-Link Kasa Smart Plug', 10, 'Ổ cắm thông minh wifi', 390000, 50, 'https://example.com/kasaplug.jpg'),

-- Phụ kiện laptop (CategoryId = 5)
('Logitech MX Master 3S', 5, 'Chuột không dây cao cấp', 2290000, 25, 'https://example.com/mxmaster3s.jpg'),
('Apple Magic Keyboard', 5, 'Bàn phím không dây Apple', 2990000, 15, 'https://example.com/magickeyboard.jpg'),
('Dell UltraSharp U2723QE', 5, 'Màn hình 4K 27 inch cho laptop', 12990000, 8, 'https://example.com/dellu2723qe.jpg'),
('Anker USB-C Hub 7-in-1', 5, 'Hub mở rộng cổng USB-C', 1590000, 40, 'https://example.com/ankerhub7in1.jpg');

-- Orders (30 đơn hàng)
INSERT INTO orders (CustomerId, Status, ShippingAddress, PaymentMethod, Notes) VALUES
(1, 'Completed', '123 Lê Lợi, Quận 1, TP.HCM', 'Credit Card', 'Giao hàng nhanh'),
(2, 'Shipped', '456 Trần Hưng Đạo, Quận 5, TP.HCM', 'Bank Transfer', NULL),
(3, 'Processing', '789 Nguyễn Huệ, Hải Châu, Đà Nẵng', 'E-Wallet', 'Đóng gói cẩn thận'),
(4, 'Pending', '321 Hoàng Diệu, Ba Đình, Hà Nội', 'Cash', NULL),
(5, 'Delivered', '654 Lý Thường Kiệt, Quận 10, TP.HCM', 'Credit Card', NULL),
(6, 'Completed', '987 Hai Bà Trưng, Đống Đa, Hà Nội', 'Debit Card', NULL),
(7, 'Processing', '159 Pasteur, Quận 3, TP.HCM', 'E-Wallet', 'Giao giờ hành chính'),
(8, 'Shipped', '753 Nguyễn Văn Cừ, Long Biên, Hà Nội', 'Bank Transfer', NULL),
(9, 'Pending', '246 Lê Duẩn, Thanh Khê, Đà Nẵng', 'Cash', 'Gọi trước khi giao'),
(10, 'Completed', '135 Điện Biên Phủ, Bình Thạnh, TP.HCM', 'Credit Card', NULL),
(11, 'Cancelled', '468 Xô Viết Nghệ Tĩnh, Bình Thạnh, TP.HCM', 'E-Wallet', 'Khách hủy đơn'),
(12, 'Processing', '579 Cách Mạng Tháng 8, Quận 3, TP.HCM', 'Credit Card', NULL),
(13, 'Delivered', '680 Nguyễn Thị Minh Khai, Quận 1, TP.HCM', 'Bank Transfer', NULL),
(14, 'Completed', '791 Võ Văn Tần, Quận 3, TP.HCM', 'Cash', NULL),
(15, 'Shipped', '802 Nam Kỳ Khởi Nghĩa, Quận 3, TP.HCM', 'Credit Card', NULL),
(1, 'Pending', '123 Lê Lợi, Quận 1, TP.HCM', 'E-Wallet', 'Đơn hàng thứ 2'),
(2, 'Completed', '456 Trần Hưng Đạo, Quận 5, TP.HCM', 'Credit Card', NULL),
(3, 'Processing', '789 Nguyễn Huệ, Hải Châu, Đà Nẵng', 'Bank Transfer', NULL),
(16, 'Delivered', '913 Lê Văn Sỹ, Tân Bình, TP.HCM', 'Cash', NULL),
(17, 'Completed', '024 Nguyễn Đình Chiểu, Quận 1, TP.HCM', 'Credit Card', NULL),
(18, 'Shipped', '135 Hai Bà Trưng, Quận 1, TP.HCM', 'E-Wallet', NULL),
(19, 'Processing', '246 Lê Lợi, Quận 1, TP.HCM', 'Bank Transfer', NULL),
(20, 'Pending', '357 Nguyễn Trãi, Quận 5, TP.HCM', 'Cash', 'Kiểm tra hàng trước khi thanh toán'),
(4, 'Completed', '321 Hoàng Diệu, Ba Đình, Hà Nội', 'Credit Card', 'Đơn hàng thứ 2'),
(5, 'Cancelled', '654 Lý Thường Kiệt, Quận 10, TP.HCM', 'E-Wallet', 'Hết hàng'),
(6, 'Processing', '987 Hai Bà Trưng, Đống Đa, Hà Nội', 'Bank Transfer', NULL),
(7, 'Delivered', '159 Pasteur, Quận 3, TP.HCM', 'Cash', NULL),
(8, 'Completed', '753 Nguyễn Văn Cừ, Long Biên, Hà Nội', 'Credit Card', NULL),
(9, 'Shipped', '246 Lê Duẩn, Thanh Khê, Đà Nẵng', 'E-Wallet', NULL),
(10, 'Pending', '135 Điện Biên Phủ, Bình Thạnh, TP.HCM', 'Bank Transfer', 'Giao cuối tuần');

-- Order Details (nhiều chi tiết đơn hàng)
INSERT INTO order_details (OrderId, ProductId, Quantity, UnitPrice, DiscountAmount) VALUES
-- Đơn hàng 1: iPhone 15 Pro Max
(1, 1, 1, 32990000, 0),
-- Đơn hàng 2: Samsung Galaxy S24 Ultra + AirPods Pro 2
(2, 2, 1, 31990000, 0),
(2, 25, 1, 5990000, 0),
-- Đơn hàng 3: MacBook Air M3
(3, 9, 1, 28990000, 0),
-- Đơn hàng 4: iPad Pro + Apple Pencil
(4, 17, 1, 29990000, 0),
-- Đơn hàng 5: Gaming setup
(5, 35, 1, 13990000, 0),
(5, 37, 1, 8990000, 0),
(5, 38, 1, 3990000, 0),
-- Đơn hàng 6: iPhone 14 Pro + phụ kiện
(6, 3, 1, 26990000, 0),
(6, 21, 2, 1290000, 0),
(6, 22, 1, 290000, 0),
-- Đơn hàng 7: Laptop Dell + chuột
(7, 11, 1, 35990000, 0),
(7, 46, 1, 2290000, 0),
-- Đơn hàng 8: Camera setup
(8, 31, 1, 54990000, 0),
-- Đơn hàng 9: Smart Home kit
(9, 40, 1, 2490000, 0),
(9, 42, 1, 4990000, 0),
(9, 44, 2, 390000, 0),
-- Đơn hàng 10: Tablet + phụ kiện
(10, 18, 1, 16990000, 0),
-- Đơn hàng 11: Cancelled order
-- Đơn hàng 12: Xiaomi + tai nghe
(12, 4, 1, 24990000, 0),
(12, 26, 1, 7990000, 0),
-- Đơn hàng 13: iPhone 13
(13, 6, 1, 17990000, 0),
-- Đơn hàng 14: Apple Watch + AirPods
(14, 29, 1, 9990000, 0),
(14, 27, 1, 4290000, 0),
-- Đơn hàng 15: Gaming mouse + headset
(15, 38, 1, 3990000, 0),
(15, 39, 1, 4990000, 0),
-- Đơn hàng 16: Sạc dự phòng + cáp
(16, 23, 1, 1990000, 0),
(16, 24, 2, 590000, 0),
-- Đơn hàng 17: Loa JBL
(17, 28, 1, 3590000, 0),
-- Đơn hàng 18: MacBook Pro
(18, 10, 1, 52990000, 0),
-- Đơn hàng 19: Samsung Tab + keyboard
(19, 19, 1, 26990000, 0),
(19, 47, 1, 2990000, 0),
-- Đơn hàng 20: iPad basic + case
(20, 20, 1, 10990000, 0),
(20, 21, 1, 1290000, 0),
-- Đơn hàng 21-30: More orders
(21, 15, 1, 22990000, 0),
(22, 5, 1, 13990000, 0),
(23, 33, 1, 9990000, 0),
(24, 12, 1, 42990000, 0),
(25, 7, 1, 22990000, 0),
(26, 13, 1, 38990000, 0),
(27, 8, 1, 19990000, 0),
(28, 14, 1, 45990000, 0),
(29, 36, 1, 12990000, 0),
(30, 41, 1, 1290000, 0);

-- Promotions (20 khuyến mãi)
INSERT INTO promotions (PromotionName, ProductId, CategoryId, DiscountPercent, DiscountAmount, StartDate, EndDate, IsActive, MinOrderAmount, MaxDiscountAmount) VALUES
-- Khuyến mãi sản phẩm cụ thể
('Giảm 10% iPhone 15 Pro Max', 1, NULL, 10.00, NULL, '2025-09-01 00:00:00', '2025-09-30 23:59:59', TRUE, 0, 5000000),
('Giảm 15% MacBook Air M3', 9, NULL, 15.00, NULL, '2025-09-15 00:00:00', '2025-10-15 23:59:59', TRUE, 0, 7000000),
('AirPods Pro 2 giảm 1 triệu', 25, NULL, NULL, 1000000, '2025-09-10 00:00:00', '2025-09-25 23:59:59', TRUE, 0, NULL),
('Samsung S24 Ultra giảm 8%', 2, NULL, 8.00, NULL, '2025-09-05 00:00:00', '2025-10-05 23:59:59', TRUE, 0, 3000000),
('iPad Pro M2 giảm 12%', 17, NULL, 12.00, NULL, '2025-09-20 00:00:00', '2025-10-20 23:59:59', TRUE, 0, 4000000),
('Gaming Laptop MSI giảm 2 triệu', 15, NULL, NULL, 2000000, '2025-09-08 00:00:00', '2025-09-28 23:59:59', TRUE, 0, NULL),
('Apple Watch Series 9 giảm 10%', 29, NULL, 10.00, NULL, '2025-09-12 00:00:00', '2025-10-12 23:59:59', TRUE, 0, 1500000),
('Sony WH-1000XM5 giảm 15%', 26, NULL, 15.00, NULL, '2025-09-18 00:00:00', '2025-10-18 23:59:59', TRUE, 0, 1200000),

-- Khuyến mãi theo danh mục
('Giảm 5% toàn bộ điện thoại', NULL, 1, 5.00, NULL, '2025-09-01 00:00:00', '2025-12-31 23:59:59', TRUE, 10000000, 2000000),
('Laptop giảm 7% cho sinh viên', NULL, 2, 7.00, NULL, '2025-09-01 00:00:00', '2025-10-31 23:59:59', TRUE, 15000000, 5000000),
('Phụ kiện điện thoại mua 2 tặng 1', NULL, 4, 33.00, NULL, '2025-09-15 00:00:00', '2025-09-30 23:59:59', TRUE, 1000000, 500000),
('Tai nghe - Loa giảm 20%', NULL, 6, 20.00, NULL, '2025-09-10 00:00:00', '2025-09-25 23:59:59', TRUE, 2000000, 3000000),
('Smart Home combo giảm 25%', NULL, 10, 25.00, NULL, '2025-09-20 00:00:00', '2025-10-15 23:59:59', TRUE, 5000000, 2000000),

-- Khuyến mãi tổng đơn hàng
('Giảm 500k cho đơn từ 20 triệu', NULL, NULL, NULL, 500000, '2025-09-01 00:00:00', '2025-12-31 23:59:59', TRUE, 20000000, NULL),
('Giảm 1 triệu cho đơn từ 50 triệu', NULL, NULL, NULL, 1000000, '2025-09-01 00:00:00', '2025-12-31 23:59:59', TRUE, 50000000, NULL),
('Giảm 2% cho đơn từ 30 triệu', NULL, NULL, 2.00, NULL, '2025-09-15 00:00:00', '2025-11-15 23:59:59', TRUE, 30000000, 1500000),

-- Khuyến mãi hết hạn
('Back to School - Laptop giảm 10%', NULL, 2, 10.00, NULL, '2025-08-01 00:00:00', '2025-08-31 23:59:59', FALSE, 10000000, 4000000),
('Tết Sale iPhone giảm 15%', NULL, 1, 15.00, NULL, '2025-01-15 00:00:00', '2025-02-15 23:59:59', FALSE, 15000000, 6000000),
('Valentine Gaming Setup', NULL, 9, 20.00, NULL, '2025-02-10 00:00:00', '2025-02-20 23:59:59', FALSE, 10000000, 3000000),
('Flash Sale Camera 30%', NULL, 8, 30.00, NULL, '2025-03-01 00:00:00', '2025-03-03 23:59:59', FALSE, 0, 10000000);

-- Support Tickets (25 tickets)
INSERT INTO support_tickets (CustomerId, Subject, Message, Status, Priority, AssignedTo, Resolution, ResolvedAt) VALUES
(1, 'Không thanh toán được bằng thẻ VISA', 'Em đang muốn mua iPhone 15 Pro Max nhưng thanh toán bằng thẻ VISA không được. Lỗi "Payment failed". Mong shop hỗ trợ.', 'Resolved', 'High', 'Nguyễn Thị Support', 'Đã hỗ trợ khách hàng thanh toán qua phương thức khác. Vấn đề do ngân hàng tạm khóa giao dịch online.', '2025-09-20 14:30:00'),

(2, 'Hỏi về bảo hành Dell XPS 13 Plus', 'Chào shop, em muốn hỏi laptop Dell XPS 13 Plus có bảo hành mấy năm? Bảo hành tại đâu và có bao gồm pin không ạ?', 'In Progress', 'Medium', 'Trần Văn Tech', NULL, NULL),

(3, 'AirPods Pro 2 giao hàng chậm', 'Em đặt AirPods Pro 2 từ hôm qua mà chưa thấy giao. Đơn hàng hiển thị "Shipped" nhưng không có thông tin vận chuyển.', 'Closed', 'Medium', 'Lê Thị Shipping', 'Đã giao hàng thành công. Shipper gặp khó khăn do thời tiết.', '2025-09-19 16:45:00'),

(4, 'MacBook Air M3 bị lỗi màn hình', 'MacBook em mua tuần trước bị xuất hiện đường kẻ dọc màn hình. Em có thể đổi máy không ạ?', 'Open', 'High', 'Phạm Minh Tech', NULL, NULL),

(5, 'Muốn đổi màu iPhone 14 Pro', 'Em đặt iPhone 14 Pro màu đen nhưng giờ muốn đổi sang màu tím. Đơn hàng chưa giao, có thể đổi không shop?', 'Resolved', 'Low', 'Nguyễn Thị Support', 'Đã hỗ trợ đổi màu thành công. Khách hàng hài lòng.', '2025-09-18 10:20:00'),

(6, 'Hủy đơn hàng Xbox Series X', 'Em muốn hủy đơn Xbox Series X vì có việc đột xuất cần tiền. Mong shop hỗ trợ hoàn tiền nhanh.', 'In Progress', 'Medium', 'Võ Thị Finance', NULL, NULL),

(7, 'Samsung Galaxy Watch 6 không kết nối được', 'Đồng hồ em mua không kết nối được với điện thoại iPhone. Shop có hỗ trợ setup không ạ?', 'Waiting Customer', 'Low', 'Đỗ Văn Tech', 'Đã hướng dẫn qua điện thoại. Chờ khách hàng thử lại và feedback.', NULL),

(8, 'Yêu cầu xuất hóa đơn VAT', 'Em cần xuất hóa đơn VAT cho đơn hàng MacBook Pro 14 inch để báo cáo công ty. Thông tin công ty em gửi kèm.', 'Open', 'Medium', 'Lưu Thị Admin', NULL, NULL),

(9, 'Camera Canon R6 Mark II thiếu phụ kiện', 'Em nhận máy ảnh nhưng thiếu dây USB-C và thẻ nhớ như quảng cáo. Mong shop kiểm tra lại.', 'Open', 'High', 'Cao Văn Check', NULL, NULL),

(10, 'HomePod mini không phát được tiếng Việt', 'Em setup HomePod mini nhưng Siri không hiểu tiếng Việt. Shop có hướng dẫn cách cài đặt không?', 'Resolved', 'Low', 'Bùi Thị Support', 'Đã hướng dẫn cài đặt ngôn ngữ. HomePod mini hiện chưa hỗ trợ đầy đủ tiếng Việt.', '2025-09-17 11:15:00'),

(11, 'PlayStation 5 bị lỗi blue light', 'PS5 em mua bị lỗi đèn xanh, không boot được. Em có thể mang đến store để check không?', 'In Progress', 'High', 'Trịnh Văn Gaming', NULL, NULL),

(12, 'Muốn trả góp iPad Pro M2', 'Em muốn mua iPad Pro M2 trả góp 0%. Điều kiện và thủ tục như thế nào shop?', 'Waiting Customer', 'Medium', 'Dương Thị Finance', 'Đã gửi thông tin trả góp qua email. Chờ khách hàng cung cấp giấy tờ.', NULL),

(13, 'Logitech MX Master 3S chuột trái không nhấn được', 'Chuột em mua 2 tuần trước giờ nút trái bị liệt, không click được. Có thể bảo hành không ạ?', 'Open', 'Medium', 'Phùng Văn Tech', NULL, NULL),

(14, 'Ring Video Doorbell 4 không ghi âm', 'Chuông cửa thông minh chỉ quay được video, không ghi được âm thanh. Em cần hỗ trợ cài đặt.', 'Open', 'Low', 'Lê Thị SmartHome', NULL, NULL),

(15, 'Đổi size túi laptop', 'Túi laptop em đặt size 13 inch nhưng máy 14 inch không vừa. Có thể đổi size không shop?', 'Resolved', 'Low', 'Nguyễn Thị Support', 'Đã hỗ trợ đổi size túi 14 inch. Khách hàng đồng ý chênh lệch giá.', '2025-09-16 15:30:00'),

(16, 'Anker PowerBank sạc chậm', 'Pin sạc dự phòng Anker 20000mAh sạc rất chậm cho iPhone. Có phải hàng lỗi không shop?', 'In Progress', 'Medium', 'Võ Minh Tech', NULL, NULL),

(17, 'Philips Hue không kết nối wifi', 'Bộ đèn thông minh Philips Hue không kết nối được wifi nhà em. Mạng bình thường, các thiết bị khác ok.', 'Open', 'Medium', 'Lê Thị SmartHome', NULL, NULL),

(18, 'Garmin Forerunner 965 thiếu dây đeo', 'Đồng hồ Garmin em nhận thiếu dây đeo silicon. Trong hộp chỉ có dây nylon thôi ạ.', 'Open', 'High', 'Đặng Thị Check', NULL, NULL),

(19, 'JBL Charge 5 loa rè', 'Loa JBL mới mua 3 ngày bị rè khi mở volume lớn. Em có thể đổi được không ạ?', 'Resolved', 'High', 'Lưu Văn Audio', 'Đã đổi loa mới cho khách hàng. Loa cũ có lỗi driver.', '2025-09-15 13:20:00'),

(20, 'Yêu cầu giao hàng nhanh', 'Em cần gấp MacBook Air M3 để làm việc. Có thể giao trong ngày được không? Em ở quận 1.', 'Resolved', 'Urgent', 'Cao Thị Express', 'Đã giao hàng trong 2 tiếng. Khách hàng hài lòng với dịch vụ.', '2025-09-21 09:45:00'),

(1, 'Cảm ơn dịch vụ tốt', 'Em cảm ơn shop đã hỗ trợ nhiệt tình vấn đề thanh toán lần trước. iPhone 15 Pro Max dùng rất tốt!', 'Closed', 'Low', NULL, 'Cảm ơn feedback tích cực của khách hàng.', '2025-09-20 16:00:00'),

(2, 'Dell XPS 13 Plus có case không?', 'Shop có bán case, túi đựng riêng cho Dell XPS 13 Plus không? Em muốn mua thêm.', 'Open', 'Low', 'Trần Thị Accessories', NULL, NULL),

(5, 'iPhone 14 Pro tím pin chai nhanh', 'iPhone em mua tháng trước pin tụt nhanh lạ. Từ sáng đến trưa đã hết 70%. Có phải lỗi pin không?', 'In Progress', 'Medium', 'Phạm Minh Tech', NULL, NULL),

(8, 'MacBook Pro 14 inch nóng máy', 'MacBook Pro khi dùng app thiết kế nóng máy và quạt chạy to. Có bình thường không shop?', 'Waiting Customer', 'Low', 'Đỗ Văn Tech', 'Đã hướng dẫn tối ưu hiệu năng và kiểm tra Activity Monitor. Chờ feedback.', NULL),

(12, 'Đã nhận iPad Pro M2 hài lòng', 'iPad Pro M2 em nhận rồi, rất đẹp và nhanh. Cảm ơn shop tư vấn tốt!', 'Closed', 'Low', NULL, 'Khách hàng hài lòng với sản phẩm.', '2025-09-19 14:10:00');

-- Views để báo cáo
CREATE VIEW customer_order_summary AS
SELECT 
    c.CustomerId,
    c.Name,
    c.Email,
    COUNT(o.OrderId) as TotalOrders,
    COALESCE(SUM(CASE WHEN o.Status = 'Completed' THEN o.TotalAmount ELSE 0 END), 0) as CompletedOrderValue,
    COALESCE(SUM(o.TotalAmount), 0) as TotalOrderValue,
    MAX(o.OrderDate) as LastOrderDate
FROM customers c
LEFT JOIN orders o ON c.CustomerId = o.CustomerId
GROUP BY c.CustomerId, c.Name, c.Email;

CREATE VIEW product_sales_summary AS
SELECT 
    p.ProductId,
    p.ProductName,
    c.CategoryName,
    p.Price,
    p.Quantity as StockQuantity,
    COALESCE(SUM(od.Quantity), 0) as TotalSold,
    COALESCE(SUM(od.SubTotal), 0) as Revenue,
    COALESCE(AVG(od.UnitPrice), p.Price) as AvgSellPrice
FROM products p
JOIN categories c ON p.CategoryId = c.CategoryId
LEFT JOIN order_details od ON p.ProductId = od.ProductId
LEFT JOIN orders o ON od.OrderId = o.OrderId AND o.Status IN ('Completed', 'Delivered')
WHERE p.IsActive = TRUE
GROUP BY p.ProductId, p.ProductName, c.CategoryName, p.Price, p.Quantity;

CREATE VIEW daily_sales_report AS
SELECT 
    DATE(o.OrderDate) as SaleDate,
    COUNT(DISTINCT o.OrderId) as TotalOrders,
    COUNT(DISTINCT o.CustomerId) as UniqueCustomers,
    SUM(CASE WHEN o.Status IN ('Completed', 'Delivered') THEN o.TotalAmount ELSE 0 END) as CompletedSales,
    SUM(o.TotalAmount) as TotalSales,
    AVG(CASE WHEN o.Status IN ('Completed', 'Delivered') THEN o.TotalAmount END) as AvgOrderValue
FROM orders o
GROUP BY DATE(o.OrderDate)
ORDER BY SaleDate DESC;

-- Indexes để tối ưu hiệu suất
CREATE INDEX idx_products_category ON products(CategoryId);
CREATE INDEX idx_products_active ON products(IsActive);
CREATE INDEX idx_orders_customer ON orders(CustomerId);
CREATE INDEX idx_orders_date ON orders(OrderDate);
CREATE INDEX idx_orders_status ON orders(Status);
CREATE INDEX idx_order_details_order ON order_details(OrderId);
CREATE INDEX idx_order_details_product ON order_details(ProductId);
CREATE INDEX idx_promotions_dates ON promotions(StartDate, EndDate);
CREATE INDEX idx_promotions_active ON promotions(IsActive);
CREATE INDEX idx_support_tickets_customer ON support_tickets(CustomerId);
CREATE INDEX idx_support_tickets_status ON support_tickets(Status);
CREATE INDEX idx_customers_email ON customers(Email);

-- Bật foreign keys
PRAGMA foreign_keys = ON;

-- Thống kê dữ liệu đã tạo
SELECT 'Customers' as TableName, COUNT(*) as RecordCount FROM customers
UNION ALL
SELECT 'Categories' as TableName, COUNT(*) as RecordCount FROM categories  
UNION ALL
SELECT 'Products' as TableName, COUNT(*) as RecordCount FROM products
UNION ALL
SELECT 'Orders' as TableName, COUNT(*) as RecordCount FROM orders
UNION ALL
SELECT 'Order Details' as TableName, COUNT(*) as RecordCount FROM order_details
UNION ALL
SELECT 'Promotions' as TableName, COUNT(*) as RecordCount FROM promotions
UNION ALL
SELECT 'Support Tickets' as TableName, COUNT(*) as RecordCount FROM support_tickets;