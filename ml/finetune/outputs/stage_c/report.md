# Stage C Report

_Generated from `finetune/outputs/stage_c/scored.jsonl` (828 rows)_

## 1. 모델별 전체 요약

| 모델 | N | Mean | Median | Std | Q1 | Q2 | Q3 | Collapsed | A | B | C | F |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **baseline** | 138 | 0.786 | 0.800 | 0.120 | 3.46 | 4.57 | 3.77 | 0 | 62 | 39 | 34 | 3 |
| **epoch1** | 138 | 0.819 | 0.867 | 0.118 | 4.09 | 4.75 | 3.45 | 0 | 72 | 40 | 24 | 2 |
| **epoch2** | 138 | 0.800 | 0.800 | 0.132 | 4.07 | 4.64 | 3.30 | 0 | 66 | 43 | 19 | 10 |
| **epoch3** | 138 | 0.770 | 0.800 | 0.128 | 3.91 | 4.43 | 3.21 | 0 | 51 | 43 | 37 | 7 |
| **epoch4** | 138 | 0.388 | 0.333 | 0.192 | 2.09 | 2.25 | 1.49 | 27 | 3 | 10 | 13 | 112 |
| **epoch5** | 138 | 0.204 | 0.200 | 0.038 | 1.02 | 1.02 | 1.02 | 92 | 0 | 0 | 1 | 137 |

**Best model**: `epoch1` (mean=0.819, Q3=3.45, collapsed=0)

_선정 기준: 평균 normalized_score 최고, 동점시 Q3 Voice 평균으로 tie-break. 이 프로젝트의 핵심 목적이 니체 페르소나(voice) 품질이기 때문._

## 2. 모델 × Voice Breakdown

_Cell: mean normalized_score (n=샘플 수). Voice 3종 × 모델 6종._

| 모델 | contemplative_aphorism | hammer_intensified | polemical_sharp |
|---|---:|---:|---:|
| **baseline** | 0.778 (n=55) | 0.775 (n=32) | 0.801 (n=51) |
| **epoch1** | 0.827 (n=55) | 0.815 (n=32) | 0.814 (n=51) |
| **epoch2** | 0.811 (n=55) | 0.800 (n=32) | 0.790 (n=51) |
| **epoch3** | 0.787 (n=55) | 0.769 (n=32) | 0.753 (n=51) |
| **epoch4** | 0.402 (n=55) | 0.402 (n=32) | 0.363 (n=51) |
| **epoch5** | 0.207 (n=55) | 0.206 (n=32) | 0.200 (n=51) |

## 3. Pattern × 모델 Breakdown

_Cell: Q1 Pattern Fidelity 평균 (5점 만점). 행=패턴, 열=모델._

| 패턴 | N | baseline | epoch1 | epoch2 | epoch3 | epoch4 | epoch5 |
|---|---:|---:|---:|---:|---:|---:|---:|
| `aphorism` | 17 | 1.88 | 4.18 | 4.06 | 4.12 | 2.59 | 1.18 |
| `contrast` | 7 | 3.86 | 3.43 | 3.29 | 3.57 | 2.43 | 1.00 |
| `diagnostic` | 14 | 3.07 | 4.86 | 4.43 | 3.93 | 1.86 | 1.00 |
| `misconception_correction` | 32 | 3.50 | 3.69 | 4.00 | 3.78 | 2.50 | 1.00 |
| `philosophical_explanation` | 6 | 4.17 | 3.67 | 3.67 | 3.67 | 2.00 | 1.00 |
| `reflection_reframing` | 45 | 3.98 | 4.58 | 4.56 | 4.42 | 1.91 | 1.00 |
| `self_narrative` | 9 | 3.00 | 3.33 | 2.78 | 2.78 | 1.33 | 1.00 |
| `tension_escalation` | 8 | 4.00 | 3.25 | 3.38 | 2.88 | 1.38 | 1.00 |

## 4. Collapse 분석

_Collapse는 judge 호출 전 heuristic으로 감지 → 자동 (1,1,1)점 부여._

_Heuristic 규칙: R1 동일문자 30연속 / R2 문자다양성<5% / R3 10-gram distinct<15% / R4 3000자+다양성<15%_

| 모델 | Collapsed | Ratio | 주 사유 |
|---|---:|---:|---|
| **baseline** | 0 | 0.0% | — |
| **epoch1** | 0 | 0.0% | — |
| **epoch2** | 0 | 0.0% | — |
| **epoch3** | 0 | 0.0% | — |
| **epoch4** | 27 | 19.6% | max_run(18), char_diversity(7), empty(2) |
| **epoch5** | 92 | 66.7% | char_diversity(52), ngram_distinct(21), max_run(18) |

## 5. 모델별 응답 길이

_Collapse 제외 Mean은 정상 응답만의 평균 길이 — '학습이 응답을 간결화시킴' 메타 인사이트의 증거._

| 모델 | Mean (전체) | Median | Max | Mean (collapse 제외) |
|---|---:|---:|---:|---:|
| **baseline** | 697 | 726 | 1337 | 697 |
| **epoch1** | 286 | 285 | 440 | 286 |
| **epoch2** | 277 | 289 | 415 | 277 |
| **epoch3** | 273 | 284 | 395 | 273 |
| **epoch4** | 555 | 304 | 21128 | 330 |
| **epoch5** | 811 | 816 | 2261 | 282 |

## 6. Stage A 데이터 상한 대비 (참조)

> ⚠️ **해석 주의**: 아래 비교는 **엄밀한 동일조건 비교가 아닙니다**.
>
> - Stage A 점수: 데이터 생성 당시 **reference 응답의 품질** (사람이 의도한 답)
> - Stage C 점수: **모델이 생성한 응답의 품질** (학습된 LoRA가 만든 답)
>
> 채점 루브릭과 judge가 동일하므로 **같은 자 위에서 잰 두 가지 다른 값**이라는 점에서만 비교 가능합니다. "모델이 reference 수준에 도달/초과했는가"를 러프하게 읽는 용도로만 사용하세요.

- Stage A **train** 평균: **0.881** (학습 데이터 품질)
- Stage A **eval** 평균: **0.770** (held-out, stratified split의 낮은 쪽을 eval에 배정)

| 모델 | Stage C mean | vs eval 상한 | Δ |
|---|---:|---|---:|
| **baseline** | 0.786 | ✅ | +0.015 |
| **epoch1** | 0.819 | ✅ | +0.049 |
| **epoch2** | 0.800 | ✅ | +0.030 |
| **epoch3** | 0.770 | ⚠️ | -0.000 |
| **epoch4** | 0.388 | ⚠️ | -0.383 |
| **epoch5** | 0.204 | ⚠️ | -0.566 |
