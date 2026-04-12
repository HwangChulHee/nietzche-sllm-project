# 니체 페르소나 sLLM 상담 시스템 — App Layer

> 캡스톤 디자인 프로젝트. Fine-tuned Gemma 4 31B (LoRA) + FastAPI + Next.js 16 + vLLM.

**프로젝트 상태 및 최근 변경 사항은 [`PROGRESS.md`](./PROGRESS.md)를 먼저 참조하세요.**

---

## 아키텍처

외부 접근 (Cloudflare Quick Tunnel):
- `ran-*.trycloudflare.com` → localhost:3000 (frontend)
- `derby-*.trycloudflare.com` → localhost:8000 (backend API)

내부 서비스 연결:
- Next.js 16 (:3000, Redux + SSE) → FastAPI (:8000, SQLite) → vLLM (:8002, Gemma 4 31B + LoRA merged, A100 80GB)

모든 서비스는 동일한 RunPod pod 안에서 실행됩니다. 외부 접근은 Cloudflare Quick Tunnel로 노출합니다 (RunPod Basic SSH는 port forwarding을 차단).

---

## 디렉토리 구조

- `app/README.md` — 이 문서 (빠른 시작 + 재현)
- `app/PROGRESS.md` — 진입점, 현재 상태, 문서 맵
- `app/CLAUDE.md` — 원본 작업 지시서 (Phase 1 기준)

### Backend (`app/backend/`)
- `README.md` — 백엔드 실행/엔드포인트
- `CLAUDE.md` — 백엔드 레이어 가이드
- `BACKEND_STRUCTURE.md` — 아키텍처 설계
- `main.py`, `api/v1/endpoints/`, `services/`, `models/`, `prompts/`, `alembic/`

### Frontend (`app/frontend/`)
- `README.md` — 프론트 실행/컴포넌트
- `CLAUDE.md` — Next.js 16 + Redux 가이드
- `AGENTS.md` — Next.js 16 경고
- `app/`, `components/` (Sidebar, Header, chat/*), `lib/` (store, hooks)

---

## Pod 재시작 복구 절차

RunPod pod가 재시작되면 아래 순서대로 복구합니다. 각 단계에서 에러가 나면 멈추고 로그를 확인하세요.

### 0. 환경 확인

    nvidia-smi                                          # GPU 살아있나
    ls /workspace/nietzche-sllm-project                 # 프로젝트 있나
    ls /workspace/nietzche-sllm-project/ml/.venv        # ml venv (vLLM용)

### 1. vLLM 서버 시작 (포트 8002)

LoRA 모델은 merged 상태여야 합니다. 없으면 먼저 merge:

    cd /workspace/nietzche-sllm-project/ml/finetune
    ls outputs/merged/epoch1   # 있어야 함 (62.6GB)
    # 없으면: poetry run python scripts/merge_one.py --epoch 1

vLLM 서빙:

    cd /workspace/nietzche-sllm-project
    source ml/.venv/bin/activate

    # Triton/torch_compile 캐시 정리 (GPU 바뀔 때마다 필요)
    rm -rf /root/.cache/vllm/torch_compile_cache/ /root/.triton/cache/ /tmp/torchinductor_root/

    export TRITON_DISABLE_AUTOTUNE=1
    nohup vllm serve /workspace/nietzche-sllm-project/ml/finetune/outputs/merged/epoch1 \
      --served-model-name nietzsche-epoch1 \
      --host 0.0.0.0 --port 8002 \
      --max-model-len 2048 \
      --gpu-memory-utilization 0.90 \
      --dtype bfloat16 \
      > /workspace/tmp/vllm_serve.log 2>&1 &

    # 준비 완료까지 약 1-2분
    tail -f /workspace/tmp/vllm_serve.log
    # "Application startup complete" 보이면 Ctrl+C

    # 검증
    curl -s http://localhost:8002/v1/models | python3 -m json.tool

### 2. 백엔드 시작 (포트 8000)

    cd /workspace/nietzche-sllm-project/app/backend

    # Poetry 환경 확인 (pod 재시작 후 깨졌으면 재설치)
    poetry env info --path 2>/dev/null || TMPDIR=/tmp python3.12 -m poetry install

    # DB 마이그레이션 (첫 시작이거나 nietzsche.db 없을 때)
    poetry run alembic upgrade head

    # 서버 실행
    nohup poetry run uvicorn main:app --host 0.0.0.0 --port 8000 \
      > /workspace/tmp/backend.log 2>&1 &

    sleep 3
    curl -s http://localhost:8000/health
    # → {"status":"alive","mode":"vllm"}

### 3. 프론트엔드 시작 (포트 3000)

    cd /workspace/nietzche-sllm-project/app/frontend

    # Node.js 환경 (nvm 필요하면 source)
    export NVM_DIR=/workspace/.nvm
    source $NVM_DIR/nvm.sh 2>/dev/null
    node --version   # v20+ 이어야 함

    # 의존성 확인
    ls node_modules >/dev/null 2>&1 || npm install

    # Production build (dev 모드는 Tailwind 4 + Turbopack 이슈 있음)
    rm -rf .next
    npm run build

    # Start
    nohup npm run start > /workspace/tmp/frontend.log 2>&1 &
    sleep 4
    curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3000
    # → 200

### 4. Cloudflare Tunnel 시작 (외부 노출)

    cd /workspace/tmp

    # cloudflared 바이너리 확인 (없으면 다운로드)
    [ -f cloudflared-linux-amd64 ] || {
      wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
      chmod +x cloudflared-linux-amd64
    }

    # 프론트용 터널
    nohup ./cloudflared-linux-amd64 tunnel --url http://localhost:3000 \
      > /workspace/tmp/cf_frontend.log 2>&1 &

    # 백엔드용 터널
    nohup ./cloudflared-linux-amd64 tunnel --url http://localhost:8000 \
      > /workspace/tmp/cf_backend.log 2>&1 &

    sleep 6

    # 새 URL 확인
    echo "=== FRONTEND ==="
    grep "trycloudflare.com" /workspace/tmp/cf_frontend.log | tail -1
    echo "=== BACKEND ==="
    grep "trycloudflare.com" /workspace/tmp/cf_backend.log | tail -1

### 5. 새 Cloudflare URL 반영

매번 새 URL이 발급되므로 두 파일 수정 + 프론트 재빌드 필요:

    # 1) 프론트 .env.local에 새 백엔드 URL
    cd /workspace/nietzche-sllm-project/app/frontend
    cat > .env.local << EOF
    NEXT_PUBLIC_API_BASE=<새-backend-URL>
    EOF

    # 2) next.config.ts의 allowedDevOrigins에 새 frontend 도메인 반영
    #    (production 모드라 엄밀히는 불필요하지만 안전하게)
    #    vim next.config.ts 으로 도메인 수동 수정

    # 3) 재빌드 + 재시작
    pkill -9 -f "next" 2>/dev/null
    sleep 2
    rm -rf .next
    npm run build
    nohup npm run start > /workspace/tmp/frontend.log 2>&1 &
    sleep 4

### 6. 검증

    # 모든 프로세스 살아있는지
    ps aux | grep -E "vllm serve|uvicorn main:app|next start|cloudflared" | grep -v grep

    # 시크릿 창에서 프론트 Cloudflare URL 접속 → 채팅 테스트

---

## 발표 데모 시연 순서

1. **워밍업** (시크릿 창, 녹화 시작 전)
   - 프론트 Cloudflare URL 접속
   - 아무 메시지 → 첫 응답 받기 (vLLM KV cache 워밍업)
   - 휴지통 버튼으로 대화 삭제

2. **녹화 시작**

3. **4턴 시연** (한 대화 안에서):
   - `삶이 무의미하게 느껴집니다.`
   - `왜 그렇게 생각해?`
   - `너무 어려워. 쉬운 말로 다시 설명해줘.`
   - `그래서 내가 뭘 해야 돼?`

4. **녹화 종료**

5. **(선택) 한계 시연** — 학습 분포 밖 입력:
   - `뭐하고 살아야 될지 모르겠다` — 환각 또는 drift 가능

시연용 질문 리스트 및 각 턴의 나레이션 포인트는 `PROGRESS.md`의 "알려진 한계" 섹션 참조.

---

## 트러블슈팅

### vLLM 시작 시 Triton 커널 에러

증상: `RuntimeError: Triton Error [CUDA]: device kernel image is invalid`

원인: 네트워크 FS (MooseFS)에 남아있는 오래된 torch_compile/triton 캐시.

해결: `rm -rf /root/.cache/vllm/torch_compile_cache/ /root/.triton/cache/ /tmp/torchinductor_root/` 후 재시도. `TRITON_DISABLE_AUTOTUNE=1` 설정.

### Poetry 설치 실패 (HF_HUB / /root 공간 부족)

원인: RunPod의 `/root`는 20GB 제한, HF 캐시가 꽉 참.

해결: 모든 캐시 환경변수를 `/workspace` 하위로.

    export HF_HOME=/workspace/.cache/huggingface
    export HF_HUB_CACHE=/workspace/.cache/huggingface/hub
    export HF_HUB_DISABLE_XET=1
    export PIP_CACHE_DIR=/workspace/.cache/pip
    export TMPDIR=/tmp

### Cloudflare Tunnel에서 CSS가 깨져 보임

원인: Cloudflare Quick Tunnel이 이전 빌드의 CSS를 캐시.

해결: 새 터널 발급 (cloudflared 프로세스 kill 후 재시작). 시크릿 창으로 접속.

### Next.js 16 dev 모드에서 cross-origin 차단

증상: `Blocked cross-origin request to Next.js dev resource`

해결: `next.config.ts`의 `allowedDevOrigins`에 Cloudflare 도메인 추가. Production 모드(`npm run build && start`)는 이 제약 없음.

### 백엔드가 `{"mode":"mock"}` 반환

원인: `.env`에 `LLM_MODE=vllm` 설정 안 됨.

해결: `app/backend/.env` 확인 후 백엔드 재시작.

---

## 다음 문서로

- 지금 시스템이 어떻게 돌아가는지 더 알고 싶으면 → [`PROGRESS.md`](./PROGRESS.md)
- 백엔드 코드 작업이 필요하면 → [`backend/README.md`](./backend/README.md)
- 프론트엔드 코드 작업이 필요하면 → [`frontend/README.md`](./frontend/README.md)
- 원본 설계 의도를 알고 싶으면 → [`CLAUDE.md`](./CLAUDE.md)
