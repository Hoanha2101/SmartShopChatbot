from langchain.tools import tool
from typing import List, Dict
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
# # ----------- ADD PRODUCT TOOL -----------
# @tool
# def add_product(name: str, category_id: int, price: float, quantity: int, description: str = None, image_url: str = None, is_active: bool = True):
#     """
#     Thêm sản phẩm mới vào cửa hàng.
#     Cần nhập: tên sản phẩm, mã danh mục, giá và số lượng.
#     Có thể thêm: mô tả, ảnh sản phẩm, trạng thái (is_active).
#     Trả về thông tin sản phẩm vừa được thêm.
#     """
#     q = """
#         INSERT INTO products 
#         (ProductName, CategoryId, Description, Price, Quantity, ImageUrl, IsActive, CreatedAt, UpdatedAt)
#         VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
#     """
#     run_query(q, (name, category_id, description, price, quantity, image_url, int(is_active)))

#     # Lấy lại sản phẩm vừa thêm để confirm
#     q2 = """
#         SELECT ProductId, ProductName, CategoryId, Description, Price, Quantity, ImageUrl, IsActive, CreatedAt
#         FROM products
#         WHERE ProductName = ?
#         ORDER BY ProductId DESC
#         LIMIT 1
#     """
#     row = run_query(q2, (name,), fetch=True)[0]

#     return {
#         "id": row[0],
#         "name": row[1],
#         "category_id": row[2],
#         "description": row[3],
#         "price": row[4],
#         "quantity": row[5],
#         "image_url": row[6],
#         "is_active": bool(row[7]),
#         "created_at": row[8]
#     }


# @ 2. Hỗ trợ đặt hàng (Order Assistance)
# ----------- ADD NEW ORDER TOOL -----------

# 2.1 Tạo đơn hàng mới: Khi khách chọn sản phẩm, 
# bot thêm vào giỏ hàng, hỏi “bạn muốn mua mấy cái?, ...”.

# ----------- ADD ORDER TOOL -----------
# ----------- HELPER FUNCTIONS -----------
def get_order_by_id(order_id: int):
    """Lấy thông tin đơn hàng theo ID"""
    try:
        order_info = run_query(
            """SELECT o.OrderId, o.CustomerId, c.Name, o.OrderDate, o.Status, 
                      o.TotalAmount, o.ShippingAddress, o.PaymentMethod, o.Notes
               FROM orders o
               JOIN customers c ON o.CustomerId = c.CustomerId
               WHERE o.OrderId = ?""",
            (order_id,), fetch=True
        )
        
        if not order_info:
            return {"error": f"Không tìm thấy đơn hàng ID {order_id}"}
        
        order = order_info[0]
        
        # Lấy chi tiết sản phẩm
        items = run_query(
            """SELECT od.ProductId, p.ProductName, od.Quantity, od.UnitPrice, od.SubTotal
               FROM order_details od
               JOIN products p ON od.ProductId = p.ProductId
               WHERE od.OrderId = ?""",
            (order_id,), fetch=True
        )
        
        return {
            "order_id": order[0],
            "customer_id": order[1],
            "customer_name": order[2],
            "order_date": order[3],
            "status": order[4],
            "total_amount": order[5],
            "shipping_address": order[6],
            "payment_method": order[7],
            "notes": order[8],
            "items": [
                {
                    "product_id": item[0],
                    "product_name": item[1],
                    "quantity": item[2],
                    "unit_price": item[3],
                    "subtotal": item[4]
                }
                for item in items
            ]
        }
    except Exception as e:
        return {"error": str(e)}
    
@tool
def add_order(
    customer_id: int,
    items: List[Dict[str, int]],
    shipping_address: str,
    payment_method: str,
    notes: str = None
):
    """
    Tạo mới một đơn hàng.
    - customer_id: mã khách hàng đặt hàng
    - items: danh sách sản phẩm, mỗi item có {product_id, quantity}
    - shipping_address: địa chỉ giao hàng
    - payment_method: phương thức thanh toán ('Cash', 'Credit Card', 'Debit Card', 'Bank Transfer', 'E-Wallet')
    - notes: ghi chú thêm
    
    Trả về:
    - success: True/False
    - order_id: mã đơn hàng
    - total_amount: tổng tiền
    - items: chi tiết sản phẩm
    - error: thông báo lỗi (nếu có)
    """
    try:
        # 1. Gộp các sản phẩm trùng lặp
        merged_items = {}
        for item in items:
            pid = item["product_id"]
            qty = item["quantity"]
            if qty <= 0:
                return {"error": f"Số lượng sản phẩm phải > 0 (ProductId: {pid})"}
            
            if pid in merged_items:
                merged_items[pid] += qty
            else:
                merged_items[pid] = qty

        # 2. Validate customer
        customer_check = run_query(
            "SELECT Name FROM customers WHERE CustomerId = ?",
            (customer_id,), fetch=True
        )
        if not customer_check:
            return {"error": f"Khách hàng ID {customer_id} không tồn tại"}

        # 3. Validate payment method
        valid_payments = ['Cash', 'Credit Card', 'Debit Card', 'Bank Transfer', 'E-Wallet']
        if payment_method not in valid_payments:
            return {"error": f"Phương thức thanh toán không hợp lệ. Chọn: {', '.join(valid_payments)}"}

        # 4. Kiểm tra sản phẩm & tính tổng tiền
        total = 0
        order_items = []
        for pid, qty in merged_items.items():
            row = run_query(
                "SELECT Price, Quantity, ProductName FROM products WHERE ProductId = ? AND IsActive = 1", 
                (pid,), fetch=True
            )
            if not row:
                return {"error": f"Sản phẩm ID {pid} không tồn tại hoặc đã ngừng bán"}
            
            price, stock, pname = row[0]
            if stock < qty:
                return {"error": f"Sản phẩm '{pname}' không đủ hàng (còn {stock}, cần {qty})"}
            
            total += price * qty
            order_items.append({"pid": pid, "qty": qty, "price": price, "name": pname})

        if total <= 0:
            return {"error": "Tổng tiền đơn hàng phải > 0"}

        # 5. Tạo đơn hàng
        run_query(
            """INSERT INTO orders (CustomerId, Status, ShippingAddress, PaymentMethod, Notes, TotalAmount)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (customer_id, "Pending", shipping_address, payment_method, notes, total),
            fetch=False
        )
        
        # 6. Lấy OrderId (với fallback nếu last_insert_rowid() = 0)
        order_id_result = run_query("SELECT last_insert_rowid()", fetch=True)
        order_id = order_id_result[0][0]
        
        if order_id == 0:
            # Fallback: tìm OrderId mới nhất của customer này
            alt_order = run_query(
                "SELECT OrderId FROM orders WHERE CustomerId = ? ORDER BY OrderDate DESC LIMIT 1",
                (customer_id,), fetch=True
            )
            if alt_order:
                order_id = alt_order[0][0]
            else:
                return {"error": "Không thể tạo đơn hàng - lỗi database"}

        # 7. Kiểm tra OrderId đã có chi tiết chưa (để tránh trùng lặp)
        existing_details = run_query(
            "SELECT COUNT(*) FROM order_details WHERE OrderId = ?",
            (order_id,), fetch=True
        )
        if existing_details[0][0] > 0:
            return {"error": f"Đơn hàng ID {order_id} đã có chi tiết. Vui lòng thử lại."}

        # 8. Thêm chi tiết đơn hàng & trừ tồn kho
        for oi in order_items:
            # Thêm chi tiết
            run_query(
                """INSERT INTO order_details (OrderId, ProductId, Quantity, UnitPrice)
                   VALUES (?, ?, ?, ?)""",
                (order_id, oi["pid"], oi["qty"], oi["price"]),
                fetch=False
            )
            
            # Trừ tồn kho
            run_query(
                "UPDATE products SET Quantity = Quantity - ?, UpdatedAt = CURRENT_TIMESTAMP WHERE ProductId = ?",
                (oi["qty"], oi["pid"]),
                fetch=False
            )

        # 9. Lấy thông tin chi tiết đơn hàng
        details = run_query(
            """SELECT od.ProductId, p.ProductName, od.Quantity, od.UnitPrice, od.SubTotal
               FROM order_details od
               JOIN products p ON od.ProductId = p.ProductId
               WHERE od.OrderId = ?""",
            (order_id,), fetch=True
        )
        
        # 10. Lấy tổng tiền cuối cùng (từ trigger)
        final_total = run_query(
            "SELECT TotalAmount FROM orders WHERE OrderId = ?",
            (order_id,), fetch=True
        )

        return {
            "success": True,
            "order_id": order_id,
            "customer_id": customer_id,
            "customer_name": customer_check[0][0],
            "total_amount": final_total[0][0] if final_total else total,
            "status": "Pending",
            "shipping_address": shipping_address,
            "payment_method": payment_method,
            "notes": notes,
            "items": [
                {
                    "product_id": d[0], 
                    "product_name": d[1], 
                    "quantity": d[2], 
                    "unit_price": d[3],
                    "subtotal": d[4]
                }
                for d in details
            ]
        }

    except Exception as e:
        return {"error": f"Lỗi hệ thống: {str(e)}"}


# 2.2 Hiển thị giỏ hàng: Cho khách xem giỏ hàng hiện tại.
# ----------- VIEW CART TOOL -----------
# ----------- VIEW CART TOOL - FIXED -----------
@tool
def view_cart(customer_id: int):
    """
    Hiển thị giỏ hàng hiện tại của khách hàng.
    Giỏ hàng = tất cả đơn hàng ở trạng thái 'Pending' của khách hàng.
    
    Trả về:
    - customer_info: thông tin khách hàng
    - pending_orders: danh sách đơn hàng pending (có thể có nhiều đơn)
    - total_cart_value: tổng giá trị tất cả đơn pending
    - item_count: tổng số sản phẩm trong giỏ
    """
    try:
        # 1. Kiểm tra khách hàng tồn tại
        customer_info = run_query(
            "SELECT CustomerId, Name, Email, Phone FROM customers WHERE CustomerId = ?",
            (customer_id,), fetch=True
        )
        
        if not customer_info:
            return {"error": f"Không tìm thấy khách hàng ID {customer_id}"}
        
        customer = customer_info[0]
        
        # 2. Lấy tất cả đơn hàng pending của khách hàng
        pending_orders = run_query(
            """SELECT OrderId, TotalAmount, OrderDate, ShippingAddress, PaymentMethod, Notes
               FROM orders 
               WHERE CustomerId = ? AND Status = 'Pending' 
               ORDER BY OrderDate DESC""",
            (customer_id,), fetch=True
        )
        
        if not pending_orders:
            return {
                "customer_id": customer[0],
                "customer_name": customer[1],
                "customer_email": customer[2],
                "customer_phone": customer[3],
                "message": "Giỏ hàng hiện tại đang trống.",
                "pending_orders": [],
                "total_cart_value": 0,
                "item_count": 0
            }
        
        # 3. Lấy chi tiết từng đơn hàng
        orders_detail = []
        total_cart_value = 0
        total_item_count = 0
        
        for order in pending_orders:
            order_id, total_amount, order_date, shipping_addr, payment_method, notes = order
            
            # Lấy chi tiết sản phẩm của đơn hàng này
            items = run_query(
                """SELECT od.ProductId, p.ProductName, p.Description, od.Quantity, 
                          od.UnitPrice, od.SubTotal, p.ImageUrl
                   FROM order_details od
                   JOIN products p ON od.ProductId = p.ProductId
                   WHERE od.OrderId = ?
                   ORDER BY od.OrderDetailId""",
                (order_id,), fetch=True
            )
            
            # Format chi tiết sản phẩm
            formatted_items = []
            order_item_count = 0
            
            for item in items:
                product_id, product_name, description, quantity, unit_price, subtotal, image_url = item
                
                formatted_items.append({
                    "product_id": product_id,
                    "product_name": product_name,
                    "description": description,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "subtotal": subtotal,
                    "image_url": image_url
                })
                
                order_item_count += quantity
            
            # Thêm thông tin đơn hàng
            orders_detail.append({
                "order_id": order_id,
                "order_date": order_date,
                "total_amount": total_amount,
                "shipping_address": shipping_addr,
                "payment_method": payment_method,
                "notes": notes,
                "item_count": order_item_count,
                "items": formatted_items
            })
            
            total_cart_value += total_amount
            total_item_count += order_item_count
        
        return {
            "success": True,
            "customer_id": customer[0],
            "customer_name": customer[1],
            "customer_email": customer[2],
            "customer_phone": customer[3],
            "pending_orders": orders_detail,
            "total_cart_value": total_cart_value,
            "item_count": total_item_count,
            "order_count": len(pending_orders)
        }
        
    except Exception as e:
        return {"error": f"Lỗi khi xem giỏ hàng: {str(e)}"}


# ----------- RELATED CART TOOLS -----------
@tool 
def get_latest_cart(customer_id: int):
    """
    Lấy đơn hàng pending mới nhất (giỏ hàng hiện tại đang được chỉnh sửa)
    """
    try:
        # Kiểm tra customer
        customer_check = run_query(
            "SELECT Name FROM customers WHERE CustomerId = ?",
            (customer_id,), fetch=True
        )
        if not customer_check:
            return {"error": f"Không tìm thấy khách hàng ID {customer_id}"}
        
        # Lấy đơn pending mới nhất
        latest_order = run_query(
            """SELECT OrderId, TotalAmount, OrderDate, ShippingAddress, PaymentMethod, Notes
               FROM orders 
               WHERE CustomerId = ? AND Status = 'Pending' 
               ORDER BY OrderDate DESC LIMIT 1""",
            (customer_id,), fetch=True
        )
        
        if not latest_order:
            return {
                "customer_name": customer_check[0][0],
                "message": "Chưa có đơn hàng nào trong giỏ."
            }
        
        order_id, total, order_date, shipping_addr, payment_method, notes = latest_order[0]
        
        # Lấy chi tiết sản phẩm
        items = run_query(
            """SELECT od.ProductId, p.ProductName, od.Quantity, od.UnitPrice, od.SubTotal
               FROM order_details od
               JOIN products p ON od.ProductId = p.ProductId
               WHERE od.OrderId = ?""",
            (order_id,), fetch=True
        )
        
        return {
            "success": True,
            "customer_name": customer_check[0][0],
            "order_id": order_id,
            "order_date": order_date,
            "total_amount": total,
            "shipping_address": shipping_addr,
            "payment_method": payment_method,
            "notes": notes,
            "items": [
                {
                    "product_id": item[0],
                    "product_name": item[1], 
                    "quantity": item[2],
                    "unit_price": item[3],
                    "subtotal": item[4]
                }
                for item in items
            ]
        }
        
    except Exception as e:
        return {"error": str(e)}


@tool
def clear_cart(customer_id: int, order_id: int = None):
    """
    Xóa giỏ hàng (hủy đơn hàng pending)
    - Nếu không chỉ định order_id: xóa tất cả đơn pending
    - Nếu có order_id: chỉ xóa đơn đó
    """
    try:
        # Kiểm tra customer
        customer_check = run_query(
            "SELECT Name FROM customers WHERE CustomerId = ?",
            (customer_id,), fetch=True
        )
        if not customer_check:
            return {"error": f"Không tìm thấy khách hàng ID {customer_id}"}
        
        if order_id:
            # Xóa đơn hàng cụ thể
            # Kiểm tra đơn hàng thuộc về customer và đang pending
            order_check = run_query(
                "SELECT OrderId FROM orders WHERE OrderId = ? AND CustomerId = ? AND Status = 'Pending'",
                (order_id, customer_id), fetch=True
            )
            
            if not order_check:
                return {"error": f"Không tìm thấy đơn hàng pending ID {order_id} của khách hàng này"}
            
            # Lấy thông tin sản phẩm để hoàn lại tồn kho
            items_to_restore = run_query(
                "SELECT ProductId, Quantity FROM order_details WHERE OrderId = ?",
                (order_id,), fetch=True
            )
            
            # Hoàn lại tồn kho
            for product_id, quantity in items_to_restore:
                run_query(
                    "UPDATE products SET Quantity = Quantity + ? WHERE ProductId = ?",
                    (quantity, product_id), fetch=False
                )
            
            # Xóa đơn hàng (order_details sẽ tự động xóa do CASCADE)
            run_query(
                "DELETE FROM orders WHERE OrderId = ?",
                (order_id,), fetch=False
            )
            
            return {
                "success": True,
                "message": f"Đã xóa đơn hàng #{order_id} khỏi giỏ hàng",
                "restored_items": len(items_to_restore)
            }
        else:
            # Xóa tất cả đơn pending
            pending_orders = run_query(
                "SELECT OrderId FROM orders WHERE CustomerId = ? AND Status = 'Pending'",
                (customer_id,), fetch=True
            )
            
            if not pending_orders:
                return {"message": "Giỏ hàng đã trống"}
            
            total_restored = 0
            for (order_id_to_delete,) in pending_orders:
                # Hoàn lại tồn kho
                items_to_restore = run_query(
                    "SELECT ProductId, Quantity FROM order_details WHERE OrderId = ?",
                    (order_id_to_delete,), fetch=True
                )
                
                for product_id, quantity in items_to_restore:
                    run_query(
                        "UPDATE products SET Quantity = Quantity + ? WHERE ProductId = ?",
                        (quantity, product_id), fetch=False
                    )
                    total_restored += quantity
                
                # Xóa đơn hàng
                run_query(
                    "DELETE FROM orders WHERE OrderId = ?",
                    (order_id_to_delete,), fetch=False
                )
            
            return {
                "success": True,
                "message": f"Đã xóa {len(pending_orders)} đơn hàng khỏi giỏ hàng",
                "cleared_orders": len(pending_orders),
                "restored_items": total_restored
            }
            
    except Exception as e:
        return {"error": str(e)}

# 2.3 Xác nhận & thanh toán: Bot hỏi địa chỉ, số điện thoại, phương thức thanh toán.
# 2.4 Theo dõi đơn hàng: Khách có thể hỏi “Đơn hàng #1234 của tôi đang ở đâu?”.

# @ 3. Quản lý tài khoản khách hàng (Customer Management)
# 3.1 Đăng ký khách hàng mới:

@tool
def register_customer(name: str, email: str, phone: str = None, address: str = None):
    """
    Đăng ký khách hàng mới.
    - name: Tên khách hàng (bắt buộc)
    - email: Email khách hàng (bắt buộc, duy nhất)
    - phone: Số điện thoại (tùy chọn)
    - address: Địa chỉ (tùy chọn)

    Trả về thông tin khách hàng vừa đăng ký hoặc lỗi nếu email đã tồn tại.
    """
    try:
        # Kiểm tra email đã tồn tại chưa
        existing = run_query("SELECT CustomerId FROM customers WHERE Email = ?", (email,), fetch=True)
        if existing:
            return {"error": f"Email {email} đã được sử dụng"}

        # Thêm khách hàng mới
        run_query(
            """
            INSERT INTO customers (Name, Email, Phone, Address)
            VALUES (?, ?, ?, ?)
            """,
            (name, email, phone, address),
            fetch=False
        )

        # Lấy ID vừa thêm
        customer_id = run_query("SELECT last_insert_rowid()", fetch=True)[0][0]

        # Trả về thông tin khách hàng
        return {
            "customer_id": customer_id,
            "name": name,
            "email": email,
            "phone": phone,
            "address": address
        }

    except Exception as e:
        return {"error": str(e)}
    
# 3.2 Tra cứu thông tin khách hàng
@tool
def get_customer_info(customer_id: int):
    """
    Tra cứu thông tin khách hàng theo ID.
    Khách có thể hỏi “Thông tin của tôi lưu thế nào?”.
    """
    try:
        row = run_query(
            """
            SELECT CustomerId, Name, Email, Phone, Address, CreatedAt, UpdatedAt
            FROM customers
            WHERE CustomerId = ?
            """,
            (customer_id,), fetch=True
        )
        if not row:
            return {"error": f"Không tìm thấy khách hàng ID {customer_id}"}

        r = row[0]
        return {
            "customer_id": r[0],
            "name": r[1],
            "email": r[2],
            "phone": r[3],
            "address": r[4],
            "created_at": r[5],
            "updated_at": r[6]
        }

    except Exception as e:
        return {"error": str(e)}

# 3.3 Cập nhật thông tin cá nhân
# ----------- UPDATE CUSTOMER INFO TOOL -----------
@tool
def update_customer_info(customer_id: int, field: str, value: str):
    """
    Cập nhật thông tin cá nhân của khách hàng.
    - customer_id: mã khách hàng
    - field: trường cần cập nhật (Name, Email, Phone, Address)
    - value: giá trị mới
    
    Ví dụ: đổi số điện thoại, cập nhật địa chỉ...
    """
    try:
        allowed_fields = ["Name", "Email", "Phone", "Address"]
        if field not in allowed_fields:
            return {"error": f"Trường '{field}' không được phép cập nhật"}

        # Nếu update Email -> check trùng
        if field == "Email":
            exists = run_query("SELECT CustomerId FROM customers WHERE Email = ?", (value,), fetch=True)
            if exists:
                return {"error": f"Email {value} đã tồn tại"}

        # Update
        query = f"UPDATE customers SET {field} = ?, UpdatedAt = datetime('now') WHERE CustomerId = ?"
        run_query(query, (value, customer_id), fetch=False)

        # Trả về thông tin sau khi update
        return get_customer_info(customer_id)

    except Exception as e:
        return {"error": str(e)}

# --------------------------------------------------------------------

safe_tools = [smart_search,
              check_categories, list_products_by_category,
              get_all_products, get_product_by_name, 
              get_discounted_products,
              compare_products]

sensitive_tools = [add_order,
                   view_cart, 
                   register_customer,
                   get_customer_info, 
                   update_customer_info
                   ]