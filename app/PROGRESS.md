# App Track 2 — Progress & Index

**최종 업데이트**: 2026-04-12 (Phase 2 완료 — vLLM 통합 + UI 대개편)
**상태**: 🟢 발표 데모 가동 중

---

## 🎯 현재 상태 요약

니체 페르소나 sLLM 상담 시스템의 웹 앱이 실제 파인튜닝된 모델과 연동되어 가동 중입니다.
Mock 모드에서 시작해 vLLM 모드로 전환 완료, UI를 ChatGPT/Claude 스타일로 재설계했습니다.

- **모델**: `banzack/nietzsche-gemma4-31b-lora` epoch 1 (merged, 62.6GB)
- **서빙**: vLLM OpenAI 호환 API (포트 8002, A100 80GB)
- **백엔드**: FastAPI + SQLite (포트 8000) — 원래 PostgreSQL 설계에서 SQLite로 전환 (사유: RunPod pod 내 Docker 불가)
- **프론트**: Next.js 16 production (포트 3000)
- **외부 노출**: Cloudflare Quick Tunnel 2개 (SSH 포워딩 차단 우회)

---

## 🟢 실행 중인 프로세스 (현재 pod)

| 서비스 | 포트 | 실행 방법 | 프로세스 로그 |
|---|---|---|---|
| vLLM | 8002 | `/workspace/tmp/vllm_serve*.log` 참조 | `ml/.venv` |
| FastAPI 백엔드 | 8000 | `poetry run uvicorn main:app` | `/workspace/tmp/backend.log` |
| Next.js 프론트 | 3000 | `npm run start` (production build) | `/workspace/tmp/frontend.log` |
| Cloudflare tunnel (frontend) | - | `./cloudflared tunnel --url http://localhost:3000` | `/workspace/tmp/cf_frontend*.log` |
| Cloudflare tunnel (backend) | - | `./cloudflared tunnel --url http://localhost:8000` | `/workspace/tmp/cf_backend*.log` |

**재현 명령어 세트 → `app/README.md`의 "Pod 재시작 복구 절차" 섹션 참조.**

---

## 📅 변경 로그 (최신순)

### 2026-04-12 (Phase 2) — vLLM 통합 + UI 대개편

#### 백엔드
- **SQLite 전환**: `DATABASE_URL=sqlite+aiosqlite:///./nietzsche.db` — 기존 모델이 generic SA 타입(Uuid, JSON)을 사용해서 코드 변경 없이 마이그레이션 성공
- **vLLM 실제 연동**: `LLM_MODE=vllm`, `LLM_BASE_URL=http://localhost:8002/v1`, `LLM_MODEL=nietzsche-epoch1`
- **DELETE 엔드포인트 추가**: `DELETE /api/v1/conversations/{id}` — Conversation의 `cascade="all, delete-orphan"` 덕분에 messages도 자동 삭제
- **Temperature 조정**: `services/llm_client.py`에서 0.8 → 0.5로 (환각 크게 감소)
- **System prompt 변경**: `prompts/nietzsche_v1.txt` → `prompts/nietzsche_contemplative.txt`
  - 내용: "나는 프리드리히 니체다. 나는 통찰을 던지고, 답을 강요하지 않는다. 나는 인간이 스스로 묻게 만든다."
  - 학습 데이터의 `contemplative_aphorism` voice 3개 variation 중 하나 (32.8% 분포)
- **CORS 와일드카드**: `CORS_ORIGINS=*` — Cloudflare tunnel 도메인 허용용

#### 프론트엔드 (대개편)
- **Sidebar 컴포넌트 신규** (`components/Sidebar.tsx`): 좌측 260px 고정, "+ 새 대화" 버튼, 가짜 최근 대화 5개, 하단 "신은 죽었다" 캡션
- **Layout 재배치** (`app/layout.tsx`): 좌측 sidebar + 우측 (header + main + footer) 구조. 입력창(footer)이 모든 페이지에서 하단 고정
- **ChatInput ChatGPT 스타일** (`components/chat/ChatInput.tsx`): 통합 컨테이너, focus 시 와인색 ring, 우측 하단 원형 ArrowUp 버튼, textarea 자동 높이 조절, 자체 `useStreamingChat` hook 호출
- **MessageBubble 개선** (`components/chat/MessageBubble.tsx`): 니체 응답 좌측에 3px 와인색 strip, "Nietzsche" 라벨 대문자+와인색+bold, 사용자 메시지는 진한 베이지+border
- **Header에 휴지통 버튼** (`components/Header.tsx`): `currentConversationId` 있을 때만 표시, `window.confirm` → DELETE 요청 → `router.replace("/")`
- **Redux thunk 추가** (`lib/store/chatSlice.ts`): `deleteConversation(conversationId)` — 성공 시 `messages=[]`, `currentConversationId=null`
- **next.config.ts**: `allowedDevOrigins: ["<cloudflare-domain>"]` — Next.js 16의 cross-origin dev 리소스 차단 우회
- **Turbopack + Tailwind 4 이슈 해결**: production build (`npm run build && npm start`) 사용, Cloudflare tunnel CSS 캐시 문제는 새 터널 발급으로 우회

#### 환경/인프라
- **Cloudflare Quick Tunnel 도입**: RunPod Basic SSH가 port forwarding 차단해서 대체 방안으로 채택. 프로세스 재시작 시 URL 재발급 필요
- **Poetry venv 복구 절차**: pod 재시작 후 `TMPDIR=/tmp python3.12 -m poetry install`로 우회 (MooseFS + `/root` 공간 부족 이슈)
- **Triton/torch_compile 캐시 정리**: `/root/.cache/vllm/torch_compile_cache/`, `/root/.triton/cache/`, `/tmp/torchinductor_root/` — GPU 바뀔 때마다 필요

### 2026-04-12 (이전) — Phase 1 완료
(원본 Track 2 Step 1~6: FastAPI + Mock LLM + SSE 스트리밍 + Redux + 기본 채팅 UI + 빈티지 디자인 적용)
→ 상세는 git log 참조: `git log --oneline -- app/`

---

## ⚠️ 알려진 한계 (발표 메타 인사이트)

현재 시스템에는 구조적 한계가 존재하며, 이는 **데이터 설계의 결과**로 파악되었습니다. 발표에서 이 한계들을 메타 인사이트로 활용합니다.

1. **Single-turn 학습**: 학습 데이터가 모두 `system → user → assistant` 1턴. 모델이 follow-up 요청("쉽게 설명해줘", "예시 들어줘")에 적응하는 패턴을 학습한 적 없음.
2. **Response pattern 단조성**: `contemplative_aphorism` voice 992개 샘플 대부분이 `reflection_reframing` 한 패턴("재해석 → 통찰 → 성찰 질문"). 추상 응답 회피 불가.
3. **Voice routing 부재**: 학습된 voice는 9개지만 추론 시 `contemplative` 하나만 고정 사용. 학습 투자의 일부만 활용.
4. **Voice-source entanglement**: `contemplative_aphorism`의 992개가 **100% 《즐거운 학문》(JW), 100% middle 시기**. voice 선택이 암묵적으로 사상 분포까지 결정.
5. **Control token 부재**: `response_pattern`, `philosophical_concept` 등 메타데이터는 데이터 생성 시에만 쓰였고 모델 input에 토큰으로 들어간 적 없음. 추론 때 제어 불가.
6. **Gemma chat template의 system role 미지원**: Gemma는 `system` role 분기가 없어 라이브러리가 자동으로 user에 prepend. multi-turn에서 system은 첫 턴에만 박힘.

**다음 작업 로드맵**: Multi-turn 학습 데이터 추가 + `assistant_only_loss` 활성화가 1~4번을 동시에 완화. v11 데이터셋 재설계 때 voice-source 독립성 확보.

---

## 📖 문서 맵

**이 PROGRESS.md는 진입점입니다.** 아래 표에서 필요한 정보에 해당하는 파일을 로드하세요.

### 프로젝트 이해
| 필요한 정보 | 파일 |
|---|---|
| 원본 작업 지시서 + 설계 의도 (Phase 1 기준) | `app/CLAUDE.md` |
| 아키텍처 다이어그램 + 데이터 흐름 | `app/backend/BACKEND_STRUCTURE.md` |

### 실행/재현
| 필요한 정보 | 파일 |
|---|---|
| **Pod 재시작 후 전체 시스템 복구 절차** | `app/README.md` |
| 백엔드 단독 실행 방법 + .env 설정 | `app/backend/README.md` |
| 프론트엔드 단독 실행 방법 + 컴포넌트 구조 | `app/frontend/README.md` |

### 코드 작업 규약
| 필요한 정보 | 파일 |
|---|---|
| 백엔드 레이어 책임 + 의존성 규칙 | `app/backend/CLAUDE.md` |
| Next.js 16 + Redux + SSE 가이드 | `app/frontend/CLAUDE.md` |
| Next.js 16 breaking changes 경고 | `app/frontend/AGENTS.md` |

### 주요 구현 세부사항 (소스 직접 참조)
| 기능 | 파일 |
|---|---|
| LLM 클라이언트 추상화 (Mock/VLLM) | `app/backend/services/llm_client.py` |
| `/chat` SSE 스트리밍 + DELETE | `app/backend/api/v1/endpoints/chat.py` |
| DB 모델 (Conversation, Message) | `app/backend/models/chat.py` |
| Alembic 초기 마이그레이션 | `app/backend/alembic/versions/001_initial_schema.py` |
| 환경 변수 schema | `app/backend/core/config.py` |
| SSE 스트리밍 훅 | `app/frontend/lib/hooks/useStreamingChat.ts` |
| Redux chat slice + delete thunk | `app/frontend/lib/store/chatSlice.ts` |
| Layout (sidebar + header + footer) | `app/frontend/app/layout.tsx` |
| Sidebar 컴포넌트 | `app/frontend/components/Sidebar.tsx` |
| ChatInput (ChatGPT 스타일) | `app/frontend/components/chat/ChatInput.tsx` |
| MessageBubble (좌측 strip) | `app/frontend/components/chat/MessageBubble.tsx` |

---

## 🔮 다음 단계 (발표 후)

### Phase 3 — 모델 한계 해소 (1~2주)
- [ ] Multi-turn 학습 데이터 200~500개 추가 생성
- [ ] `assistant_only_loss=True` 활성화 (Gemma 4 VLM 이슈 우회 방법 연구)
- [ ] 재학습 후 Stage B/C 평가 비교

### Phase 4 — RAG 파이프라인 (2~3주)
- [ ] 니체 저서 벡터화 (BGE-M3 + Qdrant)
- [ ] HyDE (Hypothetical Document Embeddings) 적용
- [ ] `services/vector_service.py` 구현 + `chat.py`와 통합

### Phase 5 — 데이터셋 v11 재설계 (장기)
- [ ] `voices.py` single source of truth
- [ ] Voice-source 독립성 확보 (각 voice가 모든 저서에서 sampling)
- [ ] 새 response_pattern 추가 (`concrete_example`, `simplification`, `dialogue_followup`)
- [ ] Control token 학습 실험

### Phase 6 — Routing (선택)
- [ ] Rule-based voice routing 프로토타입
- [ ] 필요 시 KoBERT classifier로 승격
- [ ] **우선순위 낮음**: v11 데이터 재설계 후에나 의미 있음 (엔탱글먼트 먼저 풀어야)

---

## 🧪 검증 명령어

```bash
# 1. 프로세스 살아있는지
ps aux | grep -E "vllm serve|uvicorn main:app|next start|cloudflared" | grep -v grep

# 2. 서비스 헬스체크
curl -s http://localhost:8000/health                                      # → {"status":"alive","mode":"vllm"}
curl -s http://localhost:8002/v1/models | python3 -m json.tool | head -20 # → nietzsche-epoch1

# 3. GPU 메모리
nvidia-smi | grep MiB

# 4. 현재 Cloudflare URL 확인 (임시, 재시작 시 변경됨)
grep "trycloudflare.com" /workspace/tmp/cf_frontend*.log | tail -1
grep "trycloudflare.com" /workspace/tmp/cf_backend*.log | tail -1
```
