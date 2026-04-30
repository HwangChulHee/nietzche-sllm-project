# 🏛️ Nietzsche AI: Persona-based sLLM Counseling Service

> **"심연을 들여다보는 자에게, 심연 또한 그대를 들여다보리라."**
>
> 니체 페르소나를 입힌 sLLM 기반 철학 상담 서비스입니다.

---

## 프로젝트 개요

본 프로젝트는 프리드리히 니체의 철학적 저서를 학습한 **Gemma 4** 모델을 활용하여 사용자에게 니체 특유의 문체와 철학적 통찰이 담긴 상담을 제공합니다.

단순히 텍스트를 생성하는 것을 넘어, **RAG(Retrieval-Augmented Generation)** 기술을 통해 실제 니체 저서의 구절을 근거로 답변하며, 허무주의·힘에의 의지·영원회귀 등 니체 철학 개념을 현대인의 고민에 적용합니다.

### 선정 배경

AI로 인한 기술적 특이점 시대에 노동과 직업의 가치가 흔들리는 현상은, 과거 종교적 권위가 붕괴했을 때와 유사한 허무주의적 위기다. 당대 허무주의에 돌파구를 제시했던 니체의 사상이 현대인에게도 유효하다는 판단 아래 이 프로젝트를 시작했다.

### 핵심 목표

| 목표 | 설명 |
|---|---|
| 니체 페르소나 최적화 | QLoRA SFT를 통해 니체의 사유 방식과 문체를 모델 가중치에 내재화 |
| 지식 신뢰성 확보 | RAG 기술로 실제 니체 저서 구절을 정확히 인용, 환각 억제 |
| 비용 최소화 | 프론티어 모델 API 대신 sLLM 자체 서빙으로 운영 비용 절감 |
| 응답성 확보 | TTFT(Time To First Token) 1.5초 이내 목표 |

---

## 기술 스택

### Frontend

| 항목 | 기술 |
|---|---|
| Framework | Next.js (App Router) |
| Language | TypeScript |
| State Management | Redux Toolkit (RTK Query + createAsyncThunk) |
| Streaming | Fetch API + SSE |
| Styling | Tailwind CSS, shadcn/ui (Radix UI 기반) |

### Backend

| 항목 | 기술 |
|---|---|
| Framework | FastAPI (비동기 처리 중심) |
| Database | PostgreSQL (사용자 세션 및 대화 기록) |
| Vector DB | Qdrant (니체 저서 임베딩 및 RAG 검색) |
| ORM | SQLAlchemy + Alembic |
| Embedding | BGE-M3 |

### AI / ML

| 항목 | 기술 |
|---|---|
| Base Model | Gemma 4 27B |
| Fine-tuning | QLoRA (SFT) |
| Inference Engine | vLLM (PagedAttention) |
| GPU 환경 | RunPod |
| RAG 평가 | RAGAS |

### 인프라

| 항목 | 기술 |
|---|---|
| Cloud | AWS (Amplify, App Runner, RDS) |
| CI/CD | GitHub Actions |
| Container | Docker (Multi-stage 빌드) |

---

## 디렉토리 구조

```text
nietzsche-project/
│
├── apps/                              # 서비스 애플리케이션
│   ├── frontend/                      # Next.js (App Router)
│   │   ├── app/                       # Pages & Layouts
│   │   ├── components/                # UI 컴포넌트
│   │   └── lib/                       # Hooks, Store, Utils
│   └── backend/                       # FastAPI
│       ├── api/v1/                    # API Routers & SSE Endpoints
│       ├── core/                      # 설정, 보안
│       ├── services/                  # LLM 호출, Vector DB 검색
│       ├── models/                    # DB 모델
│       └── schemas/                   # Pydantic 스키마
│
├── ml/                                # ML 파이프라인
│   ├── data/
│   │   ├── raw/
│   │   │   ├── works/                 # 니체 저서 원문 (txt/pdf)
│   │   │   └── biography/             # 전기 자료
│   │   ├── processed/                 # 전처리 완료 텍스트
│   │   └── sft/
│   │       ├── generated/             # Gemma4가 생성한 raw 샘플
│   │       └── final/                 # 학습에 사용할 최종 JSONL
│   │
│   └── sft_pipeline/                  # SFT 데이터 생성 파이프라인
│       ├── prompts/                   # SFT 생성 프롬프트 스펙
│       │   └── nietzsche_sft_prompt_v9_3.md
│       ├── generate_sft.py            # Gemma4로 샘플 생성 메인 스크립트
│       ├── validator.py               # 생성 샘플 정합성 검증
│       ├── formatter.py               # JSONL 포맷 변환 및 정리
│       └── config.py                  # 모델, 배치 크기, 경로 설정
│
├── docker-compose.yml                 # 로컬 개발 환경 (backend + qdrant)
├── CLAUDE.md
└── README.md
```

---

## ML 파이프라인 흐름

```
니체 저서 원문          SFT 데이터 생성              학습
(ml/data/raw/)    →   (sft_pipeline/)         →   (RunPod / QLoRA)
                       │
                       ├── 1. generate_sft.py   Gemma4로 샘플 생성
                       ├── 2. validator.py      정합성 검증 (스키마, 페르소나 규칙)
                       ├── 3. formatter.py      JSONL 변환 및 정리
                       └── 4. ml/data/sft/final/ 에 최종 저장
```

SFT 데이터셋은 `nietzsche_sft_prompt_v9_3.md` 스펙을 기반으로 생성된다.  
질문 유형(`existential_question` 70% / `philosophical_question` 30%), response_pattern 분포, 정합성 규칙은 해당 문서를 참고한다.

---

## 개발 환경 실행

```bash
# 로컬 환경 전체 실행 (backend + qdrant)
docker-compose up -d

# 백엔드 단독 실행
cd apps/backend
make run

# 프론트엔드 단독 실행
cd apps/frontend
npm run dev
```

---

## 개발 일정

| 기간 | 주요 작업 |
|---|---|
| 3/23 ~ 3/29 | SFT 데이터셋 구축 및 Gemma4 QLoRA 파인튜닝 프로토타입 |
| 3/30 ~ 4/4 | Next.js 상담 UI 및 FastAPI 서버 초기 설계 |
| 4/5 ~ 4/12 | 파인튜닝 모델 + UI 연동, 중간 데모 |
| 4/13 ~ 4/26 | RAG 시스템 구축 (Qdrant + BGE-M3) |
| 4/27 ~ 5/10 | vLLM 서빙 최적화, 모델 양자화 |
| 5/11 ~ 5/17 | AWS 배포, RAGAS 평가 |
| 5/18 ~ 5/24 | 최종 평가 및 시스템 안정화 |