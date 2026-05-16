# CLAUDE.md — 저장소 루트 컨텍스트

> 이 저장소의 단일 작업 미션은 **"차라투스트라와의 동행" 비주얼 노벨**이다.
> 옛 Track 1/2 (데이터 파이프라인 + 채팅 UI 분리) 구조는 종료되었음.

---

## 단일 진입점

**새 세션은 반드시 `docs/vn/VN_AGENTS.md`부터 읽을 것.**

- §3 행동 규약을 내재화한 뒤
- §3.1 시작 의식대로 *현재 상태 분석 보고*부터 시작
- 모든 Phase 정의 / UI 정책 / 화면별 텍스트 / 일러스트 가이드는 `docs/vn/`에서 lazy load

이 파일(`CLAUDE.md`)은 *"먼저 거기로 가라"* 만 알려주는 얇은 라우터다.

웹 Claude / ChatGPT 등 *파일 시스템 접근이 없는 외부 LLM 세션*은 `docs/REPO_OVERVIEW.md` 한 파일을 업로드하면 전체 인덱스 + 시나리오별 추가 파일 가이드를 한 번에 얻을 수 있다.

---

## 절대 건드리지 말 것

- **`ml/`** — 데이터 파이프라인 + LoRA 어댑터 회고 자산. `.claudeignore`로 차단됨. 비주얼 노벨에서는 *프롬프팅만* 사용 (LoRA 미사용).
- **`archived/`** — 옛 상담 챗봇 컴포넌트/프롬프트, 옛 README/CLAUDE 백업. 회고용 보존이며 *수정 시 발표 자료 손실*.
- **`app/PROGRESS.md`** — 4/13 중간 발표 회고 자산.

---

## 작업 영역

- **`app/`** (살아있음): Next.js 16 (`app/frontend/`) + Express ml-backend (`app/ml-backend/`, .mjs, llama.cpp 기반 해설 RAG) + Electron 셸 (`app/electron/`). 통합 가동은 `cd app && npm run dev`.
- **`docs/vn/`** (단일 진실 소스): 작업 문서 8개. 진입점은 `VN_AGENTS.md`.
- **`archived/`** — 회고 자산. `archived/vn_fastapi/`는 Phase 2~8 VN-era FastAPI 백엔드(2026-05-16 archive). 구조 안내는 `archived/README.md` 참조.
- **신규 디렉토리는 Phase별 산출물 정의에 따라 생성** (Phase 4의 `data/scenes/`, Phase 5의 `public/illustrations/` 등).

---

## 핵심 작업 원칙

1. **UI 먼저, 백엔드 나중** — Phase 1~8까지 Mock 모드로 풀 사이클, Phase 9에서 실 백엔드 연결
2. **갈아끼울 수 있는 구조** — 프롬프트/모델/모드는 환경변수 + 외부 파일
3. **2026-05-16 이후** — 해설 모드는 `app/ml-backend`(Express + llama.cpp + sqlite-vec)로 실 RAG. 인터랙션 페르소나·요약 sLLM은 Phase 9 잔여
4. **컨셉 축은 합의됨** — 세 모드 / 시간 흐름 / Ep 1+2 범위는 가볍게 뒤집지 말 것
5. **사용자 확인 필요 작업은 사전 확인** — `docs/vn/VN_AGENTS.md` §3.2 참조

---

## 사용자 확인 없이 하지 말 것 (요약)

자세한 목록은 `docs/vn/VN_AGENTS.md` §3.2.

- 기존 파일 5개 이상 삭제 / 디렉토리 구조 대규모 변경
- 의존성 패키지 *제거* (추가는 OK)
- DB 스키마 파괴적 변경
- 환경변수 이름 변경
- README, CLAUDE.md, AGENTS.md, MIGRATION_PLAN 등 문서 수정
- `archived/` 안 파일 수정
- `ml/` 디렉토리 접근

---

## 마지막 업데이트

- 2026-05-16: `app/ml-backend` 통합 (옛 `nietzche-local` PoC 이주) + Electron 셸 + 해설 모드 llama.cpp 기반 RAG 실 연결. 옛 FastAPI 백엔드(`app/backend/`)는 `archived/vn_fastapi/`로 archive.
- 2026-05-01: Phase 1 완료. 옛 Track 1/2 컨텍스트를 비주얼 노벨 단일 미션 라우터로 교체.
- 옛 컨텍스트는 `archived/CLAUDE_legacy.md` 참조.
