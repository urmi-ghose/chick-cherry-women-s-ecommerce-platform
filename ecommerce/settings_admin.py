from .settings import *

ROOT_URLCONF = "ecommerce.urls_admin"
TEMPLATES[0]["DIRS"] = [BASE_DIR / "templates", BASE_DIR / "ecommerce" / "templates"]
