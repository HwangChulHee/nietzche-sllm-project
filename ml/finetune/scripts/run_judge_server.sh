#!/usr/bin/env bash
# Stage C — Judge 서버 (vLLM)
#
# Gemma 4 26B-A4B-it을 localhost:8000에 띄웁니다.
# Stage A와 동일 모델·동일 포트 — 점수 축 호환성 유지.
#
# 사용법:
#   cd /workspace/nietzche-sllm-project/ml
#   source .venv/bin/activate                     # ml venv (vLLM 0.19)
#   bash finetune/scripts/run_judge_server.sh
#
# 중지:
#   kill $(cat finetune/logs/stage_c_judge_server.pid)
#
set -euo pipefail

MODEL="google/gemma-4-26B-A4B-it"
PORT=8000
LOG_DIR="$(cd "$(dirname "$0")/.." && pwd)/logs"
LOG_FILE="$LOG_DIR/stage_c_judge_server.log"
PID_FILE="$LOG_DIR/stage_c_judge_server.pid"

mkdir -p "$LOG_DIR"

# 이미 떠 있으면 재사용
if curl -s "http://localhost:${PORT}/v1/models" > /dev/null 2>&1; then
  echo "[judge] 이미 :${PORT} 에서 응답 중. 중복 실행 스킵."
  curl -s "http://localhost:${PORT}/v1/models" | python -m json.tool
  exit 0
fi

echo "[judge] Starting vLLM server"
echo "[judge]   Model: $MODEL"
echo "[judge]   Port : $PORT"
echo "[judge]   Log  : $LOG_FILE"

# vLLM 0.19 OpenAI-compatible 서버
# max-model-len 8192 — judge prompt (~2K) + 응답 (300) 충분
# gpu-memory-utilization 0.88 — 26B bf16 + KV 캐시 여유
nohup python -m vllm.entrypoints.openai.api_server \
  --model "$MODEL" \
  --port "$PORT" \
  --dtype bfloat16 \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.88 \
  --served-model-name "$MODEL" \
  > "$LOG_FILE" 2>&1 &

SERVER_PID=$!
echo "$SERVER_PID" > "$PID_FILE"
echo "[judge] PID: $SERVER_PID (saved to $PID_FILE)"

# 헬스체크 — 최대 10분 대기 (첫 로딩은 느림)
echo "[judge] Waiting for server to become ready (up to 10min)..."
for i in $(seq 1 120); do
  if curl -s "http://localhost:${PORT}/v1/models" > /dev/null 2>&1; then
    elapsed=$((i * 5))
    echo "[judge] Ready after ${elapsed}s"
    curl -s "http://localhost:${PORT}/v1/models" | python -m json.tool
    echo ""
    echo "[judge] 다음 명령으로 채점 시작:"
    echo "  python finetune/scripts/stage_c_score.py --limit 20   # 테스트"
    echo "  python finetune/scripts/stage_c_score.py               # 본 실행"
    exit 0
  fi
  # 프로세스가 죽었는지 확인
  if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "[judge] 서버 프로세스가 죽음. 로그:"
    tail -50 "$LOG_FILE"
    exit 1
  fi
  sleep 5
done

echo "[judge] Timeout (10min). 로그 확인:"
tail -50 "$LOG_FILE"
exit 1
