from app.routers.auth import router as auth
from app.routers.users import router as users
from app.routers.restaurants import router as restaurants
from app.routers.tables import router as tables
from app.routers.menu import router as menu
from app.routers.orders import router as orders
from app.routers.stats import router as stats
from app.routers.notifications import router as notifications
from app.routers.reviews import router as reviews
from app.routers.ws import router as ws

__all__ = [
    "auth", "users", "restaurants", "tables",
    "menu", "orders", "stats", "notifications", "reviews", "ws"
]

