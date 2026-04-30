# VN_PROGRESS.md — 비주얼 노벨 작업 진행 로그

> 각 Phase 종료 시 한 줄(또는 작업 단위) 추가. 다음 세션이 인계받을 수 있게.
> Phase 분할은 `VN_MIGRATION_PLAN.md` 참조. UI 정책은 `VN_UI_POLICY.md`.

---

## 현재 상태 요약

**최종 업데이트**: 2026-05-01
**현재 Phase**: 1 완료 / Phase 2 대기
**상태**: 🟢 저장소 정리 완료, 백엔드 Mock 구현 시작 가능
**모드**: — (코드 본격 작업은 Phase 2부터)

---

## 변경 로그 (최신순)

### 2026-05-01 — Phase 1 완료 (저장소 정리 + 문서 push)

#### 작업
- 메인 저장소 `docs/vn/` 8개 문서를 워크트리(`vn_01`)로 복사 → `docs/vn/`에 push
- `archived/` 디렉토리 신설 + 옛 자산 이동:
  - `archived/components/{Header.tsx, Sidebar.tsx, chat/ChatInput.tsx, chat/MessageBubble.tsx}`
  - `archived/prompts/{nietzsche_v1.txt, nietzsche_contemplative.txt, default.txt}`
  - `archived/README_legacy.md`, `archived/CLAUDE_legacy.md` (옛 백업)
- 새 최상위 `README.md` 작성 — 비주얼 노벨 컨셉, 세 모드, `docs/vn/` 라우팅 안내
- 새 최상위 `CLAUDE.md` 작성 — `docs/vn/VN_AGENTS.md` 단일 진입점 라우터로 축소
- 단일 커밋

#### 산출물 (워크트리 기준)
- `docs/vn/*.md` 8개 (VN_AGENTS, VN_MIGRATION_PLAN, VN_UI_POLICY, VN_PROGRESS, HANDOFF_CONTEXT, EP1_TEXT_AND_PROMPTS, EP1_ILLUSTRATIONS, PROJECT_PLAN_v2)
- `archived/` 디렉토리 (회고 자산 보존)
- 새 `README.md`, `CLAUDE.md`

#### 검증
- [x] `git status` clean (단일 커밋)
- [x] `archived/components/` `archived/prompts/`에 옛 자산 이동 확인
- [x] 새 `README.md`가 비주얼 노벨 컨셉 반영
- [x] 새 `CLAUDE.md`가 `docs/vn/VN_AGENTS.md`를 단일 진입점으로 안내
- [x] `app/PROGRESS.md`는 그대로 유지

#### 알려진 한계
- 옛 컴포넌트(`Header.tsx`, `Sidebar.tsx`, `ChatInput.tsx`, `MessageBubble.tsx`)를 archived/로 이동했기 때문에 *현재 시점 프론트엔드 빌드는 깨진 상태*. Phase 3 (라우팅 + Redux 골격) 또는 Phase 4 (정적 나레이션) 진입 시 새 컴포넌트로 대체될 예정 — 이는 의도된 일시 상태.
- 옛 챗봇 페이지(`app/frontend/app/chat/[conversationId]/page.tsx`, `app/page.tsx`)는 *코드 그대로 두었음*. Phase 3에서 라우팅 재설계와 함께 이동/제거.

#### 다음 Phase
- **Phase 2: 백엔드 인터페이스 + Mock 구현**
- 입력: `VN_UI_POLICY.md` §1, §8 / `EP1_TEXT_AND_PROMPTS.md` §0~§4 / `app/backend/services/llm_client.py` (재활용 베이스)
- 핵심 작업: 8개 신규 엔드포인트 (`/api/respond`, `/respond/auto`, `/respond/farewell`, `/explain`, `/summarize`, `/save` GET/POST/DELETE) + Mock 응답 데이터 + `SaveSlot` 모델 + 시스템 프롬프트 3개 + Alembic 마이그레이션
- 사용자 확인 필요: 새 엔드포인트 URL 패턴, DB 스키마 변경 (옛 `Conversation` archived/로)

### 2026-04-30 — Phase 0 완료 (컨텍스트 준비)

#### 작업
- 사용자와 Ⅰ~Ⅶ 영역 (정적 나레이션 / 인터랙션 / 해설 / 인터랙션 정책 / RAG UI / 세이브 / Ep 2) 합의
- UI 우선 + Mock 백엔드 원칙 확정
- 짧은 세션 8개 분할 결정 (Phase 1~8)

#### 산출물
- `VN_AGENTS.md` — 새 LLM 세션 단일 진입점
- `VN_MIGRATION_PLAN.md` — Phase 0~9 분할 마스터
- `VN_UI_POLICY.md` — UI/인터랙션 정책 단일 진실 소스 (Ⅰ~Ⅶ 합의 정리)
- `VN_PROGRESS.md` — 이 문서 (빈 템플릿)

#### 다음 Phase
- **Phase 1: 저장소 정리 + 문서 push**
- 입력: 위 4개 문서 + 기존 `HANDOFF_CONTEXT.md`, `EP1_TEXT_AND_PROMPTS.md`, `EP1_ILLUSTRATIONS.md`, `PROJECT_PLAN_v2.md`
- 핵심 작업:
  1. 4개 신규 문서 + 4개 기획 문서 저장소에 push
  2. 옛날 챗봇 컴포넌트/프롬프트 `archived/`로 이동
  3. 새 `README.md` + 최상위 `CLAUDE.md` 작성 (옛것은 `archived/`에 백업)
- 사용자 확인 필요: README.md / CLAUDE.md 변경분, `archived/` 디렉토리 이름

---

## Phase별 체크리스트

| Phase | 제목 | 상태 |
|---|---|---|
| 0 | 컨텍스트 준비 | ✅ 완료 (2026-04-30) |
| 1 | 저장소 정리 + 문서 push | ✅ 완료 (2026-05-01) |
| 2 | 백엔드 인터페이스 + Mock 구현 | ⏳ 대기 |
| 3 | 프론트 라우팅 + Redux 골격 | ⏳ 대기 |
| 4 | 정적 나레이션 컴포넌트 + 텍스트 | ⏳ 대기 |
| 5 | 책 삽화 레이아웃 + 페이드 + 일러스트 placeholder | ⏳ 대기 |
| 6 | 인터랙션 컴포넌트 | ⏳ 대기 |
| 7 | 해설 패널 + 모달 + 토스트 + 세이브 | ⏳ 대기 |
| 8 | Ep 2 통합 + transition + 시연 대본 | ⏳ 대기 |
| 9 | (별도) vLLM 실제 연결 + RAG + 요약 sLLM | 🔵 Phase 8 후 |

---

## 누적 결정 사항

각 Phase 진행 중 *구현 디테일* 결정이 발생하면 여기 추가. (정책 차원 결정은 `VN_UI_POLICY.md` 직접 수정.)

### Phase 0
- (해당 없음 — 컨텍스트 준비만)

### Phase 1
- `archived/` 디렉토리 이름 채택 (대안: `legacy/`). VN_AGENTS.md §3.5의 *"archived/ 디렉토리 안 파일 수정 X"* 규약과 어휘 일치 위해 `archived/` 선택.
- 옛 README.md → `archived/README_legacy.md`, 옛 CLAUDE.md → `archived/CLAUDE_legacy.md` 백업 (제거 X, 회고 가치).
- 신규 문서 위치: 저장소 루트가 아닌 `docs/vn/`로 통일 — 루트 README/CLAUDE.md만 작품 정보, 작업 컨텍스트는 `docs/vn/`로 분리.
- 옛 컴포넌트 import 깨짐은 Phase 3에서 라우팅 재설계와 함께 정리. Phase 1은 이동만 수행.

### Phase 2
- _작성 예정_

---

## 알려진 이슈 / 한계

각 Phase 결과의 *알려진 한계*를 누적. 발표에서 메타 인사이트로 활용 가능.

- **Phase 1**: 프론트엔드 빌드가 일시적으로 깨진 상태. 옛 챗봇 컴포넌트(`Header`, `Sidebar`, `ChatInput`, `MessageBubble`)를 import하던 페이지(`app/frontend/app/page.tsx`, `app/frontend/app/chat/[conversationId]/page.tsx`)가 그대로 남아있음. Phase 3 (라우팅 재설계) 또는 Phase 4 (정적 나레이션 컴포넌트 신설) 시점에 정리 예정.

---

## 검증 명령어 모음

각 Phase 끝날 때마다 *동작 확인 명령어* 추가. (다음 세션이 같은 명령어로 검증 가능.)

### Phase 1 (저장소 정리)
```bash
# 옛 컴포넌트 archived/로 이동됐는지
ls archived/components/        # Header.tsx, Sidebar.tsx, chat/
ls archived/components/chat/   # ChatInput.tsx, MessageBubble.tsx
ls archived/prompts/           # nietzsche_v1.txt, nietzsche_contemplative.txt, default.txt
ls archived/                   # README_legacy.md, CLAUDE_legacy.md, components/, prompts/

# 신규 문서 push됐는지 (docs/vn/로 통일)
ls docs/vn/                    # 8개 *.md

# 새 README/CLAUDE.md가 비주얼 노벨 컨셉인지
head -10 README.md             # "차라투스트라와의 동행"
head -10 CLAUDE.md             # "단일 미션은 비주얼 노벨"

# git 상태
git log --oneline -1           # Phase 1 커밋
git status --short             # clean
```

### Phase 2 (백엔드 Mock)
```bash
# 8개 엔드포인트 mock 동작
curl -X POST http://localhost:8000/api/respond -d '{"screen_id": "ep1_screen5_meeting", "message": "안녕"}' \
  -H "Content-Type: application/json"  # → SSE 스트림

curl http://localhost:8000/api/save  # → null (빈 슬롯)
```

### (이후 Phase는 작업 끝날 때 추가)

---

## 변경 이력

- 2026-04-30: 초안 작성. Phase 0 완료 라인 추가.
- 2026-05-01: Phase 1 완료 라인 추가 (저장소 정리 + 문서 push).
