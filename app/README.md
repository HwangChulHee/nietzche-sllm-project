# app/ — 차라투스트라와의 동행 시연 가이드

> Phase 1~8 완료 시점. Mock 모드로 Ep 1 + Ep 2 풀 사이클 라이브.
> 진행 로그는 `../docs/vn/VN_PROGRESS.md`.

---

## Quick Start (Mock 모드, 시연 셋업)

발표/시연용 가장 단순한 흐름. 약 1분.

```bash
# 1. DB 마이그레이션 (최초 1회 또는 nietzsche.db 없을 때)
cd app/backend
PYTHONPATH=. poetry run alembic upgrade head

# 2. 백엔드 (mock 모드, 포트 8000)
PYTHONPATH=. poetry run uvicorn main:app --port 8000

# 3. 프론트엔드 (별 터미널, 포트 3000)
cd ../frontend
npm install   # 최초 1회
npm run dev
```

브라우저에서 `http://localhost:3000` → [시작] 클릭 → Ep 1 #2부터 진행.

`/health` 응답이 `{"status":"alive","mode":"mock"}`이면 정상.

---

## 시연 흐름 (~6분)

타이틀 → Ep 1 (#2~#7) → 카운드오버 transition → Ep 2 (#1~#4) → 엔딩 → 타이틀.

화면별 시연 포인트와 발표 흐름은 `../demo/scenario_script.md` 참조.

| 단계 | 화면 | 핵심 |
|---|---|---|
| 1 | `/` 타이틀 | 작품 진입 + 인용구 |
| 2 | `/ep1/scene/2` 산 정상 | 정적 나레이션 + [해설] 패널 시연 |
| 3 | `/ep1/scene/3` 숲의 성자 | "나는 인간을 사랑한다" |
| 4 | `/ep1/scene/4` 길로 나섬 | "신이 죽었다는 소식" (분위기 전환점, 800ms 슬로우 페이드) |
| 5 | `/ep1/scene/5` 만남 | 첫 인터랙션, 고정 발화 + 학습자 발화/[침묵] |
| 6 | `/ep1/scene/6` 동행 | 자동 발화 (auto sLLM) |
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
├── frontend/              # Next.js 16 — 비주얼 노벨 UI
│   ├── app/               # 라우팅 (/, /ep1/*, /ep2/*)
│   ├── components/vn/     # VN 컴포넌트 (NarrationScreen, InteractionScreen, ...)
│   ├── data/scenes/       # 정적 텍스트 + 인터랙션 메타
│   ├── data/haeseol/      # 정적 풀이 (해설 패널)
│   ├── lib/api/           # SSE 클라이언트
│   ├── lib/store/         # Redux slices
│   ├── lib/hooks/         # useInteraction, useExplain, useSave, useNavigate
│   └── public/illustrations/  # WebP 일러스트 13장
│
└── backend/               # FastAPI — sLLM 라우팅 + 세이브
    ├── api/v1/endpoints/  # respond / explain / summarize / save
    ├── services/          # llm_client (저수준), sllm_clients (3종 ABC)
    ├── prompts/           # 시스템 프롬프트 3개
    ├── models/save.py     # SaveSlot (단일 슬롯)
    └── alembic/           # DB 마이그레이션
```

---

## 모드 토글

### Mock 모드 (기본, 시연 권장)
미리 짠 응답 풀에서 SSE 스트리밍. 안정적.

```bash
# .env (또는 그대로)
LLM_MODE=mock
```

### vLLM 모드 (Phase 9, 별도 RunPod 환경)
실제 파인튜닝 모델 호출. RunPod + vLLM 0.19 + Gemma 4 31B 셋업 필요.

```bash
# .env
LLM_MODE=vllm
VLLM_BASE_URL=http://<runpod-ip>:8002/v1
VLLM_MODEL=nietzsche-epoch1
VLLM_API_KEY=dummy
```

자세한 RunPod 셋업 절차(vLLM 서빙 / Cloudflare Tunnel / 트러블슈팅)는
`archived/README_legacy.md`에 보존된 옛 가이드를 참조. 비주얼 노벨에서도
같은 vLLM 명령으로 모델 서빙 가능 (LoRA 미사용 → merged 모델 그대로).

---

## 문서 라우팅

| 필요한 정보 | 파일 |
|---|---|
| **새 LLM 세션 진입점** | `../docs/vn/VN_AGENTS.md` |
| 현재 진행 상태 | `../docs/vn/VN_PROGRESS.md` |
| Phase 분할 / 작업 정의 | `../docs/vn/VN_MIGRATION_PLAN.md` |
| UI 정책 / 인터랙션 규약 | `../docs/vn/VN_UI_POLICY.md` |
| 시연 대본 | `../demo/scenario_script.md` |
| 백엔드 엔드포인트 / 환경변수 | `backend/README.md` |
| 프론트 컴포넌트 / Redux | `frontend/README.md`, `frontend/CLAUDE.md` |

---

## 옛 컨텍스트 (회고)

- 4/13 중간 발표 회고: `PROGRESS.md` (보존)
- 옛 상담 챗봇 README: `archived/README_legacy.md`
- 옛 작업 지시서: `archived/CLAUDE_legacy.md`
- 옛 챗봇 UI 컴포넌트 / 프롬프트: `archived/components/`, `archived/prompts/`
