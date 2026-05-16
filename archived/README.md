# archived/ — 회고 자산 디렉토리

> 본 작품의 *현재 미션* 외 자산을 시대별로 보존한다.
> **수정 금지** (발표 회고 자료 / 시대 변천 기록). 단, 본 `README.md`와 향후 archive 정리는 예외.

---

## 구조

```
archived/
├── README.md            # 이 파일 — 디렉토리 안내
├── README_legacy.md     # 옛 상담 챗봇 README (Phase 1 이전 버전)
├── CLAUDE_legacy.md     # 옛 작업 지시서 (Track 1/2 분리 컨텍스트)
├── components/          # 옛 챗봇 UI 컴포넌트 (Phase 1, archive됨)
├── prompts/             # 옛 페르소나 프롬프트 (Phase 1, archive됨)
├── endpoints/           # 옛 챗봇 백엔드 엔드포인트 (Phase 2 이전, archive됨)
├── models/              # 옛 챗봇 DB 모델
├── schemas/             # 옛 챗봇 Pydantic 스키마
├── tests/               # 옛 챗봇 백엔드 테스트
├── frontend/            # 옛 챗봇 프론트엔드 페이지/hooks (Phase 3, archive됨)
└── vn_fastapi/          # Phase 2~8 VN-era FastAPI 백엔드 (2026-05-16 archive)
    ├── README.md / CLAUDE.md / BACKEND_STRUCTURE.md  (각 ⚠️ ARCHIVE 표시)
    ├── api/v1/endpoints/   # respond / explain / summarize / save
    ├── services/           # llm_client, sllm_clients (Persona/Explain/Summary ABC + Mock + VLLM)
    ├── models/save.py      # SaveSlot 단일 슬롯
    ├── prompts/            # persona_v1 / explain_v1 / summary_v1
    ├── alembic/            # DB 마이그레이션 001/002
    └── core/config.py      # 환경변수 schema
```

---

## 시대별 분류

본 디렉토리는 두 *시대*의 자산이 섞여 있다.

### 시대 1 — 옛 상담 챗봇 (Phase 1 이전 ~ Phase 2 진입)

니체 페르소나 *상담 챗봇*으로 4/13 중간 발표까지 진행한 트랙. 비주얼 노벨 전환(Phase 1) 시점에 archive됨.

해당 자산:
- `README_legacy.md`, `CLAUDE_legacy.md` — 옛 루트 문서 백업
- `components/`, `prompts/` — 옛 챗봇 UI / 시스템 프롬프트 (Phase 1에서 이동)
- `endpoints/`, `models/`, `schemas/`, `tests/` — 옛 챗봇 백엔드 단편 (Phase 2 진입 시 새 VN 엔드포인트 작성하며 이동)
- `frontend/` — 옛 챗봇 프론트엔드 페이지/hooks (Phase 3 라우팅 재설계 시 이동)

회고 가치: 4/13 중간 발표 자료, 비주얼 노벨 전환 발표(4/29) 비교 대상.

### 시대 2 — VN-era FastAPI 백엔드 (Phase 2~8, 2026-05-16 archive)

비주얼 노벨 작업의 Phase 2에서 신설된 FastAPI 백엔드. 8개 SSE 엔드포인트(respond / explain / summarize / save × GET/POST/DELETE) + `MockClient` / `VLLMClient` 추상화 + SaveSlot DB 모델. Phase 1~8 내내 Mock 모드로 동작.

2026-05-16 통합 작업에서 윈도우 온디바이스 llama.cpp 트랙(`app/ml-backend/`, Node + Express + sqlite-vec)으로 swap되면서 폐기 노선으로 전환.

해당 자산:
- `vn_fastapi/` 전체

회고 가치:
- *원래 계획*(RunPod A100 + vLLM 0.19 + Gemma 4 31B + Alembic + PostgreSQL)이 *어떻게 변형되어 진행되었는지* 기록
- Persona / Explain / Summary 3종 sLLM 추상화 패턴, Mock 데이터 풀, 시스템 프롬프트 v1
- Phase 9 잔여 작업(인터랙션 페르소나·요약 sLLM 실 연결) 진행 시 *옛 엔드포인트 스펙* 참조 가능

---

## 활성 자산은 어디에?

| 종류 | 위치 |
|---|---|
| 활성 백엔드 (해설 RAG) | `../app/ml-backend/` |
| 활성 프론트엔드 (VN UI) | `../app/frontend/` |
| Electron 셸 | `../app/electron/` |
| 통합 가동 / 시연 가이드 | `../app/README.md` |
| 진행 로그 | `../docs/vn/VN_PROGRESS.md` |
| 새 LLM 세션 진입점 | `../docs/vn/VN_AGENTS.md` |

---

## 변경 이력

- 2026-05-01 (Phase 1): `README_legacy.md`, `CLAUDE_legacy.md`, `components/`, `prompts/` 이동
- 2026-05-01 (Phase 2): `endpoints/`, `models/`, `schemas/`, `tests/` 이동 (옛 챗봇 단편)
- 2026-05-01 (Phase 3): `frontend/` 이동
- 2026-05-16 (통합): `vn_fastapi/` 이동 (옛 `app/_archive_backend/` → 현 위치)
