from langchain.tools import tool
from ..utils import run_query

# ---------------- SAFE TOOLS ----------------


# ----------- CATEGORY COUNT TOOL -----------
@tool
def check_categories():
    """
    Đếm số lượng danh mục sản phẩm hiện có trong hệ thống.
    Trả về số lượng và danh sách tên danh mục.
    """
    q = "SELECT COUNT(*) as TotalCategories FROM categories"
    total = run_query(q)

    q2 = "SELECT CategoryName FROM categories"
    names = run_query(q2, fetch=True)

    return {"total": total[0][0], "categories": [n[0] for n in names]}

# ---------------- LIST PRODUCTS BY CATEGORY NAME TOOL ----------------
@tool
def list_products_by_category_name(category_name: str):
    """
    Liệt kê sản phẩm theo tên danh mục (category_name).
    Ví dụ: list_products_by_category_name("Laptop")
    Trả về danh sách sản phẩm gồm tên, giá, mô tả ngắn.
    """
    q = """
        SELECT p.ProductName, p.Price, 
               COALESCE(p.Description, 'Không có mô tả') AS ShortDesc
        FROM products p
        JOIN categories c ON p.CategoryId = c.CategoryId
        WHERE LOWER(c.CategoryName) = LOWER(?)
        ORDER BY p.ProductName
    """
    return run_query(q, (category_name,), fetch=True)


# ---------------- SENSITIVE TOOLS ----------------
@tool
def create_customer(name: str, email: str, phone: str, address: str):
    """Thêm khách hàng mới"""
    q = "INSERT INTO customers (Name, Email, Phone, Address) VALUES (?, ?, ?, ?)"
    return run_query(q, (name, email, phone, address))

@tool
def add_product(name: str, category: str, description: str, price: float, quantity: int):
    """Thêm sản phẩm mới vào kho"""
    q = "INSERT INTO products (ProductName, Category, Description, Price, Quantity) VALUES (?, ?, ?, ?, ?)"
    return run_query(q, (name, category, description, price, quantity))

@tool
def update_order_status(order_id: int, status: str):
    """Cập nhật trạng thái đơn hàng"""
    q = "UPDATE orders SET Status=? WHERE OrderId=?"
    return run_query(q, (status, order_id))

safe_tools = [check_categories, list_products_by_category_name]
sensitive_tools = [create_customer, add_product, update_order_status]