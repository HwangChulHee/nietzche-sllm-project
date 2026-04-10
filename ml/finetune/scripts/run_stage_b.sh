#!/bin/bash
# Stage B 전체 실행 — 단순 인터리브 (가장 안전)
#
# 흐름:
#   1. baseline 추론 (ml venv)
#   2. epoch1 추론 (이미 merged) → 삭제
#   3. epoch2~5: merge (finetune venv) → 추론 (ml venv) → 삭제
#
# 예상 시간: ~170~205분
#
# 재시작 가능: stage_b_generate.py가 이미 처리된 (sample_id, model_tag) skip
#
# 사용:
#   cd /workspace/nietzche-sllm-project/ml
#   bash finetune/scripts/run_stage_b.sh 2>&1 | tee finetune/logs/stage_b_run.log

set -e  # 에러 발생 시 즉시 중단

# ─────────────────────────────────────────────────────────
# 경로
# ─────────────────────────────────────────────────────────
ML_DIR="/workspace/nietzche-sllm-project/ml"
ML_VENV="${ML_DIR}/.venv/bin/activate"
FT_VENV="${ML_DIR}/finetune/.venv/bin/activate"
MERGED_DIR="${ML_DIR}/finetune/outputs/merged"
SCRIPTS_DIR="${ML_DIR}/finetune/scripts"
LOG_DIR="${ML_DIR}/finetune/logs"

mkdir -p "$LOG_DIR"

# ─────────────────────────────────────────────────────────
# 헬퍼
# ─────────────────────────────────────────────────────────
log() {
    echo ""
    echo "════════════════════════════════════════════════════════════"
    echo "  [$(date +%H:%M:%S)] $1"
    echo "════════════════════════════════════════════════════════════"
}

run_inference() {
    local TAG=$1
    local PATH_=$2
    log "INFERENCE: $TAG"
    cd "$ML_DIR"
    source "$ML_VENV"
    python finetune/scripts/stage_b_generate.py \
        --model-tag "$TAG" \
        --model-path "$PATH_" \
        2>&1 | tee -a "$LOG_DIR/stage_b_${TAG}.log"
    deactivate
}

run_merge() {
    local EPOCH=$1
    log "MERGE: epoch${EPOCH}"
    cd "$ML_DIR/finetune"
    source "$FT_VENV"
    python scripts/merge_one.py --epoch "$EPOCH" \
        2>&1 | tee -a "$LOG_DIR/merge_epoch${EPOCH}.log"
    deactivate
}

cleanup_merged() {
    local EPOCH=$1
    local TARGET="${MERGED_DIR}/epoch${EPOCH}"
    if [ -d "$TARGET" ]; then
        log "CLEANUP: removing ${TARGET}"
        rm -rf "$TARGET"
        echo "  ✓ Removed (disk reclaimed ~62 GB)"
    fi
}

disk_status() {
    echo ""
    echo "  [disk] $(du -sh $MERGED_DIR 2>/dev/null || echo '0  '$MERGED_DIR' (empty)')"
    echo "  [free] $(df -h /workspace | tail -1 | awk '{print "Used "$3" / "$2" ("$5")"}')"
}

# ─────────────────────────────────────────────────────────
# 시작
# ─────────────────────────────────────────────────────────
START_TIME=$(date +%s)
log "STAGE B START — $(date)"
disk_status

# Step 1: baseline (HF에서)
run_inference "baseline" "google/gemma-4-31B-it"
disk_status

# Step 2: epoch1 (이미 merged 됨, Test B-1에서)
if [ ! -d "${MERGED_DIR}/epoch1" ]; then
    log "epoch1 merged 디렉토리 없음 — merge 실행"
    run_merge 1
fi
run_inference "epoch1" "${MERGED_DIR}/epoch1"
cleanup_merged 1
disk_status

# Step 3: epoch2 ~ epoch5
for EPOCH in 2 3 4 5; do
    run_merge $EPOCH
    disk_status
    
    run_inference "epoch${EPOCH}" "${MERGED_DIR}/epoch${EPOCH}"
    cleanup_merged $EPOCH
    disk_status
done

# ─────────────────────────────────────────────────────────
# 완료
# ─────────────────────────────────────────────────────────
END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
ELAPSED_MIN=$((ELAPSED / 60))

log "STAGE B COMPLETE"
echo ""
echo "  Total time: ${ELAPSED_MIN} min ($((ELAPSED / 3600))h $((ELAPSED % 3600 / 60))m)"
echo "  Output:     ${ML_DIR}/finetune/outputs/stage_b/responses.jsonl"
echo ""
echo "  다음 단계: Stage C (judge 채점)"
