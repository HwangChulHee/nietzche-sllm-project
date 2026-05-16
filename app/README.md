# app/ — 차라투스트라와의 동행 시연 가이드

> Phase 1~8 완료 + 2026-05-16 통합. Ep 1 + Ep 2 풀 사이클 라이브 (Electron 셸).
> 해설 모드는 `ml-backend` (llama.cpp 기반 멀티턴 RAG) 실 연결.
> 진행 로그는 `../docs/vn/VN_PROGRESS.md`.

---

## 전제 — llama-server 2개 별도 가동

해설 모드 RAG에는 외부 llama.cpp 서버 2개가 떠 있어야 한다.

```powershell
# 터미널 A — Chat (router / rewriter / generator 공용, 포트 8000)
cd C:\Users\hch\llama-b9159-bin-win-cpu-x64
$kwargs = '{"enable_thinking":false}'
.\llama-server.exe -m C:\models\gemma-4-E2B-it-Q4_K_M.gguf --port 8000 -c 8192 -t 6 `
  --jinja --chat-template-kwargs $kwargs `
  --temp 0.7 --top-p 0.95 --top-k 64

# 터미널 B — Embeddings (BGE-M3, 포트 8001)
cd C:\Users\hch\llama-b9159-bin-win-cpu-x64
.\llama-server.exe -m C:\models\bge-m3-q4_k_m.gguf --port 8001 `
  --embeddings --pooling mean -c 2048 -t 4
```

자세한 RAG 파이프라인 / CLI 진입점은 `ml-backend/README.md` 참조.

---

## Quick Start (통합 가동)

```powershell
cd app
npm install   # 최초 1회 (root + ml-backend + frontend)
npm run dev
# → ml-backend(:3001) + frontend(:3000) + Electron 동시 가동
```

Electron 창이 `http://localhost:3000`을 로드 → 타이틀 → [시작] → Ep 1 #2부터 진행.

`http://localhost:3001/health` 응답에 `indexed_chunks` 숫자가 떠 있으면 정상.

### 단독 가동 (디버깅)

```powershell
cd app/ml-backend && node server.mjs       # ml-backend만 (:3001)
cd app/frontend && npm run dev             # frontend만 (:3000)
cd app && npm run electron:dev             # Electron만
```

---

## 시연 흐름 (~6분)

타이틀 → Ep 1 (#2~#7) → 카운드오버 transition → Ep 2 (#1~#4) → 엔딩 → 타이틀.

화면별 시연 포인트와 발표 흐름은 `../demo/scenario_script.md` 참조.

| 단계 | 화면 | 핵심 |
|---|---|---|
| 1 | `/` 타이틀 | 작품 진입 + 인용구 |
| 2 | `/ep1/scene/2` 산 정상 | 정적 나레이션 + [해설] 패널 시연 (실 RAG) |
| 3 | `/ep1/scene/3` 숲의 성자 | "나는 인간을 사랑한다" |
| 4 | `/ep1/scene/4` 길로 나섬 | "신이 죽었다는 소식" (분위기 전환점, 800ms 슬로우 페이드) |
| 5 | `/ep1/scene/5` 만남 | 첫 인터랙션, 고정 발화 + 학습자 발화/[침묵] |
| 6 | `/ep1/scene/6` 동행 | 자동 발화 (auto sLLM, Mock) |
| 7 | `/ep1/scene/7` 시장 원경 | [작별을 고한다 →] 흐름 |
| 8 | `/ep1/ending` 빈 길 | 엔딩 카드 → [Ep 2로 계속] |
| 9 | `/ep2/transition` | 카운드오버 (검은 + italic 텍스트 + 3초 정적) |
| 10 | `/ep2/scene/1`~`/3` | 시장 광장 / 위버멘쉬 / 광대 사건 |
| 11 | `/ep2/scene/4` 학습자 재회 | 두 번째 인터랙션 + 작별 |
| 12 | `/ep2/ending` | 메뉴 → [타이틀로] 또는 [Ep 3 확장 비전] |

---

## 디렉토리 구조

```
app/
├── package.json              # Electron + concurrently + wait-on, dev 스크립트
├── electron/
│   ├── main.js               # BrowserWindow가 http://localhost:3000 로드
│   └── preload.js            # IPC 자리 (현재 비어있음)
│
├── ml-backend/               # Node + Express, llama.cpp 기반 해설 RAG
│   ├── server.mjs            # Express + SSE HTTP 래퍼 (포트 3001)
│   ├── multiturn_rag.mjs     # CLI 진입점 (디버깅용 보존)
│   ├── router.mjs            # intent classification
│   ├── query_rewriter.mjs    # coreference resolution
│   ├── search.mjs            # sqlite-vec wrapper
│   ├── build_index.mjs       # 코퍼스 → corpus.db 인덱싱
│   ├── prompts/              # router / query_rewriter / commentary_system
│   ├── data/                 # interp/orig jsonl 청크 (TSZ 1부 Prologue)
│   ├── corpus.db             # sqlite-vec 벡터 인덱스 (~80MB)
│   └── README.md
│
├── frontend/                 # Next.js 16 — 비주얼 노벨 UI
│   ├── .env.local            # NEXT_PUBLIC_API_BASE=http://localhost:3001
│   ├── app/                  # 라우팅 (/, /ep1/*, /ep2/*)
│   ├── components/vn/        # VN 컴포넌트 (NarrationScreen, InteractionScreen, ...)
│   ├── data/scenes/          # 정적 텍스트 + 인터랙션 메타
│   ├── data/haeseol/         # 정적 풀이 (해설 패널)
│   ├── lib/api/              # SSE 클라이언트
│   ├── lib/store/            # Redux slices
│   ├── lib/hooks/            # useInteraction, useExplain, useSave, useNavigate
│   └── public/illustrations/ # WebP 일러스트 13장
│
└── _archive_backend/         # 옛 FastAPI 백엔드 (archive됨, 폐기 노선)
```

---

## 백엔드 모드

| 모드 | 구현 | 상태 |
|---|---|---|
| **해설 모드 RAG** (실 연결) | `ml-backend/server.mjs` → llama-server(:8000) + BGE-M3(:8001) + sqlite-vec | 라이브 |
| **인터랙션 페르소나** (Mock) | 옛 mock_data.py 풀 → Phase 9에서 swap 예정 | 미연결 (frontend Mock 또는 placeholder) |
| **요약 sLLM** | 미구현 | Phase 9 |

해설 모드만 ml-backend로 실제 RAG가 도는 상태. 인터랙션/요약은 Phase 9에서 별도 구현.

---

## ml-backend HTTP 엔드포인트

`server.mjs`가 노출하는 엔드포인트.

- `POST /api/v1/explain` — SSE. 해설 모드 멀티턴 RAG.
  - 파이프라인: `classify → COMMENTARY면 rewrite → embed → search → LLM stream` / `OOD·AMB`는 short-circuit
  - SSE 이벤트: `metadata` (router/rewrite/rag) / `delta` / `done` / `error`
- `GET /health` — `{ indexed_chunks, ... }` 반환

자세한 RAG 아키텍처·결정 로그·트러블슈팅은 `ml-backend/README.md`.

---

## 문서 라우팅

| 필요한 정보 | 파일 |
|---|---|
| **새 LLM 세션 진입점** | `../docs/vn/VN_AGENTS.md` |
| 현재 진행 상태 | `../docs/vn/VN_PROGRESS.md` |
| Phase 분할 / 작업 정의 | `../docs/vn/VN_MIGRATION_PLAN.md` |
| UI 정책 / 인터랙션 규약 | `../docs/vn/VN_UI_POLICY.md` |
| 시연 대본 | `../demo/scenario_script.md` |
| ml-backend (RAG 파이프라인) | `ml-backend/README.md` |
| 프론트 컴포넌트 / Redux | `frontend/README.md`, `frontend/CLAUDE.md` |

---

## 옛 컨텍스트 (회고)

- 4/13 중간 발표 회고: `PROGRESS.md` (보존, 수정 금지)
- 옛 상담 챗봇 README: `archived/README_legacy.md`
- 옛 작업 지시서: `archived/CLAUDE_legacy.md`
- 옛 챗봇 UI 컴포넌트 / 프롬프트: `archived/components/`, `archived/prompts/`
- 옛 FastAPI 백엔드: `_archive_backend/` (옛 chat 엔드포인트·SaveSlot·Alembic 등)
