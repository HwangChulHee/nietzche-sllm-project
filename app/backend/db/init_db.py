# apps/backend/db/init_db.py
import asyncio
import sys
import os

# 현재 디렉토리를 path에 추가 (임포트 오류 방지)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.base import Base
from models.user import User
from models.chat import ChatRoom, ChatMessage
from db.session import engine

async def init_models():
    async with engine.begin() as conn:
        print("심연의 테이블을 생성 중...")
        # 기존 테이블을 유지하며 생성하려면 create_all만 사용
        await conn.run_sync(Base.metadata.create_all)
        print("테이블 생성 완료!")

if __name__ == "__main__":
    asyncio.run(init_models())