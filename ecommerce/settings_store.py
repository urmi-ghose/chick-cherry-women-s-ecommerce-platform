from .settings import *

ROOT_URLCONF = "ecommerce.urls_store"
SESSION_TIMEOUT_REDIRECT = "/"
TEMPLATES[0]["DIRS"] = [BASE_DIR / "ecommerce" / "templates", BASE_DIR / "templates"]
