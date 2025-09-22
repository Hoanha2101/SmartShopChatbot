# from src.chatTools.tools import *

# # Dùng invoke() để chạy
# result = check_categories.invoke({})
# print(result)
# print("-----")
# result = list_products_by_category.invoke({"category_name": "Điện thoại"})
# print(result)

from src.utils import run_query
q = "SELECT * FROM products"
result = run_query(q, fetch=True)

for r in result:
    print(r)