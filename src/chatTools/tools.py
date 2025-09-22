from langchain.tools import tool
from ..utils import run_query
from ..models import tavilySearch

# ---------------- SAFE TOOLS ----------------

# *** Tavily search
@tool
def smart_search(query: str):
    """
    Tìm kiếm thông tin chung trên web.
    Sử dụng Tavily để tìm kiếm và trả về kết quả.
    """
    results = tavilySearch.search(query)
    return results

# @1. Khám phá sản phẩm (Product Discovery)
# 1.1 Gợi ý sản phẩm theo danh mục: Khách hỏi “có laptop không?”, 
# bot trả danh sách laptop kèm giá, mô tả ngắn.
# ----------- CATEGORY LIST TOOL -----------
@tool
def check_categories():
    """
    Lấy danh sách tất cả danh mục sản phẩm trong cửa hàng.
    Trả về tổng số lượng và danh sách gồm CategoryId, CategoryName, Description.
    """
    q = """
        SELECT CategoryId, CategoryName, 
               COALESCE(Description, 'Không có mô tả') AS Description
        FROM categories
        ORDER BY CategoryName
    """
    rows = run_query(q, fetch=True)
    return {
        "total": len(rows),
        "categories": [{"id": r[0], "name": r[1], "description": r[2]} for r in rows]}

# ----------- LIST PRODUCTS BY CATEGORY TOOL -----------
@tool
def list_products_by_category(category_name: str):
    """
    Liệt kê các sản phẩm thuộc một danh mục theo tên (category_name).
    Trả về danh sách sản phẩm gồm ProductId, ProductName, Price, ShortDesc.
    Ví dụ: list_products_by_category("Laptop")
    """
    q = """
        SELECT p.ProductId, p.ProductName, p.Price, 
               COALESCE(p.Description, 'Không có mô tả') AS ShortDesc
        FROM products p
        JOIN categories c ON p.CategoryId = c.CategoryId
        WHERE LOWER(c.CategoryName) = LOWER(?)
        ORDER BY p.ProductName
    """
    rows = run_query(q, (category_name,), fetch=True)
    return [{"id": r[0], "name": r[1], "price": float(r[2]), "description": r[3]} for r in rows]

# 1.2 Tìm sản phẩm theo từ khóa: Khách hỏi “cho tôi điện thoại iPhone 14 Pro”, 
# bot tìm đúng sản phẩm.

# ----------- GET ALL PRODUCTS TOOL -----------
@tool
def get_all_products():
    """
    Lấy toàn bộ danh sách sản phẩm trong cửa hàng.
    Trả về tất cả thông tin: ProductId, ProductName, CategoryId, CategoryName,
    Description, Price, Quantity, ImageUrl, IsActive, CreatedAt, UpdatedAt.
    """
    q = """
        SELECT p.ProductId, p.ProductName, p.CategoryId, c.CategoryName,
               COALESCE(p.Description, 'Không có mô tả') AS Description,
               p.Price, p.Quantity, p.ImageUrl, p.IsActive,
               p.CreatedAt, p.UpdatedAt
        FROM products p
        JOIN categories c ON p.CategoryId = c.CategoryId
        ORDER BY p.ProductName
    """
    rows = run_query(q, fetch=True)
    return [
        {
            "id": r[0],
            "name": r[1],
            "category_id": r[2],
            "category_name": r[3],
            "description": r[4],
            "price": float(r[5]),
            "quantity": r[6],
            "image_url": r[7],
            "is_active": bool(r[8]),
            "created_at": r[9],
            "updated_at": r[10]
        }
        for r in rows
    ]

# ----------- GET PRODUCT BY NAME TOOL -----------
@tool
def get_product_by_name(product_name: str):
    """
    Lấy toàn bộ thông tin của sản phẩm theo tên (ProductName).
    Trả về ProductId, ProductName, CategoryId, CategoryName, Description, Price, Quantity, ImageUrl, IsActive, CreatedAt, UpdatedAt.
    Ví dụ: get_product_by_name("iPhone 15 Pro")
    """
    q = """
        SELECT p.ProductId, p.ProductName, p.CategoryId, c.CategoryName,
               COALESCE(p.Description, 'Không có mô tả') AS Description,
               p.Price, p.Quantity, p.ImageUrl, p.IsActive,
               p.CreatedAt, p.UpdatedAt
        FROM products p
        JOIN categories c ON p.CategoryId = c.CategoryId
        WHERE LOWER(p.ProductName) = LOWER(?)
        LIMIT 1
    """
    rows = run_query(q, (product_name,), fetch=True)
    if not rows:
        return {"message": f"❌ Không tìm thấy sản phẩm tên '{product_name}'"}

    r = rows[0]
    return {
        "id": r[0],
        "name": r[1],
        "category_id": r[2],
        "category_name": r[3],
        "description": r[4],
        "price": float(r[5]),
        "quantity": r[6],
        "image_url": r[7],
        "is_active": bool(r[8]),
        "created_at": r[9],
        "updated_at": r[10]
    }

# 1.3 So sánh sản phẩm: Khách có thể so sánh 2 sản phẩm 
# (ví dụ iPhone 14 vs Samsung S23).

@tool
def compare_products(product1: str, product2: str):
    """
    So sánh hai sản phẩm theo tên.
    Lấy thông tin trong DB (nếu có), và dùng Tavily để bổ sung dữ liệu ngoài.
    Trả về kết quả so sánh chi tiết.
    """
    def get_product_info(name):
        q = """
            SELECT p.ProductId, p.ProductName, c.CategoryName, p.Price, p.Description
            FROM products p
            JOIN categories c ON p.CategoryId = c.CategoryId
            WHERE LOWER(p.ProductName) = LOWER(?)
        """
        rows = run_query(q, (name,), fetch=True)
        if rows:
            r = rows[0]
            return {
                "id": r[0], "name": r[1], "category": r[2],
                "price": float(r[3]), "description": r[4]
            }
        else:
            # fallback: gọi Tavily
            print(f"⚠️ Không tìm thấy '{name}' trong DB, gọi Tavily để bổ sung thông tin.")
            tavily_res = tavilySearch.search(f"Thông tin sản phẩm {name}")
            return {
                "id": None, "name": name,
                "category": "Unknown",
                "price": None,
                "description": tavily_res['results'][0]['content'] if tavily_res['results'] else "Không tìm thấy"
            }

    info1 = get_product_info(product1)
    info2 = get_product_info(product2)

    return {"product1": info1, "product2": info2}

# 1.4 Hiển thị sản phẩm nổi bật/khuyến mãi: 
# Bot chủ động gợi ý sản phẩm đang giảm giá.

# ----------- GET DISCOUNTED PRODUCTS TOOL -----------
@tool
def get_discounted_products():
    """
    Lấy tất cả sản phẩm đang có khuyến mãi (giảm giá).
    Trả về ProductId, ProductName, Giá gốc, Giá sau giảm, loại giảm (theo % hoặc số tiền),
    cùng thông tin khuyến mãi.
    """
    q = """
        SELECT p.ProductId, p.ProductName, p.Price,
               pr.PromotionName,
               pr.DiscountPercent, pr.DiscountAmount,
               pr.StartDate, pr.EndDate
        FROM products p
        JOIN promotions pr 
            ON (pr.ProductId = p.ProductId OR pr.CategoryId = p.CategoryId)
        WHERE pr.IsActive = 1
          AND datetime('now') BETWEEN pr.StartDate AND pr.EndDate
        ORDER BY p.ProductName
    """
    rows = run_query(q, fetch=True)
    if not rows:
        return {"message": "❌ Hiện tại không có sản phẩm nào đang giảm giá."}

    result = []
    for r in rows:
        product_id, name, price, promo_name, percent, amount, start, end = r
        if percent is not None:
            discount_value = price * (percent / 100)
            final_price = price - discount_value
            discount_type = f"{percent}%"
        else:
            discount_value = amount
            final_price = price - discount_value
            discount_type = f"-{amount}"

        if final_price < 0:
            final_price = 0

        result.append({
            "id": product_id,
            "name": name,
            "original_price": float(price),
            "final_price": float(final_price),
            "discount_type": discount_type,
            "promotion": promo_name,
            "valid_from": start,
            "valid_to": end
        })

    return result

# ---------------- SENSITIVE TOOLS ----------------
# ----------- ADD PRODUCT TOOL -----------
@tool
def add_product(name: str, category_id: int, price: float, quantity: int, description: str = None, image_url: str = None, is_active: bool = True):
    """
    Thêm sản phẩm mới vào cửa hàng.
    Cần nhập: tên sản phẩm, mã danh mục, giá và số lượng.
    Có thể thêm: mô tả, ảnh sản phẩm, trạng thái (is_active).
    Trả về thông tin sản phẩm vừa được thêm.
    """
    q = """
        INSERT INTO products 
        (ProductName, CategoryId, Description, Price, Quantity, ImageUrl, IsActive, CreatedAt, UpdatedAt)
        VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
    """
    run_query(q, (name, category_id, description, price, quantity, image_url, int(is_active)))

    # Lấy lại sản phẩm vừa thêm để confirm
    q2 = """
        SELECT ProductId, ProductName, CategoryId, Description, Price, Quantity, ImageUrl, IsActive, CreatedAt
        FROM products
        WHERE ProductName = ?
        ORDER BY ProductId DESC
        LIMIT 1
    """
    row = run_query(q2, (name,), fetch=True)[0]

    return {
        "id": row[0],
        "name": row[1],
        "category_id": row[2],
        "description": row[3],
        "price": row[4],
        "quantity": row[5],
        "image_url": row[6],
        "is_active": bool(row[7]),
        "created_at": row[8]
    }
# @ 2. Hỗ trợ đặt hàng (Order Assistance)


# Tạo đơn hàng mới: Khi khách chọn sản phẩm, 
# bot thêm vào giỏ hàng, hỏi “bạn muốn mua mấy cái?”.

safe_tools = [smart_search,
              check_categories, list_products_by_category,
              get_all_products, get_product_by_name, 
              get_discounted_products,
              compare_products]

sensitive_tools = [add_product]