from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.v1.api import api_router

app = FastAPI(title="Nietzsche AI API")

# 프론트엔드(Next.js)와 통신을 위해 CORS 설정은 필수입니다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], # Next.js 기본 포트
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 통합 라우터를 앱에 등록합니다.
app.include_router(api_router, prefix="/api/v1")

@app.get("/health")
def health_check():
    return {"status": "alive", "message": "Nietzsche is watching you."}