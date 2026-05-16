# app/ml-backend

차라투스트라 비주얼노벨 해설 모드의 윈도우 온디바이스 RAG 백엔드.

---

## 컨텍스트

큰 프로젝트는 **"차라투스트라와의 동행"** — 니체 페르소나 기반 인터랙티브 철학 비주얼 노벨 (고급캡스톤디자인). 세 모드(나레이션·해설·인터랙션) 중 **해설 모드**의 멀티턴 RAG 파이프라인이 이 디렉토리.

원래 별도 작업 디렉토리(`nietzche-local`)의 PoC였고, **2026-05-16 통합 작업으로 메인 repo의 `app/ml-backend/`로 이주**했다. RunPod 클라우드 트랙(vLLM/Qdrant) 폐기 후 채택된 llama.cpp/sqlite-vec 트랙. CLI(`multiturn_rag.mjs`)는 디버깅용으로 보존, 비주얼 노벨에서 호출하는 HTTP 진입점은 `server.mjs` (포트 3001).

---

## 빠른 시작

전제: PowerShell 7, `chcp 65001` 영구화, 모델 파일 `C:\models\`에 배치.

**터미널 1 — Chat (포트 8000)**
```powershell
cd C:\Users\hch\llama-b9159-bin-win-cpu-x64
$kwargs = '{"enable_thinking":false}'
.\llama-server.exe -m C:\models\gemma-4-E2B-it-Q4_K_M.gguf --port 8000 -c 8192 -t 6 `
  --jinja --chat-template-kwargs $kwargs `
  --temp 0.7 --top-p 0.95 --top-k 64
```

**터미널 2 — Embeddings (포트 8001)**
```powershell
cd C:\Users\hch\llama-b9159-bin-win-cpu-x64
.\llama-server.exe -m C:\models\bge-m3-q4_k_m.gguf --port 8001 `
  --embeddings --pooling mean -c 2048 -t 4
```

**터미널 3 — CLI (디버깅)**
```powershell
cd app/ml-backend
node multiturn_rag.mjs
```

비주얼 노벨에서 호출할 때는 CLI 대신 HTTP 래퍼를 띄운다 (`server.mjs`, 포트 3001).
통합 가동(`cd app && npm run dev`)은 ml-backend + frontend + Electron을 한 번에 띄움 — `../README.md` 참조.

**인덱스 재빌드 (코퍼스 변경 시만)**
```powershell
node build_index.mjs   # 8001 서버 떠 있어야 함
```

---

## 아키텍처

```
사용자 입력
    ↓
[Router]  ──► OUT_OF_DOMAIN  → short-circuit (거절 메시지)
              AMBIGUOUS      → short-circuit (되묻기)
    ↓ COMMENTARY
[Rewriter]  → standalone 검색 쿼리
    ↓
[BGE-M3 임베딩] + [sqlite-vec 검색]  (top-K=5)
    ↓
[Generator]  → 스트리밍 응답
```

3단계 LLM 호출(router · rewriter · generator) 모두 같은 E2B 인스턴스 재사용. RAG retrieval은 별도 BGE-M3 임베딩 서버.

**모델 / 포트**
| 역할 | 모델 | 포트 | 메모리 |
|---|---|---|---|
| Chat (router/rewriter/generator) | Gemma 4 E2B Q4_K_M | 8000 | ~1.5GB |
| Embeddings | BGE-M3 Q4_K_M | 8001 | ~500MB |
| Vector store | sqlite-vec (corpus.db) | — | ~80MB |

**호출 비용 / 턴**
- COMMENTARY: 3 호출 (router + rewriter + generator) ≈ 25~30초
- OUT_OF_DOMAIN / AMBIGUOUS: 1 호출 (router only) ≈ 2~5초

---

## 디렉토리 구조

```
app/ml-backend/
├── prompts/                  system prompts (별도 파일로 분리)
│   ├── router.md
│   ├── query_rewriter.md
│   └── commentary_system.md
├── data/                     원천 jsonl (원전 + 풀이 청크)
│   ├── orig_tsz_p1_prologue.jsonl     (원전 6청크)
│   └── interp_tsz_p1_prologue.jsonl   (풀이 13청크)
├── logs/                     세션 JSONL (gitignore)
├── sessions/                 /save 출력 (gitignore)
├── corpus.db                 벡터 인덱스 (build_index.mjs로 재빌드 가능)
├── prompts.mjs               prompt 로더
├── router.mjs                intent classification
├── query_rewriter.mjs        coreference resolution
├── search.mjs                sqlite-vec wrapper
├── logger.mjs                콘솔 (ANSI) + JSONL 로깅
├── build_index.mjs           코퍼스 → corpus.db 인덱싱
├── multiturn_rag.mjs         CLI (디버깅 진입점)
└── server.mjs                Express + SSE HTTP 래퍼 (포트 3001, 비주얼 노벨 진입점)
```

**의존성**: Node.js 22+, `better-sqlite3`, `sqlite-vec`. Python 없음.

---

## 운영 명령 (CLI)

| 명령 | 동작 |
|---|---|
| `/reset` | 히스토리 초기화 |
| `/save` | 현재 대화를 `sessions/`에 JSON 저장 |
| `/context` | 마지막 검색 쿼리 |
| `/router` | 마지막 라우팅 결과 (intent, message, duration) |
| `/rewrite` | 마지막 쿼리 재작성 결과 |
| `/log` | 현재 세션 로그 파일 경로 |
| `/stats` | 세션 통계 (턴, intent 분포, 평균 시간) |
| `/verbose on\|off` | 토큰 stream 출력 토글 |
| `/quit` | 종료 |

---

## 알려진 한계

- **AMBIGUOUS conversational drift**: 직전 대화 주제에 분류가 끌림. "그 짐승들은?" 같은 모호 referent를 직전 응답에 명사가 없는데도 COMMENTARY로 분류. Router prompt 3시도 강화(엄격 기준 → 예시 보강 → self-check 가이드) 모두 실패. sLLM 본질적 한계(작은 모델의 context contagion). 시연 시 시나리오 통제로 우회. RAG가 청크 회수해 응답은 정상.
- **응답 다양성 약함**: 청크 19개 한정 → 같은 주제 후속 질문 시 비슷한 응답. 코퍼스 확장(차라 1부 22편) 시 자연 해소.
- **CPU only**: 1턴당 ~25초. GPU 가속 시 단축 가능.

---

## 결정 로그

**채택**
- llama.cpp (서버 모드) + Node.js 22 ESM
- Gemma 4 E2B Q4_K_M (단일 모델로 모든 LLM 호출)
- BGE-M3 Q4_K_M (임베딩)
- sqlite-vec (벡터 + SQLite 통합 — 향후 세이브/히스토리도 같은 DB)
- 3-way Router (COMMENTARY / OUT_OF_DOMAIN / AMBIGUOUS) + selective short-circuit
- Query Rewriting (standalone 쿼리, 첫 턴 skip)
- Electron (Next.js wrap 예정)
- prompts/ 디렉토리 (system prompt 코드 분리)

**폐기** *(재시도 시 비용 인지)*
- RunPod 클라우드 + vLLM 트랙 (CUDA 드라이버 호환 + 학생 비용)
- Qdrant (sqlite-vec로 통합)
- Tauri (Next.js 친숙도 + node-llama-cpp 호환으로 Electron 선택)
- HyDE (프로덕션 표준 아님, 비용 대비 효과 미미)
- Hybrid 검색 (온디바이스 회피, dense only로 충분)
- E4B/31B 우선 트랙 (E2B 단독으로 검증 완료)
- REFRAMING intent (4-way 분류 신뢰도 불확실 + 호출 절약 0.2/턴으로 미미)
- presence_penalty 1.0 (한국어 발산 부작용)
- Fine-tuning (P2 후순위, 발표 마감 ROI 부족)

---

## 향후 작업 (P1 ~ P2)

- 코퍼스 확장 (Discourses 1부 22편 → 19청크 → 100+청크)
- 평가 프레임워크 (3축: RAG 정확도 / 페르소나 / 멀티턴 일관성)
- 인터랙션 모드 페르소나 prompt (차라투스트라 발화)

---

## 트러블슈팅

**한글 깨짐**: PowerShell 7 사용 + `$PROFILE`에 `chcp 65001 > $null` 영구화.

**포트 충돌**:
```powershell
Get-NetTCPConnection -LocalPort 8000 | Select-Object OwningProcess
Stop-Process -Id <PID>
```

**thinking 토큰이 응답에 섞임**: chat 서버 실행 시 `--jinja --chat-template-kwargs $kwargs` 누락 확인.

**corpus.db 없음**: `node build_index.mjs` (단, 8001 임베딩 서버 떠 있어야 함).