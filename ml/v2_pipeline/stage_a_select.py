"""Stage A — Select: A+B 등급 → stratified train/eval split.

입력: v2_data/sft_candidates/deduped.jsonl
출력: v2_data/sft_dataset/train.jsonl
     v2_data/sft_dataset/eval.jsonl
     v2_data/sft_dataset/select_report.json

규칙:
- A+B만 사용 (C, F 폐기)
- 95/5 split
- (voice × response_pattern × use_case) stratified
- 그룹 크기 < 5면 전부 train (eval에 너무 작은 그룹 방지)
- 그룹 내에서 점수 높은 순 → 상위 95% train, 하위 5% eval
  (점수 높은 게 train으로 가야 학습 효과 ↑)
- split 필드 채우기
"""
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

INPUT = Path("v2_data/sft_candidates/deduped.jsonl")
TRAIN_OUT = Path("v2_data/sft_dataset/train.jsonl")
EVAL_OUT = Path("v2_data/sft_dataset/eval.jsonl")
REPORT = Path("v2_data/sft_dataset/select_report.json")

ACCEPTED_GRADES = {"A", "B"}
EVAL_RATIO = 0.05
MIN_GROUP_FOR_EVAL = 5  # 그룹이 이보다 작으면 전부 train으로
SEED = 42


def stratify_key(s):
    return (s["voice"], s["response_pattern"], s["use_case"])


def main():
    samples = [json.loads(l) for l in INPUT.open(encoding="utf-8")]
    print(f"입력: {len(samples)}")
    
    # 등급 필터
    accepted = [s for s in samples if s.get("grade") in ACCEPTED_GRADES]
    rejected = len(samples) - len(accepted)
    print(f"A+B 통과: {len(accepted)} (폐기 {rejected})")
    
    # Stratification
    groups = defaultdict(list)
    for s in accepted:
        groups[stratify_key(s)].append(s)
    
    print(f"\nStratification 그룹: {len(groups)}개")
    
    rng = random.Random(SEED)
    train, eval_set = [], []
    small_groups = 0
    
    for key, group in groups.items():
        # 점수 높은 순 정렬 (동점이면 랜덤)
        group_with_jitter = [(s["normalized_score"] + rng.random() * 1e-6, s) for s in group]
        group_with_jitter.sort(key=lambda x: -x[0])
        sorted_group = [s for _, s in group_with_jitter]
        
        if len(sorted_group) < MIN_GROUP_FOR_EVAL:
            train.extend(sorted_group)
            small_groups += 1
            continue
        
        n_eval = max(1, round(len(sorted_group) * EVAL_RATIO))
        # 점수 높은 거 train, 낮은 거 eval (학습 우선)
        train.extend(sorted_group[:-n_eval])
        eval_set.extend(sorted_group[-n_eval:])
    
    print(f"  작은 그룹(< {MIN_GROUP_FOR_EVAL}): {small_groups}개 → 전부 train")
    
    # split 필드 채우기
    for s in train:
        s["split"] = "train"
    for s in eval_set:
        s["split"] = "eval"
    
    # 저장
    TRAIN_OUT.parent.mkdir(parents=True, exist_ok=True)
    with TRAIN_OUT.open("w", encoding="utf-8") as f:
        for s in train:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    with EVAL_OUT.open("w", encoding="utf-8") as f:
        for s in eval_set:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    
    # ────────────────────────────
    # 분포 리포트
    # ────────────────────────────
    def dist(samples_, key_fn):
        return dict(Counter(key_fn(s) for s in samples_).most_common())
    
    print(f"\n{'='*60}")
    print("  Select 결과")
    print(f"{'='*60}")
    print(f"Train: {len(train)}")
    print(f"Eval:  {len(eval_set)}")
    print(f"Total: {len(train) + len(eval_set)}")
    
    print(f"\n=== Train 분포 ===")
    print(f"voice: {dist(train, lambda s: s['voice'])}")
    print(f"qtype: {dist(train, lambda s: s['question_type'])}")
    print(f"pattern: {dist(train, lambda s: s['response_pattern'])}")
    print(f"use_case: {dist(train, lambda s: s['use_case'])}")
    print(f"difficulty: {dist(train, lambda s: s['difficulty'])}")
    print(f"source: {dist(train, lambda s: s['source_ref'].split('_')[0])}")
    print(f"grade: {dist(train, lambda s: s['grade'])}")
    
    print(f"\n=== Eval 분포 ===")
    print(f"voice: {dist(eval_set, lambda s: s['voice'])}")
    print(f"qtype: {dist(eval_set, lambda s: s['question_type'])}")
    print(f"pattern: {dist(eval_set, lambda s: s['response_pattern'])}")
    print(f"use_case: {dist(eval_set, lambda s: s['use_case'])}")
    print(f"grade: {dist(eval_set, lambda s: s['grade'])}")
    
    train_avg = sum(s["normalized_score"] for s in train) / max(len(train), 1)
    eval_avg = sum(s["normalized_score"] for s in eval_set) / max(len(eval_set), 1)
    print(f"\n평균 점수:  train {train_avg:.3f}  /  eval {eval_avg:.3f}")
    
    print(f"\n출력:")
    print(f"  {TRAIN_OUT}")
    print(f"  {EVAL_OUT}")
    
    REPORT.write_text(json.dumps({
        "input": len(samples),
        "accepted": len(accepted),
        "rejected": rejected,
        "train": len(train),
        "eval": len(eval_set),
        "train_avg_score": train_avg,
        "eval_avg_score": eval_avg,
        "groups": len(groups),
        "small_groups_to_train": small_groups,
        "train_dist": {
            "voice": dist(train, lambda s: s["voice"]),
            "question_type": dist(train, lambda s: s["question_type"]),
            "response_pattern": dist(train, lambda s: s["response_pattern"]),
            "use_case": dist(train, lambda s: s["use_case"]),
            "difficulty": dist(train, lambda s: s["difficulty"]),
            "source": dist(train, lambda s: s["source_ref"].split("_")[0]),
            "grade": dist(train, lambda s: s["grade"]),
        },
        "eval_dist": {
            "voice": dist(eval_set, lambda s: s["voice"]),
            "question_type": dist(eval_set, lambda s: s["question_type"]),
            "response_pattern": dist(eval_set, lambda s: s["response_pattern"]),
            "use_case": dist(eval_set, lambda s: s["use_case"]),
            "grade": dist(eval_set, lambda s: s["grade"]),
        },
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  {REPORT}")


if __name__ == "__main__":
    main()