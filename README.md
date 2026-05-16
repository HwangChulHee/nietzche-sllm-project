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
| Framework | Node + Express (`app/ml-backend/server.mjs`, .mjs ESM) |
| Vector store | sqlite-vec (corpus.db) |
| Streaming | SSE (해설 모드 RAG 응답) |

### LLM / 인프라
| 항목 | 기술 |
|---|---|
| Chat (router / rewriter / generator) | Gemma 4 E2B Q4_K_M, llama.cpp 서버 (포트 8000) |
| Embedding | BGE-M3 Q4_K_M, llama.cpp 서버 (포트 8001) |
| 패키징 | Electron 셸 (`app/electron/`, `npm run dev`) |

### 개발 원칙
- **UI 먼저, 백엔드 나중**: Phase 1~8까지 Mock 모드로 풀 사이클 구축, Phase 9에서 실 백엔드 연결
- **갈아끼울 수 있는 구조**: 프롬프트, 모델, 모드는 모두 환경변수/외부파일
- **2026-05-16 통합 이후**: 해설 모드는 `app/ml-backend`(Express + llama.cpp + sqlite-vec)로 실 RAG 연결. 인터랙션 페르소나·요약 sLLM은 Phase 9 잔여

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
├── app/                      # 살아있는 코드
│   ├── package.json          # Electron + concurrently + wait-on, dev 스크립트
│   ├── electron/             # Electron 셸 (main.js, preload.js)
│   ├── frontend/             # Next.js 16 — 비주얼 노벨 UI
│   │   ├── app/              # 라우팅
│   │   ├── components/vn/    # 비주얼 노벨 컴포넌트
│   │   ├── lib/              # hooks, store, api
│   │   └── data/             # 정적 텍스트, 해설
│   ├── ml-backend/           # Node + Express, llama.cpp 기반 해설 RAG
│   │   ├── server.mjs        # SSE HTTP 래퍼 (포트 3001)
│   │   ├── multiturn_rag.mjs # CLI (디버깅)
│   │   ├── prompts/ data/    # 시스템 프롬프트 + 코퍼스
│   │   └── corpus.db         # sqlite-vec 벡터 인덱스
│   └── _archive_backend/     # 옛 FastAPI 백엔드 (archive됨, 폐기 노선)
│
├── archived/                 # 회고 자산 (수정 금지)
│   ├── README_legacy.md      # 옛 상담 챗봇 README
│   ├── CLAUDE_legacy.md      # 옛 Track 1/2 분리 컨텍스트
│   ├── components/           # 옛 챗봇 UI 컴포넌트
│   └── prompts/              # 옛 페르소나 프롬프트
│
├── demo/
│   └── scenario_script.md    # 발표 시연 대본
├── ml/                       # 회고 자산 (.claudeignore 차단)
├── docker-compose.yml
├── README.md
└── CLAUDE.md
```

---

## 작업 진입점

- **Claude Code (CLI 환경, 파일 시스템 접근 가능)**: `docs/vn/VN_AGENTS.md`부터 읽기. 30초 안에 컨텍스트 + 행동 규약(§3) + 라우팅 표(§5).
- **웹 Claude / ChatGPT 등 외부 LLM 세션 (파일 업로드 방식)**: `docs/REPO_OVERVIEW.md` 한 파일이 전체 인덱스. 시나리오별로 추가 파일을 골라 함께 업로드.

진행 상태는 `docs/vn/VN_PROGRESS.md` 참조.

---

## Quick Start (통합 가동, 시연)

전제: 해설 모드 RAG용 llama-server 2개(chat :8000, embed :8001)가 떠 있어야 함.
자세한 llama-server 기동·모델 파일 위치는 `app/README.md` 참조.

```powershell
cd app
npm install   # 최초 1회 (root + ml-backend + frontend)
npm run dev
# → ml-backend(:3001) + frontend(:3000) + Electron 동시 가동
```

Electron 창이 `http://localhost:3000`을 로드 → 타이틀 → [시작] → Ep 1 진행.

`http://localhost:3001/health` 응답에 `indexed_chunks` 숫자가 떠 있으면 정상.

---

## 시연 흐름 (~6분)

타이틀 → Ep 1 (#2~#7) → 카운드오버 → Ep 2 (#1~#4) → 엔딩 → 타이틀 복귀.

화면별 시연 포인트와 발표 흐름은 `demo/scenario_script.md` 참조.

---

## 진행 상태 (2026-05-16)

- **Phase 1~8 완료** — Ep 1 + Ep 2 풀 사이클 라이브
- **2026-05-16 통합** — Electron 셸 + ml-backend(:3001) HTTP 래퍼 + frontend(:3000) 동시 가동. 해설 모드는 llama.cpp 기반 RAG로 실 연결.
- **Phase 9 잔여** — 인터랙션 페르소나 / 요약 sLLM 실 연결

| Phase | 산출물 | 상태 |
|---|---|---|
| 1 | 저장소 정리 + 문서 push | ✅ |
| 2 | 백엔드 sLLM 인터페이스 + Mock 구현 (8개 엔드포인트) | ✅ |
| 3 | 프론트 라우팅 + Redux 골격 + API 클라이언트 | ✅ |
| 4 | 정적 나레이션 컴포넌트 + Ep 1 텍스트 데이터 | ✅ |
| 5 | 책 삽화 16:10 레이아웃 + 일러스트 통합 | ✅ |
| 6 | 인터랙션 컴포넌트 + Mock SSE | ✅ |
| 7 | 해설 패널 + 모달 + 토스트 + 세이브 | ✅ |
| 8 | Ep 2 통합 + transition + 시연 대본 | ✅ |
| 9 | 실 백엔드 연결 + RAG | 🟡 부분 완료 (2026-05-16, 해설 모드만 llama.cpp로 변형 진행) |

---

## 개발 일정

| 기간 | 주요 작업 |
|---|---|
| ~ 4/13 | 중간 발표 (옛 상담 챗봇 컨셉, 완료) |
| 4/29 | 보충 발표 — 비주얼 노벨 전환 발표 (완료) |
| 4/30 ~ 5/01 | Phase 1~8 완료 (Mock 모드) |
| 5/16 | Electron + ml-backend(llama.cpp RAG) 통합, 해설 모드 실 연결 |
| 5/16 ~ 5월 말 | (선택) 인터랙션 페르소나·요약 sLLM 실 연결 + 시연 리허설 |
| **5월 말** | **최종 발표** |

---

## 라이선스 / 학술 정보

- 본 프로젝트는 졸업 캡스톤 작품이며 학술 목적으로 작성됨.
- 니체 저작 인용은 공개 도메인 번역본을 사용.
