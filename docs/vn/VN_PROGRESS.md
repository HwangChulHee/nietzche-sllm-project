# VN_PROGRESS.md — 비주얼 노벨 작업 진행 로그

> 각 Phase 종료 시 한 줄(또는 작업 단위) 추가. 다음 세션이 인계받을 수 있게.
> Phase 분할은 `VN_MIGRATION_PLAN.md` 참조. UI 정책은 `VN_UI_POLICY.md`.

---

## 현재 상태 요약

**최종 업데이트**: 2026-05-01
**현재 Phase**: 8 완료 + UI/UX 폴리시 패스 / Phase 9 대기 (vLLM 실제 연결 + RAG)
**상태**: 🟢 **Ep 1 + Ep 2 풀 사이클 완성**. 타이틀 → Ep 1 (정적 나레이션 #2~#4 + 해설 + 인터랙션 #5~#7 + 저장/불러오기 + 엔딩 #8) → 카운드오버 transition → Ep 2 (정적 나레이션 #1~#3 + 해설 + 인터랙션 #4 + 엔딩) → 타이틀 복귀 모두 Mock 모드로 동작. 시연 대본 작성.
**모드**: 백엔드 `LLM_MODE=mock`

---

## 변경 로그 (최신순)

### 2026-05-01 — Phase 8 폴리시 패스 (UI/UX 정합 + 정책 문서 갱신)

#### 작업
- **응답 지연 인디케이터** (정책 §3.5 구현): `MessageBox`에 3초 booting 타이머 + `vn-msgbox__delay-hint` (italic 14px / `--vn-ink-muted` / 400ms 페이드). 첫 delta 도착 또는 완료 시 즉시 해제. 정상 응답에서는 노출 X (§5.3 *"검색 중..." 신호 X* 원칙 준수).
- **빈 awaiting bubble 레이아웃 점프 방지**: `.vn-msgbox__body--awaiting { min-height: 1.75em }` — 본문 한 줄 자리 미리 확보.
- **#7/Ep 2 #4 작별 단계 안내** (정책 §3.10 구현): `InputArea`에 `hint?: string | null` prop 추가, `inFarewellPhase`일 때 *"마지막 한 마디를 남기거나, 곧장 떠나도 괜찮습니다."* italic 안내. CSS `.vn-input__hint`.
- **침묵 색상 토큰 정합**: `vn-msgbox__body--silent`가 `--vn-ink-muted` (#b8ad9b) 사용하던 것을 정책 §3.3에 맞춰 `--vn-ink-light` (#6b5f4f, 학습자 일반 발화와 동일)로 통일.
- **에러 토스트 / 알림 톤 정리**:
  - `.vn-interaction__error` / `.vn-haeseol__error`에서 백엔드 디버그 details(`— {error.message}`) 제거. 작품 결 *"길이 잠시 끊겼습니다."* 만 노출 (정책 §5.7 명시 추가).
  - 타이틀 [종료] 토스트 *"패키징(Tauri) 단계에서 동작합니다"* → *"데스크톱 앱 버전에서 동작합니다"* (학습자 친화적, 기술 용어 제거).
- **VN_UI_POLICY 정책 문서 갱신**: 초기 합의 수치 vs 구현값 차이를 *의도된 디자인 결정*으로 박아둠 (§2.4 페이드 600ms / §3.3 침묵 색상 명시 / §3.5 인디케이터 구현 / §3.8 자동 발화 타이밍 1600/260/80 / §3.10 작별 안내 / §5.7 에러 details 금지 / §6.5 transition 시퀀스 200+600+3000ms). §11 변경 이력에 한 줄 추가.

#### 산출물 — 변경 파일
| 파일 | 변경 |
|---|---|
| `app/frontend/components/vn/MessageBox.tsx` | useAppSelector + 3초 booting 타이머 + delay hint slot |
| `app/frontend/components/vn/InputArea.tsx` | `hint?` prop 추가, textarea row 위 슬롯 |
| `app/frontend/components/vn/InteractionScreen.tsx` | inFarewellPhase 시 hint 전달, 에러 details 제거 |
| `app/frontend/components/vn/HaeseolPanel.tsx` | 에러 details 제거 |
| `app/frontend/app/page.tsx` | 종료 토스트 문구 학습자 친화적으로 |
| `app/frontend/app/globals.css` | `.vn-msgbox__delay-hint*`, `.vn-msgbox__body--awaiting`, `.vn-input__hint` 추가, `--silent` 색상 토큰 정정 |
| `docs/vn/VN_UI_POLICY.md` | §2.4/§3.3/§3.5/§3.8/§3.10/§5.7/§6.5/§11 갱신 |

#### 검증
- [x] `npx tsc --noEmit` 무에러
- [x] `npm run lint` clean (초기 `react-hooks/set-state-in-effect` 룰 위반 → cleanup 패턴으로 정정)
- [x] dev 서버 라이브 + 타이틀/`/ep1/scene/5`/`/ep1/scene/7` SSR 확인 — `vn-interaction`, `vn-msgbox`, `vn-save`, "작별을 고한다" 마운트 정상
- [ ] **3초 응답 지연 인디케이터 / 작별 안내 / 침묵 색상**의 *시각 확인*은 브라우저 라이브 점검 필요 (SSR로는 booting/farewell 동적 상태 검증 불가)

#### 알려진 한계 / 미해결 (P2 잔존)
- `/load` 라우트 placeholder 잔존 (타이틀 모달 직접 처리, 라우트 미사용)
- 모달 백드롭 fixed (frame 외부 letterbox 덮음) — 정책 §6.4 미세 차이, 의도된 결정일 가능성
- 해설 패널 백드롭 클릭 닫기 미지원 — 모달은 ESC+백드롭, 패널은 ESC만
- 수동 스크롤 일시정지 미구현 (Phase 6부터 P1 잔여)
- 모달 포커스 트랩 (Tab 순환) 미구현
- 토스트 단일 슬롯 (덮어쓰기 방식) — 빠른 연타 시 마지막만 남음

#### 다음 Phase
- **Phase 9: vLLM 실제 연결 + RAG + 요약 sLLM** (별도 Phase, RunPod 환경 의존, 변경 없음)

### 2026-05-01 — Phase 8 완료 (Ep 2 통합 + transition + 시연 대본)

#### 작업
- **Ep 2 데이터 5개 (사용자 작성 본문)**: `data/scenes/ep2_screen1_market_arrival.ts` (5단락) + `ep2_screen2_uebermensch.ts` (8단락) + `ep2_screen3_clown_fall.ts` (18단락 — 원본 16단락에서 *narration 안 발화 인용*은 quote 단락 분리) + `ep2_screen4_reunion.ts` (auto + farewell) + `ep2_ending.ts`
- **Ep 2 강조 마커 적용**: `**위버멘쉬**`, `**마지막 인간**`, `**차라투스트라의 마음이 슬퍼졌다.\n그리고 무거워졌다.**`, `**인간은 짐승과 위버멘쉬 사이에 매인 밧줄이다...**` (밧줄 잠언), `**나는 그대를 내 손으로 묻으리라.**`, `**차라투스트라는 죽은 자를 등에 졌다.\n그리고 길을 떠났다.**`
- **TransitionEp2 컴포넌트**: 검은 배경 (`var(--vn-letterbox)`) + 옅은 세피아 italic 텍스트 *"밤이 깊었다.\n시간은 흘러, 시장의 새벽이 왔다."* + 200ms 정적 → 600ms 페이드인 → 3000ms 정적 → `useNavigate("/ep2/scene/1")`. 백그라운드 요약 sLLM은 Phase 9로 미룸 (시각 흐름만).
- **Ep 2 라우트 마운트**: `/ep2/transition` (TransitionEp2), `/ep2/scene/[id]` (id 1/2/3 NarrationScreen + id 4 InteractionScreen), `/ep2/ending` (EndingCard). PREV/NEXT 매핑 완성.
- **Ep 2 엔딩 액션**: `[Ep 3는 확장 비전 슬라이드로 대체]` → `showToast` *"이 자리에서 외부 발표 슬라이드로 전환됩니다."* (실제 발표 시 외부 슬라이드 수동 전환), `[타이틀로]` → `navigate("/")`
- **`globals.css`**: `.vn-transition-ep2` (검은 배경 + 옅은 세피아 italic 텍스트, 22px line-height 2)
- **시연 대본 (`demo/scenario_script.md`)**: 사전 준비(alembic 등) + 발표 흐름 (~10분) + 화면별 시연 시나리오 + 시연 포인트 매트릭스 + 메타 인사이트 + Q&A 예상 답변 결

#### 산출물 — Ep 2 화면 매트릭스
| 라우트 | 컴포넌트 | screenId | 단락/모드 | 일러스트 (임시) |
|---|---|---|---|---|
| `/ep2/transition` | TransitionEp2 | — | 검은 배경 + italic | (없음) |
| `/ep2/scene/1` | NarrationScreen | `ep2_screen1_market` | 5단락 | screen_07_market_distant |
| `/ep2/scene/2` | NarrationScreen | `ep2_screen2_uebermensch` | 8단락 | screen_05_meeting |
| `/ep2/scene/3` | NarrationScreen | `ep2_screen3_clown_fall` | 18단락 | screen_04_prologue_road |
| `/ep2/scene/4` | InteractionScreen | `ep2_screen4_reunion` | auto + farewell | screen_05_meeting |
| `/ep2/ending` | EndingCard | `ep2_ending` | 2줄 + 메뉴 | screen_08_ending |

#### 검증
- [x] `npx tsc --noEmit` 무에러
- [x] `npm run lint` clean
- [x] 6개 Ep 2 라우트 모두 200
- [x] SSR HTML 검증
  - `/ep2/transition`: `vn-transition-ep2` + "밤이 깊었다" 마운트
  - `/ep2/scene/1`: `vn-narration` + "차라투스트라가 가까운"
  - `/ep2/scene/2`: `vn-narration` + "이번에는 더 깊이"
  - `/ep2/scene/3`: `vn-narration` + "군중에게서 눈을"
  - `/ep2/scene/4`: `vn-interaction` + "작별을 고한다"
  - `/ep2/ending`: `vn-ending` + "EPISODE 2" + "시 장" + "Ep 3는" + "타이틀로"
- [ ] 라이브 흐름 (Ep 1 #8 → transition → Ep 2 #1 자동 진행, 작별 흐름)은 브라우저에서 수동 검증 필요

#### 알려진 한계
- **Ep 2 일러스트 5장 별도 제작 필요**: 현재 Ep 1 일러스트 임시 매핑 (#1→ep1#7, #2→ep1#5, #3→ep1#4, #4→ep1#5, 엔딩→ep1#8). 학습자 시각 일관성은 깨지지만 시연 동작은 보장. 사용자가 ep2_screen_*.webp 5장 추가 후 데이터 파일 5개의 `illustration` 경로만 교체.
- **컨텍스트 보존(Ep 1 → Ep 2 #4 주입)은 Phase 9 vLLM 통합으로 미룸**: TransitionEp2가 백그라운드 요약 sLLM 호출 안 함. Ep 2 #4의 `useInteraction`은 빈 history로 시작. 시각 시퀀스만 동작. 발표 시 *"개인화 RAG와 카운드오버 요약은 Phase 9 RunPod vLLM 환경에서 동작"* 명시 필요.
- **Ep 2 엔딩 [Ep 3는 확장 비전 슬라이드로 대체] 액션은 토스트만**: 실제 발표 시 시연자가 토스트 본 후 외부 슬라이드로 수동 전환. 자동 라우팅 X (외부 슬라이드 시스템과 분리).
- **Ep 2 #4 백엔드 Mock 응답이 Ep 1 #5/#6/#7과 동일 풀**: `mock_data.py`의 `EP2_PERSONA_*` 별도 풀 미구현. Phase 9에서 vLLM 실제 응답으로 자연 차이.
- **#3 광대 사건 18단락은 학습자 시연 시 클릭 부담 큼**: 작품 핵심이라 줄이기 어려움. 발표 흐름에서 ~90초 할애.

#### 다음 Phase
- **Phase 9: vLLM 실제 연결 + RAG + 요약 sLLM** (별도 Phase, RunPod 환경 의존)
- 핵심 작업: `LLM_MODE=vllm` 토글 검증, `VLLMPersonaClient`/`VLLMExplainClient`/`VLLMSummaryClient` 실 호출, BGE-M3 + HyDE RAG 인덱스 구축, Ep 1 → Ep 2 카운드오버 요약 sLLM 결과를 Ep 2 #4 시스템 프롬프트에 주입
- 사용자 확인 필요: RunPod 환경 셋업 + vLLM 0.19 + Gemma 4 31B 가중치 / Alembic 002 적용 / RAG 인덱스 빌드 시점

### 2026-05-01 — Phase 7 완료 (해설 패널 + 모달 + 토스트 + 세이브)

#### 작업
- **정적 풀이 데이터 6개 (사용자 직접 작성, 200~380자/화면)**: `data/haeseol/types.ts` (HaeseolEntry/HaeseolQuote) + Ep 1 #2/#3/#4 + Ep 2 #1/#2/#3 + 레지스트리 (`getHaeseolByScreenId`)
- **Modal 공용 컴포넌트**: 백드롭(`rgba(0,0,0,0.45)`, fixed) + 평이한 시스템 톤. ESC + 백드롭 클릭으로 닫기. primary 액션 잉크 배경.
- **HaeseolPanel**: 우측 슬라이드 50% 패널 (380ms ease, `transform: translateX(100%) → 0`). 정적 풀이(제목 + 한 줄 요약 + 인용/풀이 블록) + 동적 풀이([더 깊이 묻기] 입력창 + 응답 누적 + waiting `…`). ESC + [해설 닫기]로 닫기.
- **useExplain 훅**: `streamExplain` SSE → haeseolSlice 누적. 같은 화면 안에서 history 누적 → 백엔드 `/explain`에 컨텍스트 전달. 화면 전환 시 자동 reset (screenId 의존성).
- **NarrationScreen 해설 통합**: [해설] 클릭 시 `dispatch(openPanel({ screenId }))` → HaeseolPanel 마운트. 패널 open 동안 `advance` / `goBack` / Space/Enter 모두 차단. ▼ 인디케이터도 숨김.
- **useSave 훅**: `getSave` / `postSave` / `deleteSave` 래핑 + saveSlice 동기화. `refresh` / `save` / `clear` API. `saveSlice.SaveSlot`을 `lib/api/types.ts`에서 re-export하여 타입 단일화.
- **InteractionScreen [저장] 버튼**: 우상단 (`top: 18px, right: 24px`, BackButton과 대칭). 동작:
  - 슬롯 없음 → 즉시 `postSave` → 토스트 *"저장되었습니다"*
  - 슬롯 있음 → Modal 확인 (*"기존 저장 데이터를 덮어씁니다. 진행하시겠습니까?"*) → [덮어쓰기] 클릭 시 저장 + 토스트
  - 비활성: streaming 중 / 저장 중 / 메시지 0개 (자동 발화 전)
  - 진입 시 `refresh()` 호출하여 슬롯 미리 fetch → 정확한 분기
- **TitleScreen [불러오기] 모달**: page (`app/page.tsx`)가 `useSave` + 모달 마운트. 슬롯 없음 → *"저장된 게임이 없습니다"* + [돌아가기]. 슬롯 있음 → 미리보기 (Ep/scene_index + timestamp + summary italic) + [취소] / [불러오기]. [불러오기] 클릭 시 `slotToPath(slot)`로 navigate.
- **타이틀 [불러오기]가 모달로 직접 처리** → 기존 `/load` 라우트는 placeholder 그대로 (별도 정리 X — 사용자 확인 없이 라우트 자체 제거는 보류).
- **globals.css**: `.vn-haeseol*` (우측 슬라이드 + 정적/동적 풀이 + 입력창) + `.vn-modal*` (백드롭 + 패널 + primary 버튼) + `.vn-save` (우상단) + `.vn-load-preview*` (불러오기 모달 미리보기)

#### 산출물 — 활성 화면별 매트릭스
| 라우트 | [해설] | [저장] | [불러오기] |
|---|---|---|---|
| `/` (타이틀) | — | — | ✅ 모달 |
| `/ep1/scene/2`/3/4 | ✅ 우측 슬라이드 | — | — |
| `/ep1/scene/5`/6/7 | — | ✅ 우상단 | — |
| `/ep1/ending` | — | — | — |

#### 검증
- [x] `npx tsc --noEmit` 무에러 (saveSlice ↔ api/types SaveSlot 타입 통일 후)
- [x] `npm run lint` clean
- [x] 백엔드(mock) + 프론트 dev 동시 기동
- [x] 4개 라우트 200
- [x] `/api/v1/explain` SSE mock 정상 스트리밍 (metadata + delta)
- [x] SSR HTML: `/ep1/scene/2`에 `vn-haeseol` 패널 + "해설" 버튼 + "서문 1절" 정적 풀이 텍스트 / `/ep1/scene/5`에 `vn-save` 우상단 / `/`에는 `vn-save` 없음
- [ ] **`/save` GET/POST/DELETE 라이브 동작은 PostgreSQL + Alembic 002 적용이 필요** — 사용자 시연 환경에서 `cd app/backend && PYTHONPATH=. poetry run alembic upgrade head` 한 번 실행 권장. 코드는 정상이지만 DB 미적용 환경에서는 [저장] 클릭 시 토스트 *"저장에 실패했습니다"* 노출.

#### 알려진 한계
- **DB 미적용**: Phase 2부터 누적된 한계. 시연 셋업 시 `alembic upgrade head` 필요. 미적용 시 [저장]/[불러오기] 흐름 라이브 검증 불가.
- **/load 라우트 placeholder 잔존**: 타이틀 [불러오기]는 모달로 처리되어 라우트 미사용. 별도 정리는 사용자 확인 후.
- **모달 백드롭 fixed (frame 외부 letterbox까지 덮음)**: VN_UI_POLICY §6.4의 *"frame 내부 absolute"*와 차이 있음. 사용자 시각 일관성을 위해 fixed 채택 — letterbox 영역도 어둠 처리되어 모달 집중도 향상. 정책 미세 변경.
- **수동 스크롤 일시 정지 미구현(해설 패널 / 메시지박스 공통)**: 항상 자동 스크롤. 시연 환경 영향 작음.
- **에러 토스트 톤이 시스템적**: `/respond/auto` 실패 시 Phase 6의 *"길이 잠시 끊겼습니다"*를 그대로 가져왔지만 백엔드 미응답 시 *"저장에 실패했습니다"* 같은 평이한 톤 혼재. Phase 8 시연 폴리시에서 통일.
- **TitleScreen이 hasSavedSlot prop을 받지만 useSave를 직접 호출하진 않음**: 별 차이 없으나 page → TitleScreen으로 prop 흐름이 한 단계 더 거침. 의도된 분리 (TitleScreen은 표현, page는 데이터/모달).

#### 다음 Phase
- **Phase 8: Ep 2 통합 + transition + 시연 시나리오**
- 입력: `VN_UI_POLICY.md` §7 (Ep 2 정책) + 사용자 작성 Ep 2 본문 텍스트 (3화면 + 엔딩)
- 핵심 작업: `data/scenes/ep2_*.ts` 본문 텍스트 (위버멘쉬 선포 / 광대 사건 등) + `TransitionEp2.tsx` (3초 검은 페이드 + transition 텍스트 + 백그라운드 요약 sLLM) + Ep 2 라우트 마운트 + `demo/scenario_script.md` 시연 대본
- 사용자 확인 필요: Ep 2 #1~#3 본문 텍스트 (Ep 2 정적 풀이는 이미 Phase 7에서 데이터로 작성됨)

### 2026-05-01 — Phase 6 완료 (인터랙션 컴포넌트 + Mock SSE 통합)

#### 작업
- **신규 컴포넌트 4종**: `useInteraction.ts` 훅, `InteractionScreen.tsx`, `MessageBox.tsx`, `InputArea.tsx`
- **`useInteraction` 훅**: 진입 시 `resetForScreen` + 800ms(페이드 600 + 정적 200) 대기 후 자동 발화 시퀀스 트리거. `firstUtterance.kind === "fixed"`(#5)는 32ms/char 시뮬 스트리밍, `"auto"`(#6/#7)는 `streamRespondAuto` SSE 호출. `send` / `silent` / `farewell` 액션 노출. `streamingState !== "idle"` 가드로 동시 호출 방지. unmount 시 `AbortController.abort()`.
- **`MessageBox`**: 누적 스크롤 (메시지 변경 시 `scrollTop = scrollHeight` 자동 — 수동 스크롤 일시정지는 P1로 미룸). 화자별 시각 분리 (좌-차라투스트라 진한 잉크 / 우-그대 옅은 잉크). 침묵 메시지는 `…` italic + ink-muted. assistant 응답 booting 단계는 빈 streaming 메시지를 italic `…`로 렌더 (delta 들어오면 즉시 본문 대체).
- **`InputArea`**: textarea 자동 높이 (1줄 → 최대 120px). 500자 카운터 (`217 / 500`), 450자 초과 진해짐, 500자 초과 [발화하기] 비활성. [발화하기] (빈 입력 비활성), [침묵] (항상 활성), 화면 전환 버튼 (canTransition만 활성). 스트리밍 중 textarea/모든 버튼 비활성, placeholder `…`. Enter 전송 / Shift+Enter 줄바꿈.
- **`InteractionScreen`**: Frame + IllustrationLayer(`mode="interaction"`, 상 50%) + 하단 50% 박스(MessageBox + InputArea). farewell 흐름 자체 관리 — `[작별을 고한다 →]` 클릭 시 `ix.farewell()` 호출 → 라벨이 `[엔딩으로 →]`로 전환 → 학습자 추가 send/silent 가능 → 다시 클릭 시 `onComplete`.
- **데이터 메타**: `data/scenes/ep1_screen5_meeting.ts` (firstUtterance="그대.\n어디서 왔는가." 고정), `ep1_screen6_walking.ts` (auto), `ep1_screen7_market_distant.ts` (auto + farewell=true). `types.ts`에 `InteractionScene` 타입 추가.
- **`ep1/scene/[id]/page.tsx`**: id ∈ {5,6,7}일 때 `InteractionScreen` 마운트. NEXT 라우팅 #5→#6→#7→#8.
- **`globals.css` 인터랙션 스타일**: `.vn-interaction` + `.vn-msgbox*` (화자별 색·정렬·italic 침묵·waiting 인디케이터) + `.vn-input*` (textarea·카운터·버튼·전환 버튼 활성/비활성).

#### 산출물 — 인터랙션 화면 매트릭스
| 라우트 | screenId | 첫 발화 | 전환 라벨 | 작별 흐름 |
|---|---|---|---|---|
| `/ep1/scene/5` | `ep1_screen5_meeting` | 고정 `"그대.\n어디서 왔는가."` (시뮬 스트림) | `[그와 함께 걷는다 →]` | — |
| `/ep1/scene/6` | `ep1_screen6_walking` | `/respond/auto` SSE | `[시장이 가까워진다 →]` | — |
| `/ep1/scene/7` | `ep1_screen7_market_distant` | `/respond/auto` SSE | `[작별을 고한다 →]` → `[엔딩으로 →]` | `/respond/farewell` SSE |

#### 검증
- [x] `npx tsc --noEmit` 무에러
- [x] `npm run lint` clean
- [x] 백엔드(`LLM_MODE=mock`) + 프론트 dev 동시 기동 성공
- [x] 인터랙션 라우트 3개(`/ep1/scene/{5,6,7}`) 모두 200
- [x] 백엔드 mock SSE 3종 라이브 검증: `POST /api/v1/respond` (메시지+history 반영), `POST /api/v1/respond/auto`, `POST /api/v1/respond/farewell` 모두 metadata + delta 정상 스트리밍
- [x] SSR HTML 검증: `/ep1/scene/5`에 `vn-interaction` + `vn-illust--interaction` + `vn-msgbox` + `vn-input` + "발화하기" + "침묵" + "그와 함께 걷는다" + `screen_05`. `/ep1/scene/{6,7}`에 각각의 전환 라벨 + 일러스트 매핑 확인
- [ ] *대화 흐름* (자동 발화 → 학습자 입력 → 응답 스트리밍 → 화면 전환): SSR로 검증 불가 — 브라우저 라이브 점검 필요

#### 알려진 한계
- **#7 작별 후 학습자 마지막 응답 1회 폴리시 미반영**: VN_UI_POLICY §3.10은 *"학습자 마지막 응답 1회 가능 (선택)"*을 명시하지만, 현재 구현은 farewell 발화 후 `[엔딩으로 →]` 라벨로 전환되어 학습자가 자유롭게 send/silent 추가 후 클릭하는 흐름. 대체로 충족하지만 *어느 시점에 학습자가 멈춰야 하는지* UI 가이드는 없음.
- **수동 스크롤 일시정지 미구현**: 자동 스크롤만 동작. 학습자가 위로 스크롤해 이전 메시지 보는 중에도 새 응답 도착 시 자동으로 하단 이동. 시연에서 발생 가능성 낮으니 P1.
- **3초 응답 지연 인디케이터 미구현**: §3.5의 *"응답 지연 > 3초: italic 작은 …"*은 *전용 booting 인디케이터*이지만 현재는 빈 streaming 메시지를 항상 `…`로 표시 (스트리밍 시작 후 첫 delta까지). 시각적으로 동일 효과지만 booting을 명시적으로 표시하지 않음.
- **자동 발화 페이드 시퀀스 단순화**: 화자명 페이드인 280~320ms는 단순 100ms 정적으로 대체. 차라투스트라 메시지 박스가 booting 단계부터 마운트되어 화자명만 먼저 등장하는 효과는 자연스럽지 않음.
- **#7 일러스트 alt가 학습자 등장 표현 부족**: "언덕 위 두 인물과 멀리 보이는 시장의 황혼" — Ep 1 #5/#6/#7은 학습자(두 번째 인물)가 함께 있다는 게 핵심. 일러스트 자체는 OK.

#### 다음 Phase
- **Phase 7: 해설 패널 + 모달 + 토스트 + 세이브 시스템**
- 입력: `VN_UI_POLICY.md` §4 (해설 모드) + §6 (세이브) + 기존 `EXPLAIN_RESPONSES` mock 데이터
- 핵심 작업: `HaeseolPanel.tsx` (우측 슬라이드 50%) + `Modal.tsx` (공용) + `data/haeseol/` (정적 풀이 손글씨) + `useExplain.ts` + `useSave.ts` 훅 + `/save` 엔드포인트 통합 + `[해설]` 버튼 진짜 동작
- 사용자 확인 필요: 정적 풀이 손글씨 텍스트 (황철희 직접 작성 — 미리 받아야 진행)

### 2026-05-01 — Phase 5 완료 (책 삽화 레이아웃 + 일러스트 통합)

#### 작업
- **일러스트 자산**: 사용자가 제작한 Ep 1 8장 PNG (2624×1632, 합 ~100MB)를 1600×1000 WebP 품질 88로 변환 (Pillow). 합 ~5.8MB (94% 절감). `app/frontend/public/illustrations/screen_01_title.webp` ~ `screen_08_ending.webp`. 파일명 오타 `submit → summit` 1건 수정. 원본 PNG는 `.gitignore`로 추적 제외 (로컬 보관).
- **신규 컴포넌트**: `Frame.tsx` (16:10 캔버스 wrapper), `IllustrationLayer.tsx` (Next/Image + mode별 비율 — narration 70% / interaction 50% / fullscreen 100%)
- **NarrationScreen 리팩터**: 일러스트 placeholder div → IllustrationLayer(mode=narration). 텍스트박스를 *반투명 오버레이*에서 *분할 단색 박스* (하단 30%, border-top 1px ink-muted)로 전환. props에 `illustration`/`alt` 추가
- **EndingCard 리팩터**: IllustrationLayer(mode=fullscreen) + 가독성용 옅은 세피아 vignette `__veil` (radial gradient) + 텍스트 그림자. 5초→텍스트→3초→메뉴 시퀀스 유지
- **TitleScreen 리팩터**: IllustrationLayer(mode=fullscreen) + `__veil` + 메뉴/인용구 오버레이. 메뉴 버튼은 반투명 세피아 배경(가독성)
- **데이터 파일 4개 갱신**: `NarrationScene` / `EndingCardData`에 `illustration`, `alt` 필드 추가
- **VnFrame 갱신**: viewport에 검은 letterbox(`--vn-letterbox: #0d0a07`) + 안쪽 16:10 박스 (`width: min(100vw, 100vh*16/10)`, `height: min(100vh, 100vw*10/16)` 조합 — viewport 비율에 따라 letterbox 자동). `/ep1/scene/5` 진입 시 `vn-page--slow` 클래스 부착 (#4 → #5 800ms wiring)
- **globals.css 정리**: 옛 챗봇 토큰(`--bg-primary` 등) 제거 — VN 토큰만 단일 진실 소스. `vn-illust*` 클래스 + `vn-book` + `__veil` 추가. 컴포넌트별 `__illust` / `__illust-placeholder` 옛 클래스 제거. 페이지 컴포넌트는 `body` 배경이 letterbox이므로 `--vn-bg`(세피아)는 vn-page만 보유.
- **페이지 갱신**: `app/page.tsx` (TitleScreen에 illustration/alt 전달), `app/ep1/scene/[id]/page.tsx` (NarrationScreen에 scene.illustration/alt 전달), `app/ep1/ending/page.tsx` (EndingCard에 illustration/alt 전달)

#### 산출물 — 화면별 일러스트 통합
| 라우트 | 일러스트 | 모드 | 텍스트 영역 |
|---|---|---|---|
| `/` | `screen_01_title.webp` | fullscreen + veil | 가운데 메뉴 + 인용구 (그림자 부착) |
| `/ep1/scene/2` | `screen_02_prologue_summit.webp` | narration (상 70%) | 하단 30% 단색 박스 |
| `/ep1/scene/3` | `screen_03_prologue_forest.webp` | narration | 하단 30% 단색 박스 |
| `/ep1/scene/4` | `screen_04_prologue_road.webp` | narration | 하단 30% 단색 박스 |
| `/ep1/scene/5` | (placeholder) | — | `vn-page--slow` 800ms 진입 페이드 적용 |
| `/ep1/ending` | `screen_08_ending.webp` | fullscreen + veil | 가운데 텍스트 + 하단 메뉴 (그림자 부착) |

#### 검증
- [x] `npx tsc --noEmit` 무에러
- [x] `npm run lint` clean
- [x] dev 서버 라이브 (`Ready in 257ms`), 10개 라우트 모두 200
- [x] 일러스트 정적 자산 5개(타이틀·#2·#3·#4·#8) `/illustrations/*.webp` 모두 200
- [x] SSR HTML 검증
  - `/`: `vn-book` + `vn-illust--fullscreen` + `vn-title__veil` + `screen_01_title` + 타이틀/메뉴 텍스트
  - `/ep1/scene/2`: `vn-book` + `vn-illust--narration` + `vn-narration__textbox` + `screen_02` + 첫 단락
  - `/ep1/scene/5`: **`vn-page--slow`** 클래스 SSR 적용 (slowFade wiring 검증)
  - `/ep1/ending`: `vn-book` + `vn-illust--fullscreen` + `vn-ending__veil` + `screen_08` + 텍스트/메뉴

#### 알려진 한계
- **#5~#7 placeholder**: 일러스트는 있으나 컴포넌트 미마운트 (Phase 6 인터랙션). `screen_05~07.webp`는 자산만 사용 가능, 화면 마운트 X.
- **#8 → #4 진입 비대칭**: `vn-page--slow`는 #5 진입 시만. #4 *이탈* 페이드는 표준 600ms (route 변경 시 이전 페이지 unmount 즉시 발생, CSS-only로는 fade-out 불가능). 분위기 전환점 효과는 `#5 진입 800ms`로 단방향 흡수.
- **세이브 / 우상단 메뉴 영역**: Frame 안 자유 absolute 슬롯이지만 컴포넌트 미부착 (Phase 7).
- **Ep 2 일러스트 4장**: 본 작업 범위 밖. Phase 8에서 별도 자산 수령 필요.
- **타이틀 진입 페이드 1200ms**: EP1_TEXT_AND_PROMPTS §화면 #1의 *"검은 화면 → 일러스트 페이드인 1200ms"*는 표준 600ms로 통일. 시연 폴리시에서 필요 시 `vn-page--title` 변형 추가.
- **첫 페이드 시 텍스트가 일러스트와 동기 페이드인**: 타이틀/엔딩에서 일러스트보다 텍스트가 먼저 잠깐 떠 보일 가능성 (next/image 로드 시간차). priority=true로 완화했지만 완전 해결은 EndingCard처럼 `illust_only` 단계 추가가 필요.

#### 다음 Phase
- **Phase 6: 인터랙션 컴포넌트 (#5~#7, Ep 2 #4)**
- 입력: `VN_UI_POLICY.md` §3 (인터랙션 정책 전부) + `EP1_TEXT_AND_PROMPTS.md` §5 #5~#7 (sLLM 호출 컨텍스트)
- 핵심 작업: `InteractionScreen.tsx` + `MessageBox.tsx` + `InputArea.tsx` + `useInteraction.ts` 훅 + `dialogueSlice` 본격 활용 + `/api/v1/respond/auto` `/respond` `/respond/farewell` 백엔드 SSE 연결
- 사용자 확인 필요: 화면 전환 버튼 위치 (우측 또는 하단), [세이브] 버튼 위치 (우상단)

### 2026-05-01 — Phase 4 완료 (정적 나레이션 컴포넌트 + 텍스트 데이터)

#### 작업
- 정적 텍스트 데이터: `data/scenes/` 신설 + `types.ts` (Paragraph/NarrationScene/EndingCardData) + `ep1_screen2_summit.ts` (5단락) + `ep1_screen3_forest.ts` (6단락) + `ep1_screen4_road.ts` (3단락, slowFade=true) + `ep1_screen8_ending.ts` (엔딩 카드)
- VN 컴포넌트 4종 신설: `components/vn/NarrationScreen.tsx`, `EndingCard.tsx`, `TitleScreen.tsx`, `ToastHost.tsx`
- `NarrationScreen`: 단락 phase 머신 (in→idle→out→in / 마지막은 exit→onComplete), 290ms 페이드, 클릭/Space/Enter 진행, ▼ 인디케이터(idle 시만, 1.4s blink), 좌하단 [해설] placeholder 버튼 (클릭 시 toast "Phase 7에서 구현")
- `EndingCard`: 일러스트 5초 정적 → 텍스트 페이드인 600ms → 3초 후 메뉴 페이드인 600ms 시퀀스. props로 episode/title/body/actions 받음
- `TitleScreen`: 타이틀 + 부제 + 메뉴 3개([시작]/[불러오기 disabled when !hasSavedSlot]/[종료]) + 인용구
- `ToastHost`: `uiSlice.toast`를 셀렉트해서 화면 하단 부유 박스로 렌더, `visibleUntil` 기반 자동 숨김
- 라우트 마운트: `app/page.tsx` → TitleScreen (SSE 검증 위젯 제거, getSave로 hasSavedSlot 결정), `app/ep1/scene/[id]/page.tsx` → id ∈ {2,3,4}일 때 NarrationScreen, 그 외(5,6,7) placeholder 유지, `app/ep1/ending/page.tsx` → EndingCard ([Ep 2로 계속]/[타이틀로])
- `app/layout.tsx`: VnFrame과 형제로 ToastHost 마운트
- `globals.css`: VN 토큰 활용한 narration/ending/title/toast 스타일 + `vn-indicator-blink` 1.4s 키프레임 + `vn-toast-in` 200ms 애니메이션

#### 산출물 — 화면 구성
| 라우트 | 컴포넌트 | 상태 |
|---|---|---|
| `/` | `TitleScreen` | 라이브 (메뉴 3개 + 인용구, hasSavedSlot 동적) |
| `/ep1/scene/2` | `NarrationScreen(ep1Screen2Summit)` | 라이브 (5단락) |
| `/ep1/scene/3` | `NarrationScreen(ep1Screen3Forest)` | 라이브 (6단락) |
| `/ep1/scene/4` | `NarrationScreen(ep1Screen4Road)` | 라이브 (3단락, slowFade 데이터만) |
| `/ep1/scene/{5,6,7}` | placeholder | Phase 6 |
| `/ep1/ending` | `EndingCard(ep1Screen8Ending)` | 라이브 (5초 정적 → 텍스트 → 3초 후 메뉴) |
| `/ep2/*` | placeholder | Phase 8 |

#### 검증
- [x] `npx tsc --noEmit` 무에러
- [x] `npm run lint` 무에러 (ESLint clean)
- [x] dev 서버 라이브 (`Ready in 229ms`) → 10개 라우트 모두 200 응답
- [x] SSR HTML 검증: `/`에 "차라투스트라"·"시 작"·"극복되어야" 포함, `/ep1/scene/{2,3,4}`에 `vn-narration` 클래스 + 첫 단락 본문 + [해설] 버튼, `/ep1/ending`에 `vn-ending` + "시간은 흐른다" + 메뉴 라벨
- [x] 단락 페이즈 머신 (in→idle→out→in) 290ms 페이드 클래스 토글
- [x] [해설] 버튼 클릭 시 `showToast` dispatch → ToastHost 1.8초 자동 숨김
- [x] EndingCard 5초+600ms+3초+600ms 단계 timer 체인
- [ ] 키보드 Space/Enter 진행은 SSR로 직접 검증 불가 (브라우저에서 수동 확인 필요)

#### 알려진 한계
- **#4 → #5 800ms 슬로우 페이드**: 데이터(slowFade=true)는 있으나 페이지 컴포넌트가 자체 클래스(`vn-page--slow`) 적용은 Phase 5 책 삽화 레이아웃 작업과 함께. 현재는 NarrationScreen 자체 290ms 단락 페이드만 동작.
- **일러스트 placeholder**: `__illust-placeholder` div는 옅은 베이지/검정. Phase 5에서 16:10 frame + 실제 일러스트로 교체.
- **[해설] 패널**: 토스트만. 동적 풀이 패널은 Phase 7.
- **불러오기 라우트(`/load`)**: 여전히 placeholder. VN_UI_POLICY는 모달이지만 라우트로 분리되어 있음 — Phase 7에서 모달로 통합할지 결정.
- **타이틀 [종료] 버튼**: 데스크톱 패키징(Tauri, P2) 단계 전까지는 토스트로 안내.

#### 다음 Phase
- **Phase 5: 책 삽화 레이아웃 + 페이드 시스템 + 일러스트 placeholder 통합**
- 입력: `VN_UI_POLICY.md` §5 (디자인 토큰 + 16:10 frame) + `EP1_ILLUSTRATIONS.md` 전체
- 핵심 작업: VnFrame 16:10 비율 적용, `IllustrationLayer` 컴포넌트, 일러스트 SVG placeholder 8장, NarrationScreen/EndingCard/TitleScreen을 Frame + IllustrationLayer 위에 리팩터링, `#4 → #5` 800ms 슬로우 페이드 wiring
- 사용자 확인 필요: 일러스트 placeholder 형식 (단색 SVG vs 외곽선 스케치 vs AI 임시 일러스트)

### 2026-05-01 — Phase 3 완료 (프론트 라우팅 + Redux 골격)

#### 작업
- 옛 챗봇 자산 `archived/frontend/`로 이동: `app/chat/[conversationId]/page.tsx`, `lib/hooks/useStreamingChat.ts`, `lib/store/chatSlice.ts`
- 라우팅 신설: `app/page.tsx` (타이틀 + SSE 검증 위젯), `app/load/page.tsx`, `app/ep1/scene/[id]/page.tsx`, `app/ep1/ending/page.tsx`, `app/ep2/transition/page.tsx`, `app/ep2/scene/[id]/page.tsx`, `app/ep2/ending/page.tsx`
- 공통 컨테이너: `app/vn-frame.tsx` (`key={pathname}` remount → CSS 페이드 재실행), `app/providers.tsx` (Redux Provider), `app/layout.tsx` 갱신
- Redux slices 5개: `episodeSlice` (episode/sceneIndex/mode), `dialogueSlice` (인터랙션 메시지 + streaming 상태머신 + userTurns), `haeseolSlice` (해설 패널 + 동적 풀이 누적), `saveSlice` (단일 슬롯 캐시), `uiSlice` (fade/toast/modal)
- `lib/store/index.ts`로 store 구성, `lib/hooks/useAppDispatch.ts` 추가
- API 클라이언트 (`lib/api/`): `sse.ts` 공통 SSE 파서 + `persona.ts` (respond/respond/auto/respond/farewell) + `explain.ts` + `summarize.ts` + `save.ts` (GET/POST/DELETE) + `types.ts`
- 페이드 시스템: `globals.css`의 `.vn-page` + `vn-fade-in` 600ms 키프레임 + `--vn-page--slow` 800ms 옵션 (#4→#5 분위기 전환점)
- VN 디자인 토큰 추가 (`--vn-bg`, `--vn-ink`, `--vn-font-serif` 등) — Phase 5에서 본격 활용

#### 산출물 — 라우팅 매트릭스
| 라우트 | 컴포넌트 | 상태 |
|---|---|---|
| `/` | `app/page.tsx` | placeholder + SSE 검증 위젯 (Phase 4에서 TitleScreen으로 대체) |
| `/load` | `app/load/page.tsx` | placeholder (Phase 7에서 슬롯 모달) |
| `/ep1/scene/[id]` | `app/ep1/scene/[id]/page.tsx` | #2~#7 동적 (Phase 4/6에서 NarrationScreen/InteractionScreen) |
| `/ep1/ending` | `app/ep1/ending/page.tsx` | placeholder (Phase 4에서 EndingCard) |
| `/ep2/transition` | `app/ep2/transition/page.tsx` | placeholder (Phase 8에서 TransitionEp2) |
| `/ep2/scene/[id]` | `app/ep2/scene/[id]/page.tsx` | placeholder (Phase 8) |
| `/ep2/ending` | `app/ep2/ending/page.tsx` | placeholder (Phase 8) |

#### 검증
- [x] `npx tsc --noEmit` 무에러 (전체 타입 통과, archived/ 이동 후 잔존 import 깨짐 없음)
- [x] `npm run lint` 무에러 (ESLint clean)
- [x] 백엔드 mock + 프론트 dev 동시 기동 성공 (`/health` `{"mode":"mock"}` 응답)
- [x] 8개 라우트 모두 200 응답 (`/`, `/load`, `/ep1/scene/{2,5}`, `/ep1/ending`, `/ep2/transition`, `/ep2/scene/1`, `/ep2/ending`)
- [x] `POST /api/v1/respond/auto` SSE 라이브 스트리밍 검증 (metadata + delta 정상 수신)
- [x] `POST /api/v1/explain` SSE 라이브 스트리밍 검증
- [ ] `/save` 계열은 여전히 DB 미적용으로 500 (Phase 2부터 누적된 한계 — alembic 미실행)

#### 알려진 한계
- **DB 미적용 누적**: Phase 2부터 Alembic 002 미실행 상태. `/save` GET은 500. Phase 7 (세이브 시스템 구현) 또는 시연 셋업 시점에 `alembic upgrade head` 필요.
- **타이틀/엔딩/화면 컴포넌트 X**: 모든 라우트가 placeholder. Phase 4부터 본격 컴포넌트 마운트.
- **VnFrame 16:10 비율 미적용**: 현재 풀-vh. Phase 5 책 삽화 레이아웃에서 16:10 frame으로 교체.
- **`#4 → #5` 800ms 슬로우 페이드**: CSS 클래스(`.vn-page--slow`)는 정의됐으나 페이지 컴포넌트가 자체 클래스 적용은 Phase 5 범위.

#### 다음 Phase
- **Phase 4: 정적 나레이션 컴포넌트 + 텍스트 데이터**
- 입력: `VN_UI_POLICY.md` §2 (정적 나레이션 정책 전부) + `EP1_TEXT_AND_PROMPTS.md` §5 #1~#4, #8 (정적 텍스트 본문)
- 핵심 작업: `NarrationScreen`/`EndingCard`/`TitleScreen` 컴포넌트 + `data/scenes/ep1_screen{2,3,4,8}.ts` + 키보드 단축키 (Space/Enter)
- 사용자 확인 필요: 데이터 파일 경로 (`data/scenes/` vs `lib/scenes/` 등)

### 2026-05-01 — Phase 2 완료 (백엔드 인터페이스 + Mock 구현)

#### 작업
- 옛 챗봇 백엔드 자산 `archived/`로 이동 (`endpoints/chat.py`, `models/chat.py`, `schemas/chat.py`, `tests/integration/test_chat_api.py`, `tests/unit/test_models.py`, `tests/unit/test_schemas.py`)
- 환경변수 재설계 (`SYSTEM_PROMPT_FILE` → `PERSONA_PROMPT_FILE` + `EXPLAIN_PROMPT_FILE` + `SUMMARY_PROMPT_FILE`, `LLM_BASE_URL`/`LLM_MODEL`/`LLM_API_KEY` → `VLLM_*` prefix)
- `services/llm_client.py` 정리 — 저수준 LLM 스트리밍 추상화로 축소 (load_system_prompt 제거)
- `services/sllm_clients.py` 신설 — Persona / Explain / Summary 3종 ABC + Mock + VLLM 구현체 + 싱글턴 팩토리
- `services/mock_data.py` 신설 — 화면별 Mock 응답 풀 (`PERSONA_AUTO_FIRST`, `PERSONA_REPLIES`, `PERSONA_SILENT_REPLIES`, `PERSONA_FAREWELL`, `EXPLAIN_RESPONSES`, `SUMMARY_TEMPLATE`)
- 시스템 프롬프트 3개 작성 (`prompts/persona_v1.txt`, `explain_v1.txt`, `summary_v1.txt`) — `EP1_TEXT_AND_PROMPTS.md` §1~§3, `VN_UI_POLICY.md` §4 출처
- `models/save.py` 신설 — `SaveSlot` 단일 슬롯 모델 (id=1 고정)
- `schemas/vn.py` 신설 — 8개 엔드포인트 입출력 Pydantic 스키마
- 신규 엔드포인트 4파일: `endpoints/respond.py` (3개 엔드포인트), `explain.py`, `summarize.py`, `save.py` (GET/POST/DELETE)
- `api/v1/api.py` 라우터 정리 — 옛 chat 라우터 제거, 4개 새 라우터 등록
- Alembic 002 마이그레이션 — `conversations`/`messages` drop + `save_slots` create
- `db/init_db.py`, `db/reset_db.py`, `alembic/env.py`, `tests/conftest.py`의 `models.chat` 참조를 `models.save`로 갱신

#### 산출물 — 8개 엔드포인트
| 메서드 | 경로 | sLLM | 검증 |
|---|---|---|---|
| POST | `/api/v1/respond` | Persona | ✅ SSE 스트리밍 (학습자 발화 / `silent=true` 모두 동작) |
| POST | `/api/v1/respond/auto` | Persona | ✅ SSE 스트리밍 (화면 진입 자동 발화) |
| POST | `/api/v1/respond/farewell` | Persona | ✅ SSE 스트리밍 (작별 발화) |
| POST | `/api/v1/explain` | Explain | ✅ SSE 스트리밍 (해설 동적 풀이) |
| POST | `/api/v1/summarize` | Summary | ✅ SSE 스트리밍 (1인칭 회상) |
| GET | `/api/v1/save` | — | 🟡 import 검증만 (DB 미실행) |
| POST | `/api/v1/save` | Summary (내부) | 🟡 import 검증만 |
| DELETE | `/api/v1/save` | — | 🟡 import 검증만 |

#### 검증
- [x] 모든 변경 파일 `python -m py_compile` 통과
- [x] FastAPI 앱 라우트 등록 확인 (`/api/v1/respond`, `/respond/auto`, `/respond/farewell`, `/explain`, `/summarize`, `/save` × 3)
- [x] uvicorn 띄워 5개 SSE 엔드포인트 curl 검증 (metadata + delta + done 정상)
- [x] Mock 클라이언트 직접 호출로 페르소나/해설/요약 응답 풀 출력 확인
- [x] `/health` 엔드포인트 `{"status":"alive","mode":"mock"}` 응답
- [ ] DB 마이그레이션 적용 (PostgreSQL 미기동 — Phase 3 시작 시 `alembic upgrade head`로 적용)

#### 알려진 한계
- **DB 미적용**: 환경에 PostgreSQL이 안 떠있어 Alembic 002를 실제 적용 못 함. 마이그레이션 코드는 작성됨. Phase 3 시작 시 또는 시연 환경 셋업 시 `alembic upgrade head`로 적용 필요.
- **VLLM 구현체 미검증**: `LLM_MODE=vllm` 토글은 Phase 9 범위. VLLMPersonaClient/VLLMExplainClient/VLLMSummaryClient는 구조만 있고 실 호출 검증 X.
- **`app/backend/README.md`, `BACKEND_STRUCTURE.md`**: 옛 챗봇 컨셉 잔재 — Phase 2 범위 외, 별도 문서 정리 시점에 처리.
- **Phase 1의 프론트 빌드 깨짐 미해소**: Phase 3에서 라우팅 재설계와 함께.

#### 다음 Phase
- **Phase 3: 프론트 라우팅 + Redux 골격**
- 입력: `VN_UI_POLICY.md` §1 화면 매트릭스 + §8 컴포넌트 매트릭스 / 기존 `lib/store/chatSlice.ts`, `lib/hooks/useStreamingChat.ts` 패턴 / Phase 2 백엔드 엔드포인트 8개
- 핵심 작업: Next.js 라우팅 (`/`, `/load`, `/ep1/scene/[id]`, `/ep1/ending`, `/ep2/transition`, `/ep2/scene/[id]`, `/ep2/ending`) + Redux slices (episode/dialogue/haeseol/save/ui) + API 클라이언트 (`lib/api/`) + 페이드 transition
- 사용자 확인 필요: framer-motion 도입 여부, 라우팅 구조 디테일

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
| 2 | 백엔드 인터페이스 + Mock 구현 | ✅ 완료 (2026-05-01) |
| 3 | 프론트 라우팅 + Redux 골격 | ✅ 완료 (2026-05-01) |
| 4 | 정적 나레이션 컴포넌트 + 텍스트 | ✅ 완료 (2026-05-01) |
| 5 | 책 삽화 레이아웃 + 페이드 + 일러스트 통합 | ✅ 완료 (2026-05-01) |
| 6 | 인터랙션 컴포넌트 | ✅ 완료 (2026-05-01) |
| 7 | 해설 패널 + 모달 + 토스트 + 세이브 | ✅ 완료 (2026-05-01) |
| 8 | Ep 2 통합 + transition + 시연 대본 | ✅ 완료 (2026-05-01) |
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
- 엔드포인트 prefix를 `/api/v1/` 유지 (플랜의 `/api/...`는 shorthand로 해석). 기존 `main.py`의 `/api/v1` prefix 컨벤션 보존.
- DB 스키마: `conversations`/`messages` drop + `save_slots` 신설 (단일 슬롯, id=1 고정). 옛 챗봇 모델 파일 6개는 `archived/`로 이동.
- 환경변수 prefix `VLLM_*` 통일 (`VLLM_BASE_URL`, `VLLM_MODEL`, `VLLM_API_KEY`). 시스템 프롬프트는 sLLM별 분리 (`PERSONA_PROMPT_FILE`, `EXPLAIN_PROMPT_FILE`, `SUMMARY_PROMPT_FILE`).
- sLLM 클라이언트는 ABC + Mock + VLLM 3구조. Mock은 `services/mock_data.py`의 화면별 풀에서 yield, VLLM은 `LLMClient`(저수준) + 시스템 프롬프트 조립으로 호출. 싱글턴 팩토리 (`get_persona_client`, `get_explain_client`, `get_summary_client`).
- `POST /save`는 내부에서 `SummaryClient`를 동기 consume하여 summary 생성 후 upsert. 별도 summary 인자 받지 않음.
- DB는 PostgreSQL 유지 (기존 셋업 그대로). VN_AGENTS.md §1의 SQLite 표기는 README 정정 시점에 처리.
- 신규 단위/통합 테스트 미작성 (VN_AGENTS.md §3.5 *"단위 테스트 작성 시간 낭비"*). curl + smoke import로 종료 조건 충족.

### Phase 8
- **Ep 2 #3 광대 사건은 18단락 분리 (원본 16 → 18)**: *narration 안 발화 인용*이 같은 단락에 섞이면 시각 구분 약함. 죽어가는 자 발화 두 군데(#10, #12)를 도입 문장(narration)과 발화(quote)로 분리. 단락 수 늘었지만 학습자가 천천히 읽기 좋고 시각 일관 유지.
- **TransitionEp2는 시각만 (요약 sLLM 호출 X)**: VN_UI_POLICY §6.5의 *"백그라운드 요약 sLLM"*은 Phase 9 vLLM 환경에서 통합. Phase 8 mock 단계에선 *시각 시퀀스의 작품 결*만 검증. saveSlice/별도 슬라이스에 요약 결과 저장 패턴은 Phase 9 작업.
- **Ep 2 일러스트 임시 ep1 매핑**: 일러스트 자산이 없어 *시연 자체*가 막히는 것보다는 *비슷한 그림 재사용*이 진행 우선. 시연 시 *임시 일러스트* 명시.
- **Ep 2 엔딩 [Ep 3 확장 비전] 액션은 토스트**: 외부 슬라이드 자동 전환은 비주얼 노벨 앱 책임 밖. 발표자가 토스트 보고 수동으로 슬라이드 전환.
- **Ep 2 강조 마커 적용 위치**: 사상 등장(#2 위버멘쉬·마지막 인간), 차라 마음 변화(#2 마지막 단락), 밧줄 잠언 첫 두 줄(#3 #2단락 일부), 차라 약속(#3 #15 "묻으리라"), 마지막 행동(#3 #18 "등에 졌다"). 학습자 시선이 *작품 흐름의 결정적 지점*에 머물도록 의도 배치.
- **시연 대본은 markdown으로 단일 파일**: 별도 슬라이드 deck X. 발표 시 `demo/scenario_script.md` 보면서 라이브 진행.

### Phase 7
- **정적 풀이 6개 모두 작성 (Ep 1 + Ep 2)**: 사용자가 한 번에 6개 다 줘서 Ep 2도 미리 작성. Phase 8 진입 시 데이터 준비 완료 — 본문 텍스트만 받으면 Ep 2 마운트 가능.
- **HaeseolPanel은 NarrationScreen 자식으로 마운트** (페이지 직접 X). NarrationScreen이 `enableHaeseol` true일 때만 마운트하므로 #5~#7 인터랙션에서는 자동 unmount. open 상태는 haeseolSlice가 단일 진실 소스.
- **useExplain은 HaeseolPanel에서 호출, NarrationScreen은 dispatch만**: 두 군데에서 useExplain 호출 시 reset effect가 두 번 발생하므로 단일 호출. NarrationScreen은 `openPanel` dispatch + `haeseol.open` selector만 사용.
- **모달 백드롭 fixed 채택** (정책 §6.4 "frame 내부 absolute" 변경): viewport 풀스크린이 모달 집중도 더 높음. letterbox 영역까지 어두워지는 것이 시연에 더 몰입감.
- **세이브 사용자 흐름은 useSave 훅 한 곳에**: API + saveSlice 동기화 통합. InteractionScreen / TitlePage 둘 다 동일 훅 사용. 슬롯 정보가 한 군데에서 관리되어 양쪽 분기가 일관.
- **slot 상태가 마운트 시 자동 fetch**: TitlePage / InteractionScreen 둘 다 `refresh()` 호출. saveSlice 미초기화 상태에서 [저장] 클릭 시 *"덮어쓰기 모달 누락"* 회피.
- **slotToPath / sceneLabel 헬퍼는 page 안 함수 (별도 모듈 X)**: 단일 사용처라 모듈화 불필요.
- **/load 라우트는 그대로 placeholder 유지**: 타이틀 모달로 흡수했지만 라우트 자체 삭제는 사용자 확인이 없어 보류. 향후 정리 가능.

### Phase 6
- **#5 첫 발화는 고정 텍스트 + 시뮬 스트리밍** 채택 (EP1_TEXT_AND_PROMPTS §화면 #5 *"안정성"* 명시). 32ms/char로 sLLM 응답과 동일한 체감. sLLM 호출 X.
- **자동 발화 진입 지연 800ms** (페이드 600ms + 정적 200ms, VN_UI_POLICY §3.8). 화자명 페이드인 280~320ms 단계는 단순화로 100ms 정적 대체.
- **자동 스크롤 항상 동작** (수동 스크롤 일시정지 P1). 단순 `scrollTop = scrollHeight`. 시연 환경에서 학습자가 직접 스크롤할 가능성 낮음.
- **booting 인디케이터 = 빈 streaming 메시지를 italic `…`로 렌더** (스트리밍 시작 후 첫 delta까지). 별도 *3초 지연 검출* 로직 안 만듦 — 시각 결과 동일.
- **farewell 흐름 단순화**: `[작별을 고한다 →]` 클릭 → `ix.farewell()` → 라벨이 `[엔딩으로 →]`로 전환 → 학습자 자유 추가 send/silent → 다시 클릭 시 `onComplete`. *학습자 마지막 응답 1회 (선택)* §3.10 폴리시를 *"farewell 후 자유롭게 인터랙션 + 명시적 클릭으로 종료"*로 해석.
- **InteractionScreen이 farewell 상태 자체 관리**, 페이지는 `onComplete`만 받음. 페이지가 farewell 흐름을 알 필요 없음.
- **dialogueSlice의 `addUserMessage` content가 침묵 시 "…"** + isSilent=true. 백엔드 history 전송 시 ASCII "..."로 매핑 (mock의 silent 처리와 호환).

### Phase 5
- **사용자가 일러스트 8장을 직접 제작**해서 일러스트 placeholder 단계 스킵. PNG 원본 2624×1632(합 ~100MB)를 Pillow로 1600×1000 WebP @ q88 변환 → 합 ~5.8MB (94% 절감). PNG는 `.gitignore`로 추적 제외, WebP만 커밋.
- **vn.css 별도 파일 신설 안 함**. 플랜 §3 디자인 토큰은 이미 `globals.css`에 있음(Phase 3에서 추가) — 단일 진실 소스 유지가 낫다고 판단.
- **TextLayer 컴포넌트 신설 안 함**. 플랜 §작업 영역에 명시됐으나 NarrationScreen 외 사용처 없어 `vn-narration__textbox` 인라인으로 충분. (인터랙션은 다른 컴포넌트, 엔딩/타이틀은 자체 처리.)
- **Frame은 thin wrapper**. children + `vn-book` 클래스만. 우상단/좌하단 슬롯 props는 도입 안 함 — Phase 7([세이브]/[해설] 본격 부착)에서 필요해질 때 추가. *과한 추상화 회피*.
- **16:10 letterbox 구현**: `width: min(100vw, calc(100vh*16/10))` + `height: min(100vh, calc(100vw*10/16))` 조합. CSS `aspect-ratio`는 width/height 둘 다 정해지면 무시되는 함정 회피.
- **검은 배경 letterbox 색**: `--vn-letterbox: #0d0a07` (순수 검정 #000보다 살짝 따뜻). body 배경이 letterbox이고 vn-page만 세피아.
- **풀스크린 일러스트(#1, #8) 가독성**: `__veil` (radial gradient 가운데 투명 → 가장자리 옅은 세피아) + 텍스트 그림자. 일러스트 자체가 세피아 톤이라 잉크색 텍스트 잘 읽힘.
- **#4 → #5 800ms는 #5 *진입* 페이드만 적용**. CSS-only 라우팅이라 #4 *이탈* 페이드는 통제 불가 — 단방향으로 흡수. VnFrame이 pathname을 보고 `vn-page--slow` 분기.

### Phase 4
- **데이터 파일 경로 `data/scenes/` 채택** (대안: `lib/scenes/`). 근거: Next.js 관행상 `lib/`은 코드 유틸, `data/`는 정적 데이터. Phase 5 일러스트 메타·Phase 8 Ep 2 텍스트도 같은 자리에 모으기 위함.
- **단락 데이터 형태**: `Paragraph = { text, kind?: 'narration' | 'quote' }`. 발화 인용은 `kind: "quote"`로 표시 → 컴포넌트가 italic + indent 자동 적용 (VN_UI_POLICY §2.5 *"단락 안에서 살짝 들여쓰기 + italic"*). 단락 *내부* 일부만 인용인 경우는 발생 안 함 (#2~#4 모두 단락 단위로 인용 분리됨).
- **#4 slowFade는 데이터(slowFade=true)만 두고 동작 wiring은 Phase 5로 미룸**. 이유: 페이지 진입 페이드는 VnFrame의 `vn-page` 클래스 책임이고, 16:10 프레임 도입과 함께 `vn-page--slow` 적용 지점을 한 번에 정리하는 게 깔끔.
- **단락 전환 290ms 단순 out→in 시퀀스 채택** (cross-fade 대신). VN_UI_POLICY §2.4 "out-in 동시"는 cross-fade 의미지만 phase 머신이 단순한 out→in이 코드 단순성 유리, 280~300ms 범위 내에서 체감 차이 미미.
- **ToastHost는 layout 직속**: VnFrame 자식이 아니라 형제로 마운트. 이유: 라우트 변경 시 `key={pathname}` remount되는 VnFrame 자식 영역을 벗어나야 토스트가 사라지지 않음.
- **[해설] / [종료] 버튼은 `showToast` dispatch + ToastHost 렌더 패턴**. Phase 7 (해설 패널) / P2 (Tauri 패키징)까지 placeholder.

### Phase 3
- **페이드 transition 라이브러리 도입 X — CSS-only로 결정**. `key={pathname}` remount + `@keyframes vn-fade-in` 600ms로 충분. framer-motion 등 추가 의존성 없음. 근거: Phase 5 책 삽화 레이아웃에서도 동일 메커니즘으로 확장 가능, 의존성 최소화 (VN_AGENTS.md §3.5 "추가 라이브러리 도입 신중").
- **라우팅 구조**: `/ep1/scene/[id]` 동적 (`/ep1/2`가 아닌 `/ep1/scene/2`). 화면 인덱스가 URL의 어디에 박혀있는지 명시적이라 디버깅/시연이 편함.
- **Redux store는 URL의 미러**: 페이지 컴포넌트가 `useEffect`로 mount 시 `enterScene` dispatch. URL이 single source of truth, slice는 컴포넌트 간 공유 캐시.
- **`useAppDispatch` 헬퍼 신설**: 타입 추론용 (`AppDispatch`). useSelector 헬퍼는 Phase 4에서 첫 사용처 발생 시 추가.
- **타이틀 페이지(`app/page.tsx`)에 SSE 검증 위젯 임시 부착**: `<details>` 안 `/respond/auto` 호출 버튼. Phase 4 TitleScreen 도입 시 제거.
- **SSE 응답 스키마**: 백엔드의 `metadata`/`delta`/`done`/`error` 4종 이벤트를 `streamSSE`가 공통 파싱. 콜백 객체 패턴 (`onMetadata`/`onDelta`/`onDone`/`onError`).
- **API base URL**: `process.env.NEXT_PUBLIC_API_BASE` (기본 `http://localhost:8000`). 환경별 swap 가능.

---

## 알려진 이슈 / 한계

각 Phase 결과의 *알려진 한계*를 누적. 발표에서 메타 인사이트로 활용 가능.

- **Phase 1**: 프론트엔드 빌드가 일시적으로 깨진 상태. 옛 챗봇 컴포넌트(`Header`, `Sidebar`, `ChatInput`, `MessageBubble`)를 import하던 페이지(`app/frontend/app/page.tsx`, `app/frontend/app/chat/[conversationId]/page.tsx`)가 그대로 남아있음. Phase 3 (라우팅 재설계) 또는 Phase 4 (정적 나레이션 컴포넌트 신설) 시점에 정리 예정.
- **Phase 2**: PostgreSQL 미기동으로 Alembic 002 미적용. `/save` 계열 3개 엔드포인트는 import 검증만 통과. Phase 3 시작 시 또는 시연 셋업 시 `alembic upgrade head` 필요.
- **Phase 2**: VLLM 구현체(`VLLMPersonaClient` 등)는 Phase 9 범위로 미검증. Mock 모드 토글만 동작.
- **Phase 2**: `app/backend/README.md`, `app/backend/BACKEND_STRUCTURE.md`, `app/backend/CLAUDE.md`에 옛 환경변수 이름과 챗봇 컨셉 잔재. 별도 문서 정리 PR 필요.
- **Phase 3**: `app/frontend/CLAUDE.md`, `app/frontend/AGENTS.md`도 옛 챗봇 컨셉 잔재 (채팅 컴포넌트 폴더 구조 등). 별도 문서 정리 시 처리.
- **Phase 3**: 모든 라우트가 placeholder. Phase 4부터 컴포넌트 본격 마운트.
- **Phase 3**: `archived/frontend/` 트리는 옛 챗봇 자산 보존용. 이전 Phase 1 `archived/components/`, `archived/prompts/`와 별도 트리.
- **Phase 3**: `LoadPage`가 라우트(`/load`)로 분리됐으나 VN_UI_POLICY는 *불러오기 모달*로 정의. Phase 7에서 모달로 교체할지, 라우트로 유지할지 결정 필요.

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
# 서버 실행 (mock 모드)
cd app/backend && PYTHONPATH=. poetry run uvicorn main:app --port 8000

# health
curl http://localhost:8000/health  # {"status":"alive","mode":"mock"}

# 5개 SSE 엔드포인트 (모두 SSE 스트림 반환)
curl -X POST http://localhost:8000/api/v1/respond \
  -H "Content-Type: application/json" \
  -d '{"screen_id":"ep1_screen5_meeting","message":"안녕","silent":false,"history":[]}'

curl -X POST http://localhost:8000/api/v1/respond/auto \
  -H "Content-Type: application/json" \
  -d '{"screen_id":"ep1_screen6_walking","history":[]}'

curl -X POST http://localhost:8000/api/v1/respond/farewell \
  -H "Content-Type: application/json" \
  -d '{"screen_id":"ep1_screen7_market","history":[]}'

curl -X POST http://localhost:8000/api/v1/explain \
  -H "Content-Type: application/json" \
  -d '{"screen_id":"ep1_screen2_summit","query":"왜 산이었는가","history":[]}'

curl -X POST http://localhost:8000/api/v1/summarize \
  -H "Content-Type: application/json" \
  -d '{"episode":"ep1","scene_index":7,"history":[]}'

# /save 계열 (DB 필요 — alembic upgrade head 후)
curl http://localhost:8000/api/v1/save  # null (빈 슬롯) 또는 SaveSlot JSON
```

### Phase 3 (프론트 라우팅 + Redux 골격)
```bash
# 프론트 dev (포트 3000)
cd app/frontend && npm run dev

# 백엔드 mock 동시 기동 (포트 8000)
cd app/backend && PYTHONPATH=. poetry run uvicorn main:app --port 8000

# 정적 검증
cd app/frontend && npx tsc --noEmit   # TS 무에러
cd app/frontend && npm run lint        # ESLint clean

# 라우트 모두 200
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:3000/
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:3000/load
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:3000/ep1/scene/2
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:3000/ep1/scene/5
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:3000/ep1/ending
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:3000/ep2/transition
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:3000/ep2/scene/1
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:3000/ep2/ending

# SSE 라이브 (브라우저에서 / 페이지 → backend SSE 검증 위젯 → /api/v1/respond/auto 호출)
```

### (이후 Phase는 작업 끝날 때 추가)

---

## 변경 이력

- 2026-04-30: 초안 작성. Phase 0 완료 라인 추가.
- 2026-05-01: Phase 1 완료 라인 추가 (저장소 정리 + 문서 push).
- 2026-05-01: Phase 2 완료 라인 추가 (백엔드 인터페이스 + Mock 구현, 8개 엔드포인트).
- 2026-05-01: Phase 3 완료 라인 추가 (프론트 라우팅 8개 + Redux 5 slices + API 클라이언트 + CSS 페이드).
- 2026-05-01: Phase 4 완료 라인 추가 (정적 나레이션 컴포넌트 3종 + ToastHost + 텍스트 데이터 4파일 + 키보드 단축키).
- 2026-05-01: Phase 5 완료 라인 추가 (16:10 책 삽화 레이아웃 + 사용자 제작 일러스트 8장 WebP 통합 + #4→#5 800ms slowFade wiring).
- 2026-05-01: Phase 6 완료 라인 추가 (인터랙션 컴포넌트 4종 + useInteraction 훅 + Mock SSE 통합 + farewell 흐름).
- 2026-05-01: Phase 7 완료 라인 추가 (해설 패널 우측 슬라이드 + Modal 공용 + useSave/useExplain 훅 + 정적 풀이 6개 + [저장]/[불러오기] 모달 흐름).
- 2026-05-01: Phase 8 완료 라인 추가 (Ep 2 데이터 5개 + TransitionEp2 + Ep 2 라우트 마운트 + 시연 대본).
