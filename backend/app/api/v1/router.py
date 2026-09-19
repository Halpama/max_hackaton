from fastapi import APIRouter

from app.api.v1 import favorites, geo, places, trip_state, trips
from app.bot.webhook import router as bot_router

api_router = APIRouter()
api_router.include_router(trips.router)
api_router.include_router(trip_state.router)
api_router.include_router(places.router)
api_router.include_router(favorites.router)
api_router.include_router(geo.router)
api_router.include_router(bot_router)
