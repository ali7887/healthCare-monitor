"""Aggregate API router.

Individual route modules are included here and mounted under the API prefix
by the application entrypoint. New routers are registered in this module as
later phases add endpoints.
"""

from fastapi import APIRouter

from app.api.routes import dashboard, health, process, reviews, runs

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(process.router)
api_router.include_router(reviews.router)
api_router.include_router(runs.router)
api_router.include_router(dashboard.router)
