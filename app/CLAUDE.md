# app/ — 비주얼 노벨 코드베이스 라우터

> 옛 Track 1/2 챗봇 컨텍스트는 종료. 현재 단일 미션은
> **"차라투스트라와의 동행" 비주얼 노벨**.

---

## 단일 진입점

새 LLM 세션은 **반드시 `docs/vn/VN_AGENTS.md`부터** 읽을 것 (저장소 루트 기준).
이 파일은 *"먼저 거기로 가라"*만 알려주는 라우터다.

---

## 작업 영역 한눈에

```
app/
├── package.json          # Electron + concurrently + wait-on
├── electron/             # Electron 셸 (main.js / preload.js)
├── ml-backend/           # Node + Express, llama.cpp 기반 해설 RAG
│   └── README.md         # RAG 파이프라인 / CLI
├── frontend/             # Next.js 16 — 비주얼 노벨 UI
│   ├── CLAUDE.md         # 프론트 컴포넌트 + Redux 가이드
│   └── README.md         # 실행/구조
├── _archive_backend/     # 옛 FastAPI 백엔드 (archive됨, 폐기 노선)
├── README.md             # 통합 가동 / ml-backend 엔드포인트
└── PROGRESS.md           # 4/13 중간 발표 회고 자산 (수정 금지)
```

---

## 현재 상태

- **Phase 1~8 완료** (Mock 모드로 Ep 1 + Ep 2 풀 사이클 동작)
- **2026-05-16 통합** — Electron 셸 + ml-backend(:3001) HTTP 래퍼 + frontend(:3000) `npm run dev` 동시 가동. 해설 모드는 llama.cpp 기반 RAG로 실 연결.
- 진행 로그: `docs/vn/VN_PROGRESS.md`
- 인터랙션 페르소나 / 요약 sLLM은 미연결 (Phase 9 잔여)

---

## 절대 건드리지 말 것

- `archived/` 안 파일 (회고 자산)
- `_archive_backend/` 안 파일 (옛 FastAPI 백엔드, 폐기 노선)
- `app/PROGRESS.md` (4/13 중간 발표 회고)
- `ml/` (`.claudeignore`로 차단)

---

## 옛 챗봇 컨텍스트가 필요하면

- 옛 작업 지시서: `archived/CLAUDE_legacy.md`
- 옛 README: `archived/README_legacy.md`
- 옛 진행 회고: `app/PROGRESS.md` (보존)
- 옛 FastAPI 백엔드 코드: `_archive_backend/`
