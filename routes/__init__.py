from .auth import router as auth_router
from .frontend import router as frontend_router
from .user_account import router as user_account_router
from .products import router as products_router
from .admin_panel import router as admin_panel_router

# 添加调试输出
print("Routes imported:")
print(f"  auth_router: {auth_router}")
print(f"  frontend_router: {frontend_router}")
print(f"  user_account_router: {user_account_router}")
print(f"  products_router: {products_router}")
print(f"  admin_panel_router: {admin_panel_router}")