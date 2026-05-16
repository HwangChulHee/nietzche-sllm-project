from fastapi import APIRouter

from api.v1.endpoints import explain, respond, save, summarize

api_router = APIRouter()

api_router.include_router(respond.router, tags=["persona"])
api_router.include_router(explain.router, tags=["explain"])
api_router.include_router(summarize.router, tags=["summarize"])
api_router.include_router(save.router, tags=["save"])
