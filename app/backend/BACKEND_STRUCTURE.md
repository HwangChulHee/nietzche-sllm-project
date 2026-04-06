# 🏛️ Nietzsche AI Backend Structure Guide

이 문서는 니체 페르소나 sLLM 상담 시스템의 백엔드(FastAPI) 디렉토리 구조와 설계 원칙을 정의합니다. 
전체적인 구조는 **Layered Architecture(계층형 아키텍처)**를 지향합니다.


## 📁 Directory Tree
```text
apps/backend/
├── main.py              # [Entry Point] FastAPI 앱 객체 생성 및 미들웨어(CORS 등) 설정
├── core/                # [Global Config] 전역 설정 및 보안
│   ├── config.py        # 환경 변수 (.env) 및 프로젝트 상수 관리
│   └── security.py      # 인증 및 보안 관련 유틸리티
├── api/                 # [Routing] API 엔드포인트 정의
│   ├── v1/              # API 버전 관리
│   │   ├── api.py       # 모든 라우터를 하나로 통합 (Include Router)
│   │   └── endpoints/   # 도메인별 실제 엔드포인트 로직
│   │       ├── chat.py  # SSE 스트리밍 및 채팅 관련 API
│   │       └── user.py  # 사용자 세션 및 기록 관리 API
├── models/              # [DB Models] SQLAlchemy 테이블 정의
│   └── chat.py          # 대화 기록, 페르소나 설정 테이블 스키마
├── schemas/             # [Data Validation] Pydantic 모델 (Req/Res 규격)
│   ├── chat.py          # 채팅 요청/응답 JSON 포맷 정의
│   └── token.py         # 인증 토큰 규격
├── db/                  # [Database] 연결 및 세션 관리
│   ├── session.py       # PostgreSQL 비동기 엔진 및 세션 설정
│   └── base.py          # 모든 모델을 하나로 묶어 Alembic이 참조하도록 함
└── services/            # [Business Logic] 외부 서비스 연동 및 핵심 엔진
    ├── llm_service.py   # vLLM (RunPod) API 호출 및 프롬프트 엔지니어링
    └── vector_service.py # Qdrant 검색 및 RAG 로직 처리
```


## 🏗️ 아키텍처 설계 및 데이터 흐름 (Architecture & Data Flow)

### 1. 계층별 역할 정의 (Layer Responsibilities)

| 계층 (Layer) | 역할 (Responsibility) | 비유 (Analogy) |
| :--- | :--- | :--- |
| **API (Endpoints)** | 클라이언트의 요청을 받고 응답을 반환하는 인터페이스 | **웨이터**: 손님의 주문을 받고 음식을 서빙 |
| **Schemas (Pydantic)** | 데이터의 형식을 검증하고 변환 (Request/Response DTO) | **주문서**: 요리사에게 전달되는 정확한 규격 |
| **Services** | 비즈니스 로직 처리, 외부 API(vLLM, Qdrant) 연동 | **요리사**: 재료를 손질하고 실제 요리를 수행 |
| **Models (SQLAlchemy)** | 데이터베이스 테이블 구조 정의 | **냉장고 선반**: 재료가 저장되는 물리적 규칙 |
| **DB (Session)** | 데이터베이스 연결 및 세션 관리 | **배달 트럭**: 식재료를 창고에서 주방으로 이동 |

### 2. 데이터 흐름도 (Request Flow)

사용자가 질문을 던졌을 때, 데이터는 아래의 단계를 거쳐 처리됩니다.



1.  **Request**: 프론트엔드(`apps/web`)에서 `/api/v1/chat/`으로 SSE 요청을 보냄.
2.  **Routing**: `main.py` -> `api/v1/api.py` -> `endpoints/chat.py`로 요청이 전달됨.
3.  **Validation**: `schemas/chat.py`의 모델을 통해 입력 데이터 형식을 검증함.
4.  **Logic Execution**: `services/llm_service.py`가 호출됨.
    - `services/vector_service.py`를 통해 Qdrant에서 관련 니체 어록 검색 (RAG).
    - 검색된 컨텍스트와 함께 vLLM(RunPod)에 페르소나 프롬프트 전달.
5.  **Persistence**: 대화 내역은 `models/chat.py` 구조에 맞춰 PostgreSQL에 비동기로 저장됨.
6.  **Streaming Response**: 생성된 답변 조각들을 `StreamingResponse` 형태로 클라이언트에 즉시 반환.



## 📝 설계 원칙 (Design Principles)
- **관심사 분리 (SoC)**: 라우터는 비즈니스 로직을 몰라야 하며, 서비스는 HTTP 요청의 상세 내용을 몰라야 합니다.
- **비동기 우선 (Async First)**: I/O 작업(DB, 외부 API)은 모두 `async/await`를 사용하여 성능을 최적화합니다.
- **타입 안전성**: 모든 데이터 교환은 Pydantic Schemas를 통해 타입이 보장됩니다.