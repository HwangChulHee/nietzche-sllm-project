"""Stage B 결과 통계 요약.

responses.jsonl을 읽어서:
  - 모델별 샘플 수, 평균 토큰, 토큰 분포, 잘림률
  - response_pattern별 breakdown
  - voice별 breakdown
  - 발표용 핵심 숫자 출력
"""
import json
from collections import defaultdict
from pathlib import Path

RESPONSES = Path("/workspace/nietzche-sllm-project/ml/finetune/outputs/stage_b/responses.jsonl")
MAX_TOKENS = 768

# ─────────────────────────────────────────────────────────
# 로드 + 방어적 처리
# ─────────────────────────────────────────────────────────
records = []
skipped = 0
with RESPONSES.open(encoding="utf-8") as f:
    for line in f:
        try:
            r = json.loads(line)
            # gen_tokens 없으면 char 길이로 추정 (대략 char/3 = token)
            if "gen_tokens" not in r:
                r["gen_tokens"] = len(r.get("generated", "")) // 3
                r["_estimated"] = True
            records.append(r)
        except json.JSONDecodeError:
            skipped += 1

print(f"Total records: {len(records)} (skipped {skipped} bad lines)")
est_count = sum(1 for r in records if r.get("_estimated"))
if est_count:
    print(f"  ⚠ {est_count} records had no gen_tokens, estimated from char length")

# ─────────────────────────────────────────────────────────
# 모델별 통계
# ─────────────────────────────────────────────────────────
print("\n" + "=" * 78)
print("모델별 전체 통계")
print("=" * 78)
print(f"{'model':<10} {'n':>4} {'tok_avg':>8} {'tok_min':>8} {'tok_max':>8} {'char_avg':>9} {'trunc':>8}")
print("-" * 78)

by_model = defaultdict(list)
for r in records:
    by_model[r["model_tag"]].append(r)

model_stats = {}
for tag in sorted(by_model):
    rows = by_model[tag]
    tokens = [r["gen_tokens"] for r in rows]
    chars = [len(r.get("generated", "")) for r in rows]
    trunc = sum(1 for t in tokens if t >= MAX_TOKENS)
    
    stats = {
        "n": len(rows),
        "tok_avg": sum(tokens) / len(tokens),
        "tok_min": min(tokens),
        "tok_max": max(tokens),
        "char_avg": sum(chars) / len(chars),
        "trunc": trunc,
        "trunc_pct": trunc / len(rows) * 100,
    }
    model_stats[tag] = stats
    
    print(f"{tag:<10} {stats['n']:>4} {stats['tok_avg']:>8.1f} "
          f"{stats['tok_min']:>8} {stats['tok_max']:>8} "
          f"{stats['char_avg']:>9.0f} "
          f"{stats['trunc']:>3}/{stats['n']:<3} ({stats['trunc_pct']:>3.0f}%)")

# ─────────────────────────────────────────────────────────
# 길이 변화 그래프 (ASCII)
# ─────────────────────────────────────────────────────────
print("\n" + "=" * 78)
print("응답 길이 변화 (평균 토큰)")
print("=" * 78)

max_avg = max(s["tok_avg"] for s in model_stats.values())
for tag in sorted(model_stats):
    s = model_stats[tag]
    bar_len = int(s["tok_avg"] / max_avg * 60)
    bar = "█" * bar_len
    trunc_flag = f" ⚠ {s['trunc_pct']:.0f}% trunc" if s["trunc_pct"] >= 10 else ""
    print(f"  {tag:<10} {bar} {s['tok_avg']:.0f}{trunc_flag}")

# ─────────────────────────────────────────────────────────
# response_pattern별 breakdown
# ─────────────────────────────────────────────────────────
print("\n" + "=" * 78)
print("Response Pattern별 평균 토큰 (모델 × 패턴)")
print("=" * 78)

patterns = sorted(set(r["response_pattern"] for r in records if "response_pattern" in r))
models = sorted(model_stats.keys())

# 헤더
print(f"{'pattern':<30}", end="")
for m in models:
    print(f"{m:>10}", end="")
print()
print("-" * (30 + 10 * len(models)))

# 각 패턴 × 모델 평균
for p in patterns:
    print(f"{p:<30}", end="")
    for m in models:
        matching = [r["gen_tokens"] for r in records 
                    if r.get("response_pattern") == p and r["model_tag"] == m]
        if matching:
            avg = sum(matching) / len(matching)
            print(f"{avg:>10.0f}", end="")
        else:
            print(f"{'--':>10}", end="")
    print()

# ─────────────────────────────────────────────────────────
# Voice별 breakdown
# ─────────────────────────────────────────────────────────
print("\n" + "=" * 78)
print("Voice별 평균 토큰 (모델 × voice)")
print("=" * 78)

voices = sorted(set(r["voice"] for r in records if "voice" in r))

print(f"{'voice':<30}", end="")
for m in models:
    print(f"{m:>10}", end="")
print()
print("-" * (30 + 10 * len(models)))

for v in voices:
    print(f"{v:<30}", end="")
    for m in models:
        matching = [r["gen_tokens"] for r in records 
                    if r.get("voice") == v and r["model_tag"] == m]
        if matching:
            avg = sum(matching) / len(matching)
            print(f"{avg:>10.0f}", end="")
        else:
            print(f"{'--':>10}", end="")
    print()

# ─────────────────────────────────────────────────────────
# Difficulty별 breakdown
# ─────────────────────────────────────────────────────────
print("\n" + "=" * 78)
print("Difficulty별 평균 토큰")
print("=" * 78)

diffs = sorted(set(r.get("difficulty", "unknown") for r in records))
print(f"{'difficulty':<15}", end="")
for m in models:
    print(f"{m:>10}", end="")
print()
print("-" * (15 + 10 * len(models)))

for d in diffs:
    print(f"{d:<15}", end="")
    for m in models:
        matching = [r["gen_tokens"] for r in records 
                    if r.get("difficulty") == d and r["model_tag"] == m]
        if matching:
            avg = sum(matching) / len(matching)
            print(f"{avg:>10.0f}", end="")
        else:
            print(f"{'--':>10}", end="")
    print()

# ─────────────────────────────────────────────────────────
# 발표용 핵심 숫자
# ─────────────────────────────────────────────────────────
print("\n" + "=" * 78)
print("발표용 핵심 숫자")
print("=" * 78)

if "baseline" in model_stats and "epoch2" in model_stats:
    b = model_stats["baseline"]
    e2 = model_stats["epoch2"]
    reduction = (1 - e2["tok_avg"] / b["tok_avg"]) * 100
    print(f"\n1. LoRA 효과 (baseline → epoch2):")
    print(f"   baseline: {b['tok_avg']:.0f} tokens, {b['char_avg']:.0f} chars")
    print(f"   epoch2:   {e2['tok_avg']:.0f} tokens, {e2['char_avg']:.0f} chars")
    print(f"   감소율:   {reduction:.0f}%")

if "epoch2" in model_stats and "epoch5" in model_stats:
    e2 = model_stats["epoch2"]
    e5 = model_stats["epoch5"]
    increase = (e5["tok_avg"] / e2["tok_avg"] - 1) * 100
    print(f"\n2. 오버피팅 증거 (epoch2 → epoch5):")
    print(f"   epoch2:   {e2['tok_avg']:.0f} tokens, trunc {e2['trunc_pct']:.0f}%")
    print(f"   epoch5:   {e5['tok_avg']:.0f} tokens, trunc {e5['trunc_pct']:.0f}%")
    print(f"   증가율:   +{increase:.0f}%")

print(f"\n3. 전체 응답 수: {len(records)} / 기대 828")
if len(records) != 828:
    print(f"   ⚠ 예상과 다름")
