# 차라투스트라와의 동행 — 니체 페르소나 비주얼 노벨

> *"그대들에게 인간이란 무엇인가? 극복되어야 할 무엇이다."*
>
> 니체 『차라투스트라는 이렇게 말했다』 서문을, 학습자가 차라투스트라와 함께 따라가는 인터랙티브 철학 소설.

학부 캡스톤 프로젝트. 2026년 5월 최종 발표.

---

## 프로젝트 개요

본 프로젝트는 니체 페르소나를 입힌 sLLM과 학습자가 직접 대화하는 **비주얼 노벨**이다.
단순 챗봇이 아니라, 정해진 서사 위에서 *세 모드*가 교차하며 학습자를 따라온다.

### 세 모드

| 모드 | 설명 |
|---|---|
| **정적 나레이션** | 미리 작성된 본문이 클릭으로 진행 (서문의 정경 묘사) |
| **인터랙션** | 차라투스트라 페르소나 sLLM과 실시간 대화 (동행·시장 등) |
| **해설** | 외부 해설자 sLLM이 현 화면을 평이한 한국어로 풀이 |

### 범위

- **Ep 1 (8화면)**: 서문 1~2절 + 학습자 등장 + 동행 + 시장 도착
- **Ep 2 축약 (4화면)**: 시장 광장 + 위버멘쉬 선포 + 광대 사건 + 재회
- Ep 3 이후는 확장 비전 슬라이드로 대체

---

## 기술 스택

### Frontend
| 항목 | 기술 |
|---|---|
| Framework | Next.js 16 (App Router) |
| Language | TypeScript |
| State | Redux Toolkit |
| Styling | Tailwind CSS, 세피아 토큰 (`vn.css`) |
| Streaming | Fetch API + SSE |

### Backend
| 항목 | 기술 |
|---|---|
| Framework | FastAPI (비동기) |
| Database | SQLite + SQLAlchemy + Alembic (세이브 슬롯) |
| Streaming | SSE (모든 sLLM 응답) |

### LLM / 인프라
| 항목 | 기술 |
|---|---|
| Base Model | Gemma 4 31B (베이스 모델, LoRA 미사용) |
| Inference | vLLM 0.19 (RunPod A100) |
| Embedding | BGE-M3 small + HyDE |
| 패키징 | Cloudflare Quick Tunnel (P0), Tauri (P2) |

### 개발 원칙
- **Mock 우선**: 모든 백엔드 엔드포인트는 `MockClient` / `VLLMClient` 두 구현체. `LLM_MODE=mock`이 기본
- **UI 먼저, 백엔드 나중**: 실제 vLLM 연결은 Phase 9 (마지막)
- **갈아끼울 수 있는 구조**: 프롬프트, 모델, 모드는 모두 환경변수/외부파일

---

## 디렉토리 구조

```text
nietzsche-project/
├── docs/vn/                  # 비주얼 노벨 작업 문서 (진입점)
│   ├── VN_AGENTS.md          # 단일 진입점 — 새 세션은 여기부터 읽을 것
│   ├── VN_MIGRATION_PLAN.md  # Phase 0~9 분할
│   ├── VN_UI_POLICY.md       # UI/인터랙션 정책 단일 진실 소스
│   ├── VN_PROGRESS.md        # 누적 진행 로그
│   ├── HANDOFF_CONTEXT.md    # 컨셉 전체 요약 + 폐기/유지 매트릭스
│   ├── EP1_TEXT_AND_PROMPTS.md
│   ├── EP1_ILLUSTRATIONS.md
│   └── PROJECT_PLAN_v2.md
│
├── app/                      # 살아있는 코드 (재활용)
│   ├── frontend/             # Next.js 16 — 비주얼 노벨 UI
│   │   ├── app/              # 라우팅 (Phase 3에서 신설)
│   │   ├── components/       # 컴포넌트 (옛 챗봇 컴포넌트는 archived/로 이동됨)
│   │   ├── lib/              # hooks, store
│   │   └── data/             # 정적 텍스트, 해설 (Phase 4+)
│   └── backend/              # FastAPI — sLLM 라우팅 + 세이브
│       ├── api/v1/           # 엔드포인트 (Phase 2에서 재작성)
│       ├── services/         # LLMClient 추상화
│       ├── models/           # SQLAlchemy 모델
│       ├── prompts/          # 시스템 프롬프트 (Phase 2에서 신설)
│       └── core/             # 설정
│
├── archived/                 # 회고 자산 (수정 금지)
│   ├── README_legacy.md      # 옛 상담 챗봇 README
│   ├── CLAUDE_legacy.md      # 옛 Track 1/2 분리 컨텍스트
│   ├── components/           # 옛 챗봇 UI 컴포넌트
│   └── prompts/              # 옛 페르소나 프롬프트
│
├── ml/                       # 회고 자산 (.claudeignore 차단)
├── docker-compose.yml
├── README.md
└── CLAUDE.md
```

---

## 작업 진입점

**새 LLM 세션은 반드시 `docs/vn/VN_AGENTS.md`부터 읽을 것.** 30초 안에 컨텍스트를 잡고, 행동 규약(§3)을 내재화한 뒤, 라우팅 표(§5)에 따라 필요한 문서만 lazy load 하도록 설계됨.

옛 상담 챗봇(`app/`, Phase 2 완료) → 비주얼 노벨로 전환 작업이 진행 중이며, 현재 Phase는 `docs/vn/VN_PROGRESS.md`에서 확인.

---

## 개발 환경 실행

```bash
# 백엔드 (Mock 모드 기본)
cd app/backend
make run

# 프론트엔드
cd app/frontend
npm run dev
```

vLLM 실 연결은 `LLM_MODE=vllm` + `VLLM_BASE_URL` 환경변수로 swap. 자세한 운영 절차는 `app/README.md` 참조.

---

## 개발 일정

| 기간 | 주요 작업 |
|---|---|
| ~ 4/13 | 중간 발표 (옛 상담 챗봇 컨셉, 완료) |
| 4/29 | 보충 발표 — 비주얼 노벨 전환 발표 (완료) |
| 4/30 ~ 5월 말 | Phase 1~8 (Mock 모드로 작품 완성) → Phase 9 (vLLM 실 연결) |
| **5월 말** | **최종 발표** |

---

## 라이선스 / 학술 정보

- 본 프로젝트는 졸업 캡스톤 작품이며 학술 목적으로 작성됨.
- 니체 저작 인용은 공개 도메인 번역본을 사용.
