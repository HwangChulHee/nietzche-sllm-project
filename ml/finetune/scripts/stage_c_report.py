"""Stage C — Report: 채점 결과의 모델별 × breakdown 분석.

입력: finetune/outputs/stage_c/scored.jsonl
출력:
  - 콘솔 출력 (모델별 / voice별 / pattern별 / collapse / 길이 / 상한 대비)
  - finetune/outputs/stage_c/report.md  (RESULTS.md 붙여넣기용)

사용법:
  python finetune/scripts/stage_c_report.py
"""
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

# ════════════════════════════════════════════════════════════════════
# 경로 (스크립트 위치 기반 — cwd 무관)
# ════════════════════════════════════════════════════════════════════

SCRIPT_DIR = Path(__file__).resolve().parent
ML_ROOT = SCRIPT_DIR.parent.parent

INPUT = ML_ROOT / "finetune/outputs/stage_c/scored.jsonl"
OUTPUT_MD = ML_ROOT / "finetune/outputs/stage_c/report.md"

MODEL_ORDER = ["baseline", "epoch1", "epoch2", "epoch3", "epoch4", "epoch5"]


def load():
    if not INPUT.exists():
        raise SystemExit(
            f"{INPUT} 없음.\n  먼저 실행: python finetune/scripts/stage_c_score.py"
        )
    return [json.loads(l) for l in INPUT.open(encoding="utf-8")]


def agg(items):
    """정규화 점수의 평균/중앙/표준편차 요약."""
    vals = [r["normalized_score"] for r in items if r.get("q_scores")]
    if not vals:
        return {"n": 0, "mean": 0.0, "median": 0.0, "std": 0.0}
    return {
        "n": len(vals),
        "mean": statistics.mean(vals),
        "median": statistics.median(vals),
        "std": statistics.stdev(vals) if len(vals) > 1 else 0.0,
    }


def q_means(items):
    valid = [r for r in items if r.get("q_scores")]
    if not valid:
        return {"q1": 0.0, "q2": 0.0, "q3": 0.0}
    return {
        "q1": statistics.mean(r["q_scores"]["q1"] for r in valid),
        "q2": statistics.mean(r["q_scores"]["q2"] for r in valid),
        "q3": statistics.mean(r["q_scores"]["q3"] for r in valid),
    }


def section_overall(rows):
    """1. 모델별 전체 요약."""
    lines = ["## 1. 모델별 전체 요약", ""]
    lines.append(
        "| 모델 | N | Mean | Median | Std | Q1 | Q2 | Q3 | Collapsed | A | B | C | F |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")

    by_model = defaultdict(list)
    for r in rows:
        by_model[r["model_tag"]].append(r)

    summary = {}
    for model in MODEL_ORDER:
        if model not in by_model:
            continue
        items = by_model[model]
        a = agg(items)
        q = q_means(items)
        n_coll = sum(1 for r in items if r.get("collapsed"))
        g = Counter(r["grade"] for r in items)
        lines.append(
            f"| **{model}** | {a['n']} | {a['mean']:.3f} | {a['median']:.3f} | {a['std']:.3f} | "
            f"{q['q1']:.2f} | {q['q2']:.2f} | {q['q3']:.2f} | {n_coll} | "
            f"{g.get('A',0)} | {g.get('B',0)} | {g.get('C',0)} | {g.get('F',0)} |"
        )
        summary[model] = {**a, **q, "collapsed": n_coll, "grades": dict(g)}

    # Best epoch (mean 최고, 동점시 Q3 tie-breaker)
    if summary:
        best = max(summary.items(), key=lambda kv: (kv[1]["mean"], kv[1]["q3"]))
        lines.append("")
        lines.append(
            f"**Best model**: `{best[0]}` "
            f"(mean={best[1]['mean']:.3f}, "
            f"Q3={best[1]['q3']:.2f}, "
            f"collapsed={best[1]['collapsed']})"
        )
        lines.append("")
        lines.append(
            "_선정 기준: 평균 normalized_score 최고, 동점시 Q3 Voice 평균으로 tie-break. "
            "이 프로젝트의 핵심 목적이 니체 페르소나(voice) 품질이기 때문._"
        )

    lines.append("")
    return "\n".join(lines), summary


def section_voice(rows):
    """2. 모델 × voice breakdown (mean normalized_score)."""
    lines = ["## 2. 모델 × Voice Breakdown", "",
             "_Cell: mean normalized_score (n=샘플 수). Voice 3종 × 모델 6종._", ""]
    voices = sorted({r["voice"] for r in rows if r.get("voice")})
    lines.append("| 모델 | " + " | ".join(voices) + " |")
    lines.append("|---|" + "---:|" * len(voices))

    by_key = defaultdict(list)
    for r in rows:
        if r.get("voice"):
            by_key[(r["model_tag"], r["voice"])].append(r)

    for model in MODEL_ORDER:
        cells = []
        has_any = False
        for v in voices:
            items = by_key.get((model, v), [])
            if not items:
                cells.append("—")
            else:
                has_any = True
                a = agg(items)
                cells.append(f"{a['mean']:.3f} (n={a['n']})")
        if has_any:
            lines.append(f"| **{model}** | " + " | ".join(cells) + " |")

    lines.append("")
    return "\n".join(lines)


def section_pattern(rows):
    """3. Pattern × 모델 breakdown (전치 — 행=pattern, 열=모델).

    Pattern 이름이 길어서(misconception_correction 등) 가로로 쓰면 테이블이 폭주함.
    따라서 pattern을 세로로 두고 모델을 가로로 두는 전치 레이아웃 사용.
    """
    lines = ["## 3. Pattern × 모델 Breakdown", "",
             "_Cell: Q1 Pattern Fidelity 평균 (5점 만점). 행=패턴, 열=모델._", ""]

    # 헤더: 패턴 컬럼 + 모델 컬럼들
    used_models = [
        m for m in MODEL_ORDER
        if any(r["model_tag"] == m for r in rows)
    ]
    lines.append("| 패턴 | N | " + " | ".join(used_models) + " |")
    lines.append("|---|---:|" + "---:|" * len(used_models))

    # 패턴별로 행 생성
    patterns = sorted({r["response_pattern"] for r in rows if r.get("response_pattern")})
    by_key = defaultdict(list)
    for r in rows:
        if r.get("response_pattern") and r.get("q_scores"):
            by_key[(r["response_pattern"], r["model_tag"])].append(r)

    for pattern in patterns:
        # 이 패턴의 샘플 수 (모델당 동일하므로 첫 모델로 추정)
        sample_n = len([
            r for r in rows
            if r.get("response_pattern") == pattern
            and r["model_tag"] == used_models[0]
        ])

        cells = []
        for model in used_models:
            items = by_key.get((pattern, model), [])
            if not items:
                cells.append("—")
            else:
                q1 = statistics.mean(r["q_scores"]["q1"] for r in items)
                cells.append(f"{q1:.2f}")
        lines.append(f"| `{pattern}` | {sample_n} | " + " | ".join(cells) + " |")

    lines.append("")
    return "\n".join(lines)


def section_collapse(rows):
    """4. Collapse 발생 분석."""
    lines = ["## 4. Collapse 분석", "",
             "_Collapse는 judge 호출 전 heuristic으로 감지 → 자동 (1,1,1)점 부여._", "",
             "_Heuristic 규칙: R1 동일문자 30연속 / R2 문자다양성<5% / "
             "R3 10-gram distinct<15% / R4 3000자+다양성<15%_", ""]
    lines.append("| 모델 | Collapsed | Ratio | 주 사유 |")
    lines.append("|---|---:|---:|---|")

    by_model = defaultdict(list)
    for r in rows:
        by_model[r["model_tag"]].append(r)

    any_collapse = False
    for model in MODEL_ORDER:
        items = by_model.get(model, [])
        if not items:
            continue
        collapsed = [r for r in items if r.get("collapsed")]
        n = len(items)
        c = len(collapsed)
        if c == 0:
            reason_str = "—"
        else:
            any_collapse = True
            # collapse_reason의 키워드 부분만 집계 (예: "max_run=45" → "max_run")
            reasons = Counter(
                r.get("collapse_reason", "").split("=")[0]
                for r in collapsed
            )
            reason_str = ", ".join(f"{k}({v})" for k, v in reasons.most_common(3))
        lines.append(f"| **{model}** | {c} | {c/n*100:.1f}% | {reason_str} |")

    if not any_collapse:
        lines.append("")
        lines.append("_모든 모델에서 collapse 없음._")

    lines.append("")
    return "\n".join(lines)


def section_length(rows):
    """5. 응답 길이 — collapse 포함/제외 비교."""
    lines = ["## 5. 모델별 응답 길이", "",
             "_Collapse 제외 Mean은 정상 응답만의 평균 길이 — "
             "'학습이 응답을 간결화시킴' 메타 인사이트의 증거._", ""]
    lines.append("| 모델 | Mean (전체) | Median | Max | Mean (collapse 제외) |")
    lines.append("|---|---:|---:|---:|---:|")

    by_model = defaultdict(list)
    for r in rows:
        by_model[r["model_tag"]].append(r)

    for model in MODEL_ORDER:
        items = by_model.get(model, [])
        if not items:
            continue
        lens = [r["generated_len"] for r in items]
        clean = [r["generated_len"] for r in items if not r.get("collapsed")]
        clean_mean = statistics.mean(clean) if clean else 0.0
        lines.append(
            f"| **{model}** | {statistics.mean(lens):.0f} | "
            f"{statistics.median(lens):.0f} | {max(lens)} | {clean_mean:.0f} |"
        )

    lines.append("")
    return "\n".join(lines)


def section_stage_a_comparison(rows):
    """6. Stage A 데이터 상한 대비 (참조용)."""
    lines = ["## 6. Stage A 데이터 상한 대비 (참조)", ""]

    # Stage A 통계 (DATA_SPEC §1.4 고정값)
    STAGE_A_TRAIN_MEAN = 0.8806
    STAGE_A_EVAL_MEAN = 0.7705

    lines.append(
        "> ⚠️ **해석 주의**: 아래 비교는 **엄밀한 동일조건 비교가 아닙니다**.\n"
        ">\n"
        "> - Stage A 점수: 데이터 생성 당시 **reference 응답의 품질** (사람이 의도한 답)\n"
        "> - Stage C 점수: **모델이 생성한 응답의 품질** (학습된 LoRA가 만든 답)\n"
        ">\n"
        "> 채점 루브릭과 judge가 동일하므로 "
        "**같은 자 위에서 잰 두 가지 다른 값**이라는 점에서만 비교 가능합니다. "
        "\"모델이 reference 수준에 도달/초과했는가\"를 러프하게 읽는 용도로만 사용하세요."
    )
    lines.append("")
    lines.append(f"- Stage A **train** 평균: **{STAGE_A_TRAIN_MEAN:.3f}** (학습 데이터 품질)")
    lines.append(f"- Stage A **eval** 평균: **{STAGE_A_EVAL_MEAN:.3f}** "
                 f"(held-out, stratified split의 낮은 쪽을 eval에 배정)")
    lines.append("")
    lines.append("| 모델 | Stage C mean | vs eval 상한 | Δ |")
    lines.append("|---|---:|---|---:|")

    by_model = defaultdict(list)
    for r in rows:
        by_model[r["model_tag"]].append(r)

    for model in MODEL_ORDER:
        items = by_model.get(model, [])
        if not items:
            continue
        a = agg(items)
        delta = a["mean"] - STAGE_A_EVAL_MEAN
        marker = "✅" if delta >= 0 else "⚠️"
        lines.append(
            f"| **{model}** | {a['mean']:.3f} | {marker} | {delta:+.3f} |"
        )

    lines.append("")
    return "\n".join(lines)


def main():
    rows = load()
    print(f"로드: {len(rows)} rows from {INPUT}")

    sections = [
        "# Stage C Report",
        "",
        f"_Generated from `{INPUT.relative_to(ML_ROOT)}` ({len(rows)} rows)_",
        "",
    ]

    overall_md, summary = section_overall(rows)
    sections.append(overall_md)
    sections.append(section_voice(rows))
    sections.append(section_pattern(rows))
    sections.append(section_collapse(rows))
    sections.append(section_length(rows))
    sections.append(section_stage_a_comparison(rows))

    md = "\n".join(sections)

    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.write_text(md, encoding="utf-8")

    print()
    print(md)
    print()
    print(f">> 저장: {OUTPUT_MD}")


if __name__ == "__main__":
    main()
