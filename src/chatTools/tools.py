from langchain.tools import tool
from ..utils import run_query

# ---------------- SAFE TOOLS ----------------
@tool
def get_customer_info(customer_id: int):
    """Tra cứu thông tin khách hàng"""
    q = "SELECT * FROM customers WHERE CustomerId=?"
    return run_query(q, (customer_id,), fetch=True)

@tool
def get_order_info(order_id: int):
    """Tra cứu thông tin đơn hàng (bao gồm chi tiết sản phẩm)"""
    q = """SELECT o.OrderId, o.OrderDate, o.Status, p.ProductName, od.Quantity, od.UnitPrice
           FROM orders o
           JOIN orders_details od ON o.OrderId = od.OrderId
           JOIN products p ON p.ProductId = od.ProductId
           WHERE o.OrderId=?"""
    return run_query(q, (order_id,), fetch=True)

@tool
def list_products(category: str = None):
    """Liệt kê sản phẩm theo danh mục hoặc tất cả"""
    if category:
        q = "SELECT * FROM products WHERE Category=?"
        return run_query(q, (category,), fetch=True)
    else:
        q = "SELECT * FROM products"
        return run_query(q, fetch=True)

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

safe_tools = [get_customer_info, get_order_info, list_products]
sensitive_tools = [create_customer, add_product, update_order_status]