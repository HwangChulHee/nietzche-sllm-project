# apps/backend/db/session.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from core.config import settings

# 이 부분이 'engine'으로 정확히 명명되어야 합니다.
engine = create_async_engine(
    settings.DATABASE_URL, 
    echo=True, # SQL 로그를 보고 싶으면 True
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session