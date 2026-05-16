# Frontend — 차라투스트라와의 동행

니체 페르소나 비주얼 노벨의 웹 프론트엔드. Next.js 16 App Router + Redux Toolkit + SSE 스트리밍 + 책 삽화 레이아웃.

**관련 문서**:
- 컴포넌트 / 훅 / 슬라이스 가이드 → [`CLAUDE.md`](./CLAUDE.md)
- Next.js 16 breaking changes 경고 → [`AGENTS.md`](./AGENTS.md)
- 시연 셋업 → [`../README.md`](../README.md)
- 작품 정책 / Phase 정의 → [`../../docs/vn/VN_AGENTS.md`](../../docs/vn/VN_AGENTS.md)

---

## 실행

```bash
# 1. 의존성 설치 (최초 1회)
npm install

# 2. 백엔드 base URL 환경변수 (기본값, 통합 가동 시 자동)
echo "NEXT_PUBLIC_API_BASE=http://localhost:3001" > .env.local

# 3. 개발 서버
npm run dev
# → http://localhost:3000
```

해설 모드 RAG를 라이브로 동작시키려면 `app/ml-backend`(포트 3001)도 같이 띄워야 한다.
통합 가동(ml-backend + frontend + Electron 동시)은 `cd app && npm run dev` 참조 (`../README.md`).

---

## 화면 구성

| 라우트 | 모드 | 컴포넌트 |
|---|---|---|
| `/` | 타이틀 | `TitleScreen` |
| `/ep1/scene/2` ~ `/ep1/scene/4` | 정적 나레이션 | `NarrationScreen` |
| `/ep1/scene/5` ~ `/ep1/scene/7` | 인터랙션 (sLLM) | `InteractionScreen` |
| `/ep1/ending` | 엔딩 카드 | `EndingCard` |
| `/ep2/transition` | 카운드오버 | `TransitionEp2` |
| `/ep2/scene/1` ~ `/ep2/scene/3` | 정적 나레이션 | `NarrationScreen` |
| `/ep2/scene/4` | 인터랙션 | `InteractionScreen` |
| `/ep2/ending` | 엔딩 카드 | `EndingCard` |

각 인터랙션/나레이션 컴포넌트는 16:10 책 삽화 캔버스(`Frame` + `IllustrationLayer`) 위에 올라간다. 일러스트는 `public/illustrations/screen_*.webp` (Ep 1 8장) + `ep2_screen_*.webp` (Ep 2 5장).

---

## 디렉토리 구조

```
app/                    # Next.js App Router
├── layout.tsx          # 루트 layout (Providers + VnFrame + ToastHost + TransitionOverlay)
├── page.tsx            # / 타이틀
├── vn-frame.tsx        # 16:10 letterbox 컨테이너
├── globals.css         # VN 토큰 + 컴포넌트 스타일
├── ep1/
│   ├── scene/[id]/page.tsx
│   └── ending/page.tsx
└── ep2/
    ├── transition/page.tsx
    ├── scene/[id]/page.tsx
    └── ending/page.tsx

components/
├── vn/                 # 비주얼 노벨 컴포넌트 14종
└── ui/                 # shadcn/ui 베이스 (재활용)

data/
├── scenes/             # 정적 텍스트 + 인터랙션 메타
└── haeseol/            # 정적 풀이 (해설 패널)

lib/
├── api/                # SSE 클라이언트
├── hooks/              # useInteraction / useExplain / useSave / useNavigate
└── store/              # Redux slices (episode/dialogue/haeseol/save/ui)

public/illustrations/   # WebP 일러스트
```

---

## 빌드 / 검증

```bash
npx tsc --noEmit      # 타입 체크
npm run lint          # ESLint
npm run build         # 프로덕션 빌드
npm run start         # 프로덕션 실행
```

---

## 환경변수

| 변수 | 기본값 | 용도 |
|---|---|---|
| `NEXT_PUBLIC_API_BASE` | `http://localhost:3001` | 백엔드 base URL (`app/ml-backend/server.mjs`) |

`.env.local`에 정의. `process.env.NEXT_PUBLIC_API_BASE`로 `lib/api/sse.ts`에서 참조.

---

## 발표 / 시연

시연 흐름과 화면별 발표 포인트는 [`../../demo/scenario_script.md`](../../demo/scenario_script.md) 참조.
