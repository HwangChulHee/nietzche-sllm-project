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
├── frontend/          # Next.js 16 — 비주얼 노벨 UI
│   ├── CLAUDE.md      # 프론트 컴포넌트 + Redux 가이드
│   └── README.md      # 실행/구조
├── backend/           # FastAPI — sLLM 라우팅 + 세이브
│   ├── CLAUDE.md      # 레이어 책임 + sLLM 클라이언트 ABC
│   └── README.md      # 엔드포인트 + 환경변수
├── README.md          # 시연 셋업 가이드 (alembic + dev)
└── PROGRESS.md        # 4/13 중간 발표 회고 자산 (수정 금지)
```

---

## 현재 상태

- **Phase 1~8 완료** (Mock 모드로 Ep 1 + Ep 2 풀 사이클 동작)
- 진행 로그: `docs/vn/VN_PROGRESS.md`
- Phase 9 (vLLM 실제 연결 + RAG)는 RunPod 환경 의존, 별도 작업

---

## 절대 건드리지 말 것

- `archived/` 안 파일 (회고 자산)
- `app/PROGRESS.md` (4/13 중간 발표 회고)
- `ml/` (`.claudeignore`로 차단)

---

## 옛 챗봇 컨텍스트가 필요하면

- 옛 작업 지시서: `archived/CLAUDE_legacy.md`
- 옛 README: `archived/README_legacy.md`
- 옛 진행 회고: `app/PROGRESS.md` (보존)
