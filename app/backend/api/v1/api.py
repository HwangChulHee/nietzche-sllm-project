from fastapi import APIRouter
from api.v1.endpoints import auth, chat, user

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(user.router, prefix="/user", tags=["user"])
