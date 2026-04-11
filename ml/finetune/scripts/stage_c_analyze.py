"""Stage C — Analyze: Stage C 채점 결과를 다각도로 분석하는 다목적 도구.

12개 서브커맨드를 통해 voice/pattern/length/reason 등 다양한 축으로 분석.
모든 분석은 4가지 포맷(text/markdown/json/csv) 출력 지원.

입력:
  - finetune/outputs/stage_c/scored.jsonl       (점수만)
  - finetune/outputs/stage_c/scored_cot.jsonl   (CoT, reasoning 포함)

기본 입력: scored_cot.jsonl (reason 분석에 필요). --input으로 변경 가능.

출력:
  - 콘솔 출력 (--format text/markdown/json/csv)
  - 또는 finetune/outputs/stage_c/analysis/{subcommand}.{ext} (--format all)

사용법:
  python finetune/scripts/stage_c_analyze.py --help                       # 전체 명령 목록
  python finetune/scripts/stage_c_analyze.py voice-defect                 # voice별 결함률
  python finetune/scripts/stage_c_analyze.py voice-defect --format all    # 4 포맷 저장
  python finetune/scripts/stage_c_analyze.py reason-search --keyword 어미
  python finetune/scripts/stage_c_analyze.py sample-deepdive --sample-id nietzsche_000489

서브커맨드 12개:
   1. voice-defect          voice별 Q3 결함률 (Q3≤3 비율)
   2. ending-top             Q3 reason에서 인용된 어미 top N
   3. reason-search          키워드로 reason 검색
   4. compare-modes          점수만 vs CoT 모델별 비교
   5. collapse-detail        collapse 사유 분포 + 길이 통계
   6. q-distribution         Q1/Q2/Q3 점수 분포
   7. best-worst             모델별 최고/최저 점수 N개 + reason
   8. per-pattern-defect     pattern × 모델 × Q1 분포
   9. length-vs-score        응답 길이 vs normalized_score 상관
  10. agreement              점수만 vs CoT 점수 일치도
  11. voice-pattern-cross    voice × pattern 매트릭스
  12. sample-deepdive        한 샘플의 6개 모델 응답 + reason 비교
"""
import argparse
import csv
import io
import json
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path

# ════════════════════════════════════════════════════════════════════
# 경로
# ════════════════════════════════════════════════════════════════════

SCRIPT_DIR = Path(__file__).resolve().parent
ML_ROOT = SCRIPT_DIR.parent.parent
STAGE_C_DIR = ML_ROOT / "finetune/outputs/stage_c"
ANALYSIS_DIR = STAGE_C_DIR / "analysis"

DEFAULT_INPUT = STAGE_C_DIR / "scored_cot.jsonl"
SCORED_PLAIN = STAGE_C_DIR / "scored.jsonl"
SCORED_COT = STAGE_C_DIR / "scored_cot.jsonl"

MODEL_ORDER = ["baseline", "epoch1", "epoch2", "epoch3", "epoch4", "epoch5"]
TRAINED_MODELS = ["epoch1", "epoch2", "epoch3"]   # collapse 시작 전, 정상 학습 모델


# ════════════════════════════════════════════════════════════════════
# 공통 유틸
# ════════════════════════════════════════════════════════════════════

def load_rows(path: Path) -> list[dict]:
    if not path.exists():
        raise SystemExit(f"입력 없음: {path}")
    return [json.loads(l) for l in path.open(encoding="utf-8")]


def safe_mean(values):
    return statistics.mean(values) if values else 0.0


def model_sort_key(model: str) -> int:
    try:
        return MODEL_ORDER.index(model)
    except ValueError:
        return 999


# ════════════════════════════════════════════════════════════════════
# 출력 렌더러 — 4 포맷
# ════════════════════════════════════════════════════════════════════

class Table:
    """분석 결과를 담는 범용 컨테이너. 4 포맷으로 변환 가능."""

    def __init__(self, title: str, headers: list[str], rows: list[list],
                 notes: list[str] = None):
        self.title = title
        self.headers = headers
        self.rows = rows
        self.notes = notes or []

    def to_text(self) -> str:
        """ASCII 표."""
        if not self.rows:
            return f"{self.title}\n(no data)"

        # 컬럼 너비 계산
        all_rows = [self.headers] + [[str(c) for c in r] for r in self.rows]
        widths = [max(len(str(row[i])) for row in all_rows) for i in range(len(self.headers))]

        sep = "  "
        lines = [f"== {self.title} =="]
        # header
        lines.append(sep.join(str(h).ljust(w) for h, w in zip(self.headers, widths)))
        lines.append(sep.join("-" * w for w in widths))
        # rows
        for row in self.rows:
            lines.append(sep.join(str(c).ljust(w) for c, w in zip(row, widths)))
        for n in self.notes:
            lines.append(f"\n# {n}")
        return "\n".join(lines)

    def to_markdown(self) -> str:
        if not self.rows:
            return f"## {self.title}\n\n_(no data)_"
        lines = [f"## {self.title}", ""]
        lines.append("| " + " | ".join(str(h) for h in self.headers) + " |")
        lines.append("|" + "|".join("---" for _ in self.headers) + "|")
        for row in self.rows:
            lines.append("| " + " | ".join(str(c) for c in row) + " |")
        for n in self.notes:
            lines.append(f"\n_{n}_")
        return "\n".join(lines)

    def to_json(self) -> str:
        return json.dumps({
            "title": self.title,
            "headers": self.headers,
            "rows": self.rows,
            "notes": self.notes,
        }, ensure_ascii=False, indent=2)

    def to_csv(self) -> str:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(self.headers)
        for row in self.rows:
            writer.writerow(row)
        return buf.getvalue()


def emit(table: Table, fmt: str, subcommand: str):
    """포맷에 따라 콘솔 출력 또는 파일 저장."""
    if fmt == "text":
        print(table.to_text())
    elif fmt == "markdown":
        print(table.to_markdown())
    elif fmt == "json":
        print(table.to_json())
    elif fmt == "csv":
        print(table.to_csv())
    elif fmt == "all":
        ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
        for ext, content in [
            ("txt", table.to_text()),
            ("md", table.to_markdown()),
            ("json", table.to_json()),
            ("csv", table.to_csv()),
        ]:
            path = ANALYSIS_DIR / f"{subcommand}.{ext}"
            path.write_text(content, encoding="utf-8")
        print(f"저장: {ANALYSIS_DIR}/{subcommand}.{{txt,md,json,csv}}")
        # 콘솔에는 text 버전도 출력
        print()
        print(table.to_text())
    else:
        raise SystemExit(f"unknown format: {fmt}")


# ════════════════════════════════════════════════════════════════════
# 1. voice-defect
# ════════════════════════════════════════════════════════════════════

def cmd_voice_defect(args):
    """voice별 Q3 결함률 (Q3 ≤ 3 비율)."""
    rows = load_rows(args.input)
    targets = args.models.split(",") if args.models else TRAINED_MODELS
    threshold = args.threshold

    by_voice = defaultdict(lambda: {"total": 0, "low": 0, "q3_sum": 0})
    for r in rows:
        if r["model_tag"] not in targets or r.get("collapsed"):
            continue
        if not r.get("q_scores"):
            continue
        v = r["voice"]
        q3 = r["q_scores"]["q3"]
        by_voice[v]["total"] += 1
        by_voice[v]["q3_sum"] += q3
        if q3 <= threshold:
            by_voice[v]["low"] += 1

    table_rows = []
    for voice in sorted(by_voice):
        d = by_voice[voice]
        if d["total"] == 0:
            continue
        rate = d["low"] / d["total"] * 100
        avg_q3 = d["q3_sum"] / d["total"]
        table_rows.append([
            voice, d["total"], d["low"],
            f"{rate:.1f}%", f"{avg_q3:.2f}",
        ])

    table = Table(
        title=f"Voice별 Q3 결함률 (Q3 ≤ {threshold}, models={','.join(targets)})",
        headers=["voice", "n", f"Q3≤{threshold}", "rate", "avg_Q3"],
        rows=table_rows,
        notes=[
            "Collapse 응답은 제외.",
            "Q3 = Voice & Persona axis (5점 만점, 3점이 평균).",
        ],
    )
    emit(table, args.format, "voice_defect")


# ════════════════════════════════════════════════════════════════════
# 2. ending-top
# ════════════════════════════════════════════════════════════════════

def cmd_ending_top(args):
    """Q3 reason에서 인용된 어미 top N."""
    rows = load_rows(args.input)
    targets = args.models.split(",") if args.models else TRAINED_MODELS

    # Q3 reason에서 따옴표로 인용된 짧은 패턴 추출
    # 예: '~인 것이다', '~입니다', '~다'
    pattern = re.compile(r"['\"]([~∼][^'\"]{0,15})['\"]")
    counter = Counter()

    for r in rows:
        if r["model_tag"] not in targets or r.get("collapsed"):
            continue
        if not r.get("q_reasons"):
            continue
        q3 = r["q_reasons"].get("q3", "")
        for m in pattern.findall(q3):
            counter[m.strip()] += 1

    top = counter.most_common(args.top)
    table_rows = [[i + 1, ending, count] for i, (ending, count) in enumerate(top)]

    table = Table(
        title=f"Q3 reason 내 인용 어미 Top {args.top} (models={','.join(targets)})",
        headers=["#", "ending", "count"],
        rows=table_rows,
        notes=[
            "정규식: 따옴표 안의 ~로 시작하는 1~15자.",
            "정확/오답 구분 안 함. 칭찬·지적 두 맥락 모두 포함.",
        ],
    )
    emit(table, args.format, "ending_top")


# ════════════════════════════════════════════════════════════════════
# 3. reason-search
# ════════════════════════════════════════════════════════════════════

def cmd_reason_search(args):
    """키워드로 q_reasons 검색."""
    if not args.keyword:
        raise SystemExit("--keyword 필수")
    rows = load_rows(args.input)
    axes = args.axes.split(",") if args.axes else ["q1", "q2", "q3"]
    targets = args.models.split(",") if args.models else MODEL_ORDER

    matches = []
    for r in rows:
        if r["model_tag"] not in targets:
            continue
        if not r.get("q_reasons"):
            continue
        for axis in axes:
            reason = r["q_reasons"].get(axis, "")
            if args.keyword in reason:
                matches.append([
                    r["model_tag"],
                    r["sample_id"],
                    r.get("voice", ""),
                    axis,
                    r["q_scores"][axis] if r.get("q_scores") else "—",
                    reason[:200] + ("..." if len(reason) > 200 else ""),
                ])
                if args.limit and len(matches) >= args.limit:
                    break
        if args.limit and len(matches) >= args.limit:
            break

    table = Table(
        title=f"Reason 검색: '{args.keyword}' (axes={','.join(axes)})",
        headers=["model", "sample_id", "voice", "axis", "score", "reason"],
        rows=matches,
        notes=[f"매칭 수: {len(matches)}"],
    )
    emit(table, args.format, "reason_search")


# ════════════════════════════════════════════════════════════════════
# 4. compare-modes
# ════════════════════════════════════════════════════════════════════

def cmd_compare_modes(args):
    """점수만(scored.jsonl) vs CoT(scored_cot.jsonl) 모델별 비교."""
    plain = {(r["sample_id"], r["model_tag"]): r for r in load_rows(SCORED_PLAIN)}
    cot = {(r["sample_id"], r["model_tag"]): r for r in load_rows(SCORED_COT)}

    models = sorted({k[1] for k in plain.keys() | cot.keys()}, key=model_sort_key)

    rows = []
    for model in models:
        plain_scores = [r["normalized_score"] for k, r in plain.items() if k[1] == model]
        cot_scores = [r["normalized_score"] for k, r in cot.items() if k[1] == model]
        plain_q3 = [r["q_scores"]["q3"] for k, r in plain.items()
                    if k[1] == model and r.get("q_scores")]
        cot_q3 = [r["q_scores"]["q3"] for k, r in cot.items()
                  if k[1] == model and r.get("q_scores")]

        rows.append([
            model,
            len(plain_scores),
            f"{safe_mean(plain_scores):.3f}",
            f"{safe_mean(cot_scores):.3f}",
            f"{safe_mean(cot_scores) - safe_mean(plain_scores):+.3f}",
            f"{safe_mean(plain_q3):.2f}",
            f"{safe_mean(cot_q3):.2f}",
            f"{safe_mean(cot_q3) - safe_mean(plain_q3):+.2f}",
        ])

    table = Table(
        title="점수만 vs CoT 모드 비교",
        headers=["model", "n", "plain_mean", "cot_mean", "Δmean",
                 "plain_Q3", "cot_Q3", "ΔQ3"],
        rows=rows,
        notes=[
            "Δ < 0 = CoT가 더 엄격함.",
            "CoT가 reasoning을 강제하면 judge가 rubric을 더 정직하게 적용.",
        ],
    )
    emit(table, args.format, "compare_modes")


# ════════════════════════════════════════════════════════════════════
# 5. collapse-detail
# ════════════════════════════════════════════════════════════════════

def cmd_collapse_detail(args):
    """collapse 사유 분포 + 길이 통계."""
    rows = load_rows(args.input)

    by_model = defaultdict(lambda: {
        "total": 0, "collapsed": 0,
        "reasons": Counter(),
        "lens": [], "collapsed_lens": [],
    })
    for r in rows:
        m = r["model_tag"]
        by_model[m]["total"] += 1
        by_model[m]["lens"].append(r["generated_len"])
        if r.get("collapsed"):
            by_model[m]["collapsed"] += 1
            by_model[m]["collapsed_lens"].append(r["generated_len"])
            reason = r.get("collapse_reason", "").split("=")[0]
            by_model[m]["reasons"][reason] += 1

    table_rows = []
    for model in sorted(by_model, key=model_sort_key):
        d = by_model[model]
        if d["collapsed"] == 0:
            reason_str = "—"
            coll_max = "—"
            coll_med = "—"
        else:
            reason_str = ", ".join(f"{k}({v})" for k, v in d["reasons"].most_common(3))
            coll_max = max(d["collapsed_lens"])
            coll_med = int(statistics.median(d["collapsed_lens"]))
        table_rows.append([
            model, d["total"], d["collapsed"],
            f"{d['collapsed']/d['total']*100:.1f}%",
            reason_str, coll_med, coll_max,
        ])

    table = Table(
        title="Collapse 분석 (heuristic 사유 + 길이)",
        headers=["model", "n", "collapsed", "rate", "reasons",
                 "coll_med_len", "coll_max_len"],
        rows=table_rows,
        notes=[
            "Collapse heuristic R1: max_run / R2: char_diversity / R3: ngram_distinct / R4: long_low_diversity.",
            "사유는 epoch당 top 3.",
        ],
    )
    emit(table, args.format, "collapse_detail")


# ════════════════════════════════════════════════════════════════════
# 6. q-distribution
# ════════════════════════════════════════════════════════════════════

def cmd_q_distribution(args):
    """Q1/Q2/Q3 점수 분포."""
    rows = load_rows(args.input)
    targets = args.models.split(",") if args.models else MODEL_ORDER

    table_rows = []
    for model in sorted(set(r["model_tag"] for r in rows), key=model_sort_key):
        if model not in targets:
            continue
        items = [r for r in rows if r["model_tag"] == model and r.get("q_scores")]
        if not items:
            continue
        for axis in ["q1", "q2", "q3"]:
            counts = Counter(r["q_scores"][axis] for r in items)
            row = [model, axis.upper()]
            for score in [1, 2, 3, 4, 5]:
                n = counts.get(score, 0)
                pct = n / len(items) * 100
                row.append(f"{n}({pct:.0f}%)")
            row.append(f"{safe_mean([r['q_scores'][axis] for r in items]):.2f}")
            table_rows.append(row)

    table = Table(
        title="Q1/Q2/Q3 점수 분포 (모델 × axis)",
        headers=["model", "axis", "1", "2", "3", "4", "5", "mean"],
        rows=table_rows,
        notes=["각 셀: count(percent)."],
    )
    emit(table, args.format, "q_distribution")


# ════════════════════════════════════════════════════════════════════
# 7. best-worst
# ════════════════════════════════════════════════════════════════════

def cmd_best_worst(args):
    """모델별 최고/최저 N개 샘플 + reason."""
    rows = load_rows(args.input)
    targets = args.models.split(",") if args.models else MODEL_ORDER
    n = args.top

    table_rows = []
    for model in sorted(set(r["model_tag"] for r in rows), key=model_sort_key):
        if model not in targets:
            continue
        items = [r for r in rows if r["model_tag"] == model and r.get("q_scores")]
        if not items:
            continue
        items_sorted = sorted(items, key=lambda r: r["normalized_score"])

        for label, slice_ in [("WORST", items_sorted[:n]),
                              ("BEST", items_sorted[-n:][::-1])]:
            for r in slice_:
                reason = ""
                if r.get("q_reasons"):
                    reason = r["q_reasons"].get("q3", "")[:120]
                table_rows.append([
                    model, label, r["sample_id"], r.get("voice", ""),
                    r["q_scores"]["q1"], r["q_scores"]["q2"], r["q_scores"]["q3"],
                    f"{r['normalized_score']:.3f}",
                    reason,
                ])

    table = Table(
        title=f"모델별 Best/Worst {n}개 샘플",
        headers=["model", "kind", "sample_id", "voice",
                 "Q1", "Q2", "Q3", "mean", "q3_reason (truncated)"],
        rows=table_rows,
        notes=["normalized_score 기준."],
    )
    emit(table, args.format, "best_worst")


# ════════════════════════════════════════════════════════════════════
# 8. per-pattern-defect
# ════════════════════════════════════════════════════════════════════

def cmd_per_pattern_defect(args):
    """pattern × 모델 × Q1 평균 (어느 패턴이 학습으로 가장 개선/저하)."""
    rows = load_rows(args.input)

    patterns = sorted({r["response_pattern"] for r in rows
                       if r.get("response_pattern")})
    models = sorted({r["model_tag"] for r in rows}, key=model_sort_key)

    table_rows = []
    for pattern in patterns:
        row = [pattern]
        # 각 모델의 평균 Q1
        for model in models:
            items = [r for r in rows
                     if r.get("response_pattern") == pattern
                     and r["model_tag"] == model
                     and r.get("q_scores")]
            if items:
                row.append(f"{safe_mean([r['q_scores']['q1'] for r in items]):.2f}")
            else:
                row.append("—")
        # baseline 대비 epoch1 개선
        baseline_items = [r for r in rows
                          if r.get("response_pattern") == pattern
                          and r["model_tag"] == "baseline"
                          and r.get("q_scores")]
        epoch1_items = [r for r in rows
                        if r.get("response_pattern") == pattern
                        and r["model_tag"] == "epoch1"
                        and r.get("q_scores")]
        if baseline_items and epoch1_items:
            base = safe_mean([r["q_scores"]["q1"] for r in baseline_items])
            ep1 = safe_mean([r["q_scores"]["q1"] for r in epoch1_items])
            delta = ep1 - base
            row.append(f"{delta:+.2f}")
        else:
            row.append("—")

        # 샘플 수 (모델당 동일)
        n = len([r for r in rows
                 if r.get("response_pattern") == pattern
                 and r["model_tag"] == "baseline"])
        row.insert(1, n)
        table_rows.append(row)

    table = Table(
        title="Pattern × 모델 Q1 평균",
        headers=["pattern", "n"] + models + ["Δ(ep1−base)"],
        rows=table_rows,
        notes=[
            "Q1 = Pattern Fidelity (5점 만점).",
            "Δ가 클수록 학습이 그 패턴을 강하게 가르침.",
        ],
    )
    emit(table, args.format, "per_pattern_defect")


# ════════════════════════════════════════════════════════════════════
# 9. length-vs-score
# ════════════════════════════════════════════════════════════════════

def cmd_length_vs_score(args):
    """응답 길이 vs normalized_score 상관 (length bias 진단)."""
    rows = load_rows(args.input)

    table_rows = []
    for model in sorted({r["model_tag"] for r in rows}, key=model_sort_key):
        items = [r for r in rows
                 if r["model_tag"] == model
                 and r.get("q_scores")
                 and not r.get("collapsed")]
        if len(items) < 2:
            continue
        lens = [r["generated_len"] for r in items]
        scores = [r["normalized_score"] for r in items]

        # Pearson correlation
        n = len(lens)
        mean_l, mean_s = statistics.mean(lens), statistics.mean(scores)
        cov = sum((l - mean_l) * (s - mean_s) for l, s in zip(lens, scores)) / n
        std_l = statistics.stdev(lens) if len(lens) > 1 else 0
        std_s = statistics.stdev(scores) if len(scores) > 1 else 0
        corr = cov / (std_l * std_s) if std_l * std_s > 0 else 0

        table_rows.append([
            model, n,
            int(safe_mean(lens)),
            int(statistics.median(lens)),
            f"{safe_mean(scores):.3f}",
            f"{corr:+.3f}",
        ])

    table = Table(
        title="응답 길이 vs Score 상관 (collapse 제외)",
        headers=["model", "n", "mean_len", "median_len", "mean_score", "pearson_r"],
        rows=table_rows,
        notes=[
            "Pearson r > 0.3 = length bias 의심 (긴 응답이 점수 높음).",
            "r ≈ 0 = length bias 없음.",
        ],
    )
    emit(table, args.format, "length_vs_score")


# ════════════════════════════════════════════════════════════════════
# 10. agreement
# ════════════════════════════════════════════════════════════════════

def cmd_agreement(args):
    """점수만 vs CoT 점수 일치도 (sample 단위)."""
    plain = {(r["sample_id"], r["model_tag"]): r for r in load_rows(SCORED_PLAIN)}
    cot = {(r["sample_id"], r["model_tag"]): r for r in load_rows(SCORED_COT)}

    common = set(plain.keys()) & set(cot.keys())

    table_rows = []
    for model in MODEL_ORDER:
        keys = [k for k in common if k[1] == model]
        if not keys:
            continue
        diffs = []
        same_normalized = 0
        for k in keys:
            p = plain[k]
            c = cot[k]
            if not p.get("q_scores") or not c.get("q_scores"):
                continue
            diff = c["normalized_score"] - p["normalized_score"]
            diffs.append(diff)
            if abs(diff) < 0.001:
                same_normalized += 1

        if not diffs:
            continue
        abs_diffs = [abs(d) for d in diffs]
        table_rows.append([
            model, len(diffs),
            same_normalized,
            f"{same_normalized/len(diffs)*100:.1f}%",
            f"{safe_mean(diffs):+.3f}",
            f"{safe_mean(abs_diffs):.3f}",
            f"{max(abs_diffs):.3f}",
        ])

    table = Table(
        title="점수만 vs CoT 일치도 (sample 단위)",
        headers=["model", "n", "same", "same_rate",
                 "mean_Δ", "mean_|Δ|", "max_|Δ|"],
        rows=table_rows,
        notes=[
            "Δ = CoT − plain. 음수는 CoT가 더 낮은 점수.",
            "같은 judge·temperature이지만 reasoning 강제 여부에 따라 점수가 흔들림.",
            "mean_|Δ| 작을수록 두 모드가 일치.",
        ],
    )
    emit(table, args.format, "agreement")


# ════════════════════════════════════════════════════════════════════
# 11. voice-pattern-cross
# ════════════════════════════════════════════════════════════════════

def cmd_voice_pattern_cross(args):
    """voice × pattern 매트릭스."""
    rows = load_rows(args.input)
    target_model = args.model

    items = [r for r in rows
             if r["model_tag"] == target_model
             and r.get("q_scores")
             and not r.get("collapsed")]

    voices = sorted({r["voice"] for r in items if r.get("voice")})
    patterns = sorted({r["response_pattern"] for r in items if r.get("response_pattern")})

    table_rows = []
    for pattern in patterns:
        row = [pattern]
        for voice in voices:
            cell_items = [r for r in items
                          if r.get("response_pattern") == pattern
                          and r.get("voice") == voice]
            if not cell_items:
                row.append("—")
            else:
                mean = safe_mean([r["normalized_score"] for r in cell_items])
                row.append(f"{mean:.2f} (n={len(cell_items)})")
        table_rows.append(row)

    table = Table(
        title=f"Voice × Pattern 매트릭스 (model={target_model})",
        headers=["pattern"] + voices,
        rows=table_rows,
        notes=[
            "각 셀: mean normalized_score (n=샘플 수).",
            "어떤 voice의 어떤 pattern이 특히 약한지 진단.",
        ],
    )
    emit(table, args.format, "voice_pattern_cross")


# ════════════════════════════════════════════════════════════════════
# 12. sample-deepdive
# ════════════════════════════════════════════════════════════════════

def cmd_sample_deepdive(args):
    """한 샘플의 6개 모델 응답 + reason 비교."""
    if not args.sample_id:
        raise SystemExit("--sample-id 필수 (예: nietzsche_000489)")

    cot_rows = load_rows(SCORED_COT)
    sample_rows = [r for r in cot_rows if r["sample_id"] == args.sample_id]
    if not sample_rows:
        raise SystemExit(f"sample_id 없음: {args.sample_id}")

    # 메타정보
    meta = sample_rows[0]
    print(f"== Sample: {args.sample_id} ==")
    print(f"voice: {meta.get('voice')}")
    print(f"pattern: {meta.get('response_pattern')}")
    print(f"question_type: {meta.get('question_type')}")
    print()

    # 응답 본문은 stage_b에서 가져와야 함
    responses_path = ML_ROOT / "finetune/outputs/stage_b/responses.jsonl"
    response_by_model = {}
    if responses_path.exists():
        for line in responses_path.open(encoding="utf-8"):
            r = json.loads(line)
            if r["sample_id"] == args.sample_id:
                response_by_model[r["model_tag"]] = r

    # 표 형태 데이터
    table_rows = []
    for r in sorted(sample_rows, key=lambda x: model_sort_key(x["model_tag"])):
        model = r["model_tag"]
        scores = r.get("q_scores", {})
        reasons = r.get("q_reasons") or {}
        gen = response_by_model.get(model, {}).get("generated", "")[:300]

        table_rows.append([
            model,
            scores.get("q1", "—"),
            scores.get("q2", "—"),
            scores.get("q3", "—"),
            f"{r.get('normalized_score', 0):.3f}",
            "✓" if r.get("collapsed") else "",
            r.get("generated_len", "—"),
            reasons.get("q3", "")[:150],
            gen,
        ])

    table = Table(
        title=f"Sample Deep Dive: {args.sample_id}",
        headers=["model", "Q1", "Q2", "Q3", "mean", "coll", "len",
                 "q3_reason (150)", "generated (300)"],
        rows=table_rows,
        notes=[
            f"voice={meta.get('voice')}, pattern={meta.get('response_pattern')}",
            "응답 본문은 stage_b/responses.jsonl에서 join.",
        ],
    )
    emit(table, args.format, f"deepdive_{args.sample_id}")


# ════════════════════════════════════════════════════════════════════
# CLI
# ════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Stage C 채점 결과 분석 다목적 도구",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT,
                        help=f"입력 jsonl (기본: {DEFAULT_INPUT.name})")
    parser.add_argument("--format", choices=["text", "markdown", "json", "csv", "all"],
                        default="text",
                        help="출력 포맷. 'all'이면 4 포맷 모두 analysis/ 디렉토리에 저장")

    sub = parser.add_subparsers(dest="cmd", required=True, metavar="SUBCOMMAND")

    # 1. voice-defect
    p = sub.add_parser("voice-defect", help="voice별 Q3 결함률")
    p.add_argument("--threshold", type=int, default=3, help="Q3 ≤ threshold = 결함")
    p.add_argument("--models", help="대상 모델 (콤마 구분, 기본: epoch1,epoch2,epoch3)")
    p.set_defaults(func=cmd_voice_defect)

    # 2. ending-top
    p = sub.add_parser("ending-top", help="Q3 reason의 인용 어미 top N")
    p.add_argument("--top", type=int, default=20)
    p.add_argument("--models", help="대상 모델 (콤마 구분, 기본: epoch1,epoch2,epoch3)")
    p.set_defaults(func=cmd_ending_top)

    # 3. reason-search
    p = sub.add_parser("reason-search", help="키워드로 reason 검색")
    p.add_argument("--keyword", required=True)
    p.add_argument("--axes", help="검색 축 (q1,q2,q3 콤마, 기본: 전체)")
    p.add_argument("--models", help="대상 모델 (콤마 구분, 기본: 전체)")
    p.add_argument("--limit", type=int, default=50, help="최대 결과 수")
    p.set_defaults(func=cmd_reason_search)

    # 4. compare-modes
    p = sub.add_parser("compare-modes", help="점수만 vs CoT 모델별 비교")
    p.set_defaults(func=cmd_compare_modes)

    # 5. collapse-detail
    p = sub.add_parser("collapse-detail", help="collapse 사유 + 길이 분석")
    p.set_defaults(func=cmd_collapse_detail)

    # 6. q-distribution
    p = sub.add_parser("q-distribution", help="Q1/Q2/Q3 점수 분포")
    p.add_argument("--models", help="대상 모델 (콤마 구분, 기본: 전체)")
    p.set_defaults(func=cmd_q_distribution)

    # 7. best-worst
    p = sub.add_parser("best-worst", help="모델별 최고/최저 N개")
    p.add_argument("--top", type=int, default=3)
    p.add_argument("--models", help="대상 모델 (콤마 구분, 기본: 전체)")
    p.set_defaults(func=cmd_best_worst)

    # 8. per-pattern-defect
    p = sub.add_parser("per-pattern-defect", help="pattern × 모델 Q1 평균")
    p.set_defaults(func=cmd_per_pattern_defect)

    # 9. length-vs-score
    p = sub.add_parser("length-vs-score", help="응답 길이 vs score 상관")
    p.set_defaults(func=cmd_length_vs_score)

    # 10. agreement
    p = sub.add_parser("agreement", help="점수만 vs CoT 일치도")
    p.set_defaults(func=cmd_agreement)

    # 11. voice-pattern-cross
    p = sub.add_parser("voice-pattern-cross", help="voice × pattern 매트릭스")
    p.add_argument("--model", default="epoch1", help="기본 epoch1")
    p.set_defaults(func=cmd_voice_pattern_cross)

    # 12. sample-deepdive
    p = sub.add_parser("sample-deepdive", help="한 샘플의 6개 모델 응답 + reason")
    p.add_argument("--sample-id", required=True, help="예: nietzsche_000489")
    p.set_defaults(func=cmd_sample_deepdive)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
