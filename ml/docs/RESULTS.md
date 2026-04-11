# 결과물 정리

> 이 문서는 프로젝트의 모든 **결과물 위치와 핵심 수치**를 한 곳에 모은 reference입니다.
> "결과 파일이 어디 있고 어떻게 읽나"에 대한 답.
>
> 결과의 **상세 분석과 해석**은 다음 문서를 참고:
> - 데이터 통계: [DATA_SPEC.md §11](./DATA_SPEC.md)
> - 학습 분석: [SFT_STRATEGY.md §4-5](./SFT_STRATEGY.md)
> - 컴포넌트 위치: [ARCHITECTURE.md §5](./ARCHITECTURE.md)

---

## 목차

1. [한눈에 보기](#1-한눈에-보기)
2. [Stage A: 데이터 결과](#2-stage-a-데이터-결과)
3. [학습: LoRA 결과](#3-학습-lora-결과)
4. [Stage B: 응답 생성 결과](#4-stage-b-응답-생성-결과)
5. [Stage C: 채점 결과 (예정)](#5-stage-c-채점-결과-예정)
6. [결과 파일 빠른 접근](#6-결과-파일-빠른-접근)
7. [결과 검증 명령](#7-결과-검증-명령)

---

# 1. 한눈에 보기

## 1.1 모든 결과 한 페이지

| 항목 | 결과 | 위치 |
|---|---|---|
| 학습 데이터 | 2,413 샘플 | `v2_data/sft_dataset/train.jsonl` |
| 평가 데이터 (held-out) | 138 샘플 | `v2_data/sft_dataset/eval.jsonl` |
| 원전 청크 수 | 973개 (5권) | `v2_data/english_chunks/*.jsonl` |
| Stage 0.5 필터 통과율 | 928/973 (95.4%) | `v2_data/filtered/*.jsonl` (passed=True) |
| Stage A 통과율 | 91.8% (2,780 → 2,551) | `v2_data/sft_candidates/*_report.json` |
| 학습 시간 | 1시간 9분 54초 | `finetune/logs/train_31b_full.log` |
| LoRA 체크포인트 | 5개 (epoch 1~5) | `finetune/outputs/nietzsche-lora-31b/checkpoint-*` |
| LoRA HF Hub | private, 5 branches | `banzack/nietzsche-gemma4-31b-lora` |
| Best epoch (잠정) | **epoch 2** (eval_loss 0.9358) | (Stage C 후 확정) |
| Stage B 응답 | 828개 (6 모델 × 138) | `finetune/outputs/stage_b/responses.jsonl` |
| Stage B 시간 | 94분 | `finetune/logs/stage_b_run.log` |
| Stage C | 진행 예정 | — |

## 1.2 핵심 발견 3가지

### 발견 1: 학습이 응답을 60% 간결화시킴
- baseline: 697자 → epoch 1~3: ~280자
- 니체 짧은 아포리즘 스타일을 잘 학습

### 발견 2: epoch 4부터 token collapse
- epoch 4: bimodal (median 304 정상, max 21,128 폭주)
- epoch 5: uniform shift (전체가 baseline보다 길어짐)
- 단일 토큰 무한 반복 (`of of of...`, `l l l l...`)

### 발견 3: eval_loss는 정성적 붕괴를 과소평가
- epoch 3 → epoch 4: eval_loss +0.084 (미세)
- 같은 구간: 평균 응답 길이 +103% (273 → 555자)
- 결론: **loss curve만 보면 안 된다**

---

# 2. Stage A: 데이터 결과

## 2.0 Stage 0 ~ 0.9 통과율 (Stage A 이전 단계)

> **알림**: 이 섹션은 Stage A 이전의 데이터 생성 단계 결과입니다.
> Stage A는 §2.1부터 시작.
>
> 자세한 알고리즘은 [DATA_SPEC.md §9](./DATA_SPEC.md), 명령은
> [PIPELINE.md §2](./PIPELINE.md) 참고.

### 2.0.1 단계별 카운트

```
원전 (5권 영어)
       ↓ Stage 0: 청킹
973 청크
       ↓ Stage 0.7: 한국어 재구성
973 청크 (1:1 매핑, text_ko_reconstructed 추가)
       ↓ Stage 0.5: 5축 LLM 채점 + 책별 통과 조건
973 채점 → 928 passed (95.4%)
       ↓ Stage 0.9: SFT 생성 (passed만, 청크당 3개)
~2,780 SFT 후보
       ↓ Stage A 4단계
2,413 train + 138 eval
```

### 2.0.2 책별 청크 수 (Stage 0)

| 책 | 한국어 이름 | 청크 수 | expected_total | 청킹 단위 |
|---|---|---|---|---|
| JW | 즐거운 학문 | **383** | 383 ✓ | 1 아포리즘 = 1 청크 |
| BGE | 선악의 저편 | **296** | 296 ✓ | 1 아포리즘 = 1 청크 (Part 9개) |
| GM | 도덕의 계보 | 77 | 가변 | section 단위 (3 essay + preface) |
| TI | 우상의 황혼 | 151 | 가변 | 챕터 × 아포리즘 (11 챕터) |
| EH | 이 사람을 보라 | 66 | 가변 | 5 메인 챕터 × sub_chapter |
| **합계** | — | **973** | — | — |

JW와 BGE는 본편 아포리즘 수가 정해져 있어 expected_total과 1:1 검증 가능.

### 2.0.3 책별 Stage 0.5 통과율 (LLM 5축 채점 + 책별 정책)

```
JW:  376 / 383 (98.2%)  ← 가장 높음 (조건 가장 약함)
BGE: 274 / 296 (92.6%)
GM:   70 /  77 (90.9%)  ← 가장 낮음 (조건 가장 엄격)
TI:  143 / 151 (94.7%)
EH:   65 /  66 (98.5%)  ← 자전 회고는 거의 다 통과
─────────────────────
Total: 928 / 973 (95.4%)
```

### 2.0.4 책별 통과 조건과 통과율의 인과관계

| 책 | 통과 조건 | 통과율 | 해석 |
|---|---|---|---|
| EH | `(C>=3 OR B>=3) AND sc>=3` | 98.5% | density 검사 없음 (자전이라 밀도 무시) → 가장 높음 |
| JW | `(A>=3 OR B>=3) AND sc>=3 AND den>=2` | 98.2% | OR 조건 + 낮은 density 임계 → 거의 통과 |
| TI | 챕터별 11가지 다른 조건 | 94.7% | 챕터 성격에 맞춰 정교하게 설정 |
| BGE | `B>=3 AND sc>=3 AND den>=2` | 92.6% | 철학 점수 필수 (BGE는 본격 철학서) |
| GM | `B>=4 AND sc>=4 AND den>=3` | **90.9%** | **모든 축이 다른 책보다 한 단계 위 (가장 엄격)** |

**핵심 관찰**:
- **통과율과 통과 조건의 엄격성이 정확히 일치**
- 데이터셋 설계가 의도대로 작동했다는 증거
- GM의 높은 임계값(>=4, >=4, >=3)이 가장 낮은 통과율을 만듦
- EH의 density 면제가 가장 높은 통과율을 만듦

자세한 통과 조건은 [DATA_SPEC.md §9.4](./DATA_SPEC.md) 참고. TI 챕터별 11가지
조건도 같은 섹션에 있음.

### 2.0.5 5축 평가 정의 (Stage 0.5 LLM judge)

LLM은 한국어로 재구성된 청크를 5개 축으로 1~5점 채점 (텍스트만 보고, 책 정보 없이):

| 축 | 의미 |
|---|---|
| `track_existential` | 현대인 고민에 응답 가능한 통찰? |
| `track_philosophical` | 개념·논증 명확? |
| `track_biographical` | 화자 자신의 삶 서술? |
| `self_contained` | 청크 단독으로 의미 통함? |
| `density` | 통찰 압축도? |

### 2.0.6 use_case 자동 결정

5축 점수 중 3 tracks의 ≥3 여부로 use_case가 자동 도출됨:

```python
A = track_existential >= 3
B = track_philosophical >= 3
C = track_biographical >= 3

if A and B and C: "all"
if A and B:       "existential+philosophical"  # 가장 많음
if B and C:       "philosophical+biographical"
if A and C:       "existential+biographical"
if A:             "existential"
if B:             "philosophical"
if C:             "biographical"
```

**즉 use_case는 사람이 정한 게 아니라 LLM 채점 결과에서 자동 도출**됩니다.
이게 [DATA_SPEC.md §3.10](./DATA_SPEC.md)의 use_case enum의 출처.

### 2.0.7 Stage 0.9: SFT 생성 결과

- **입력**: 928 passed 청크
- **이상적 출력**: 928 × 3 = 2,784
- **실제 출력**: **2,780** (4건 LLM 실패로 0개 반환)
- **실패율**: 0.4%

**핵심 메커니즘**:
- 청크당 3개를 **한 번의 LLM 호출에 생성** (3번 호출 X)
- temperature 0.85 (다양성 우선)
- `USE_CASE_TO_PATTERNS` 매핑으로 패턴 제한
- voice별 system prompt 9개 중 random.choice

### 2.0.8 v10.0.1 vs v10.0.2 정정 사항

이전 문서(v10.0.1)는 추측에 기반해서 다음 사항이 잘못 적혀 있었음.
Phase 1 코드 검토로 정정됨:

| 항목 | v10.0.1 (잘못) | v10.0.2 (실제) |
|---|---|---|
| 파이프라인 순서 | 청킹 → 필터 → 재구성 → SFT | 청킹 → **재구성 → 필터** → SFT |
| 필터 채점 텍스트 | 영어 (추측) | **한국어** (재구성된 텍스트) |
| 5축 정의 | 표시 안 됨 | 완전 정의 |
| 책별 통과 조건 | 표시 안 됨 | 5권 + TI 11챕터별 |
| use_case 결정 | 사람이 정함 (추측) | LLM 채점에서 자동 도출 |
| filtered/ 의미 | 통과한 청크만 | **973 채점 결과 전체** + passed flag |

**메타 인사이트**: 이런 종류의 정정은 코드를 직접 읽지 않으면 발견할 수 없음.
Phase 1 작업으로 8개 핵심 파일을 모두 검토해서 발견. 자세한 정정 항목은
DATA_SPEC.md v10.0.2의 변경 이력 참고.

## 2.1 파이프라인 통과율

| 단계 | 입력 | 출력 | 폐기 | 폐기율 | 리포트 파일 |
|---|---|---|---|---|---|
| SFT Generation | — | 2,780 | — | — | — |
| Stage A-1 Clean | 2,780 | 2,728 | 52 | 1.9% | `cleaned_report.json` |
| Stage A-2 Score | 2,728 | 2,728 | 0 | 0% | `scored_report.json` |
| Stage A-3 Dedup | 2,728 | 2,725 | 3 | 0.1% | `dedup_report.json` |
| Stage A-4 Select | 2,725 | 2,551 | 174 | 6.4% | `select_report.json` |
| **Total** | **2,780** | **2,551** | **229** | **8.2%** | — |

리포트 파일 경로: `ml/v2_data/sft_candidates/*.json` 및 `ml/v2_data/sft_dataset/select_report.json`

## 2.2 Stage A-1 Clean 폐기 사유

| 사유 | 건수 |
|---|---|
| 표절 (5-gram match) | 33 |
| 길이 (<100 or >1500자) | 12 |
| 위로 표현 ("힘드시겠어요" 등) | 5 |
| Invalid concept (`amor_fati`, `perspective`) | 2 |
| **소계** | **52** |

추가로 **6건 자동 수정** (enum 정규화):
- `self-overcoming-health → self_overcoming_health` (2)
- `value-creation → value_creation` (1)
- `self_overcoming → self_overcoming_health` (1)
- `reflection_refframing → reflection_reframing` (2)

## 2.3 Stage A-2 Score 결과

**LLM Judge 평균 점수** (Gemma 4 26B-A4B, 2,728건 채점):

| 축 | 평균 (1~5) | 해석 |
|---|---|---|
| Q1 (Pattern Fidelity) | **4.53** | 응답 패턴 규칙 준수 — 양호 |
| Q2 (Q-A Coherence) | **4.81** | 질문-답변 정합성 — 매우 높음 |
| Q3 (Voice & Persona) | **3.55** | 니체 voice 구현 — 가장 어려움 |

**평균 normalized_score**: 0.859

**등급 분포**:
| Grade | 기준 | Count | % |
|---|---|---|---|
| A | ≥ 0.85 | 1,726 | 63% |
| B | ≥ 0.70 | 828 | 30% |
| C | ≥ 0.55 | 162 | 6% |
| F | < 0.55 | 12 | 0.4% |

**Q3가 낮은 이유**: voice 차이를 엄격하게 채점. polemical_sharp의 어미 일관성 결함(7%)이 일부 반영됐을 가능성. [DATA_SPEC §15.7](./DATA_SPEC.md) 참고.

## 2.4 Stage A-3 Dedup 결과

**총 제거 건수**: 3건 (0.1%)

- A-hard (MinHash similarity ≥ 0.93): **0건**
- Q+A 임베딩 중복 (≥ 0.92 + 답변 ≥ 0.85): **3건**

**Dedup이 적은 이유**: 데이터 생성 파이프라인이 **청크당 3개의 서로 다른 변주**를 만들도록 설계되어 있어서, 애초에 중복이 거의 안 생김. 상류 다양성 설계가 잘 작동했다는 증거.

## 2.5 Stage A-4 Select 결과

| 항목 | 값 |
|---|---|
| 입력 | 2,725 |
| C/F 폐기 | 174 |
| Accepted | 2,551 |
| **Train** | **2,413** |
| **Eval** | **138** |
| Train 평균 점수 | 0.8806 |
| Eval 평균 점수 | 0.7705 |
| Stratification groups | 85 |
| Small groups → train | 34 |

**Train vs Eval 점수 차이** (0.88 vs 0.77, 차이 0.11):
- **의도된 결과**. Eval을 일부러 도전적으로 구성.
- 학습 모델이 "쉬운 샘플만 잘 푸는지" 검증 목적.

## 2.6 최종 분포 (train 2,413)

### Voice
| Voice | Count | % |
|---|---|---|
| contemplative_aphorism | 992 | 41% |
| polemical_sharp | 872 | 36% |
| hammer_intensified | 549 | 23% |

### Question Type
| Type | Count | % |
|---|---|---|
| existential_question | 1,456 | 60% |
| philosophical_question | 807 | 33% |
| biographical_question | 150 | 6% |

### Source
| Source | Count | % |
|---|---|---|
| JW (즐거운 학문) | 992 | 41% |
| BGE (선악의 저편) | 691 | 29% |
| TI (우상의 황혼) | 388 | 16% |
| GM (도덕의 계보) | 181 | 7% |
| EH (이 사람을 보라) | 161 | 7% |

### Difficulty
| Difficulty | Count | % |
|---|---|---|
| medium | 1,507 | 62% |
| easy | 476 | 20% |
| hard | 430 | 18% |

### Grade
| Grade | Count | % |
|---|---|---|
| A | 1,710 | 71% |
| B | 703 | 29% |

전체 분포 표는 [DATA_SPEC §11.2](./DATA_SPEC.md) 참고.

---

# 3. 학습: LoRA 결과

## 3.1 학습 메타데이터

| 항목 | 값 |
|---|---|
| 모델 | Gemma 4 31B (`google/gemma-4-31B-it`) |
| 학습 방식 | LoRA r=16, alpha=32, bf16 |
| 데이터 | 2,413 train (95% / 5% val split) |
| Epochs | 5 |
| 학습 시간 | **1시간 9분 54초** (4,194초) |
| Total steps | 720 |
| Steps/sec | 0.172 |
| Final train_loss | 0.8648 |
| GPU | A100 80GB |
| Memory peak | ~70GB |
| Wandb run | searchformaat |

## 3.2 Loss 곡선 (실측)

### Train Loss

| Step | Epoch | Train Loss |
|---|---|---|
| 10 | 0.07 | **5.755** (시작) |
| 30 | 0.21 | 1.580 |
| 70 | 0.49 | 1.002 |
| 144 | 1.00 | ~0.95 |
| 288 | 2.00 | ~0.85 |
| 432 | 3.00 | ~0.70 |
| 600 | 4.17 | 0.560 |
| 720 | 5.00 | **0.5411** (종료) |

### Eval Loss ⭐

| Epoch | Eval Loss | 변화 |
|---|---|---|
| 1 | 0.9509 | (시작) |
| **2** | **0.9358** | **-0.0151** ⭐ **최저** |
| 3 | 0.9597 | +0.0239 |
| 4 | 1.044 | +0.0843 |
| 5 | 1.106 | +0.062 |

**관찰**:
- epoch 2가 명백한 sweet spot
- epoch 4부터 큰 폭 증가 (오버핏 진행)
- epoch 5는 시작값보다 16% 악화

### Train vs Eval 격차

| Epoch | Train | Eval | 격차 |
|---|---|---|---|
| 1 | ~0.95 | 0.9509 | ~0.00 |
| 2 | ~0.85 | 0.9358 | ~0.09 |
| 3 | ~0.70 | 0.9597 | ~0.26 |
| 4 | ~0.59 | 1.044 | ~0.45 |
| 5 | 0.54 | 1.106 | **~0.57** |

격차가 0 → 0.57로 벌어짐 = 명백한 오버핏 진행.

자세한 분석은 [SFT_STRATEGY §4](./SFT_STRATEGY.md) 참고.

## 3.3 체크포인트 위치

```
ml/finetune/outputs/nietzsche-lora-31b/
├── checkpoint-144/    epoch 1
├── checkpoint-288/    epoch 2 ⭐ (eval_loss 최저)
├── checkpoint-432/    epoch 3
├── checkpoint-576/    epoch 4
├── checkpoint-720/    epoch 5
├── final/             trainer 자동 저장 (= epoch 5)
└── README.md          모델 카드
```

각 체크포인트: ~800MB. 총 4.4GB. **gitignore** (HF Hub로 백업).

**HF Hub 백업**: `banzack/nietzsche-gemma4-31b-lora` (private)
- branches: `epoch1`, `epoch2`, `epoch3`, `epoch4`, `epoch5`

---

# 4. Stage B: 응답 생성 결과

## 4.1 평가 설정

| 항목 | 값 |
|---|---|
| 모델 수 | 6 (baseline + epoch 1~5) |
| 평가 데이터 | 138 (eval.jsonl held-out) |
| 총 응답 | **828** |
| 추론 엔진 | vLLM 0.19, PagedAttention |
| Temperature | 0.0 (greedy) |
| Max new tokens | 768 |
| Max model len | 1280 |
| 총 시간 | **94분** (예상 170분의 ~55%) |

## 4.2 응답 길이 통계 (실측, 핵심)

| 모델 | min | **avg** | median | max | 빈응답 | 짧은(<50) |
|---|---|---|---|---|---|---|
| baseline | 138 | **697** | 726 | 1,337 | 0 | 0 |
| epoch1 | 58 | **286** | 285 | 440 | 0 | 0 |
| epoch2 | 62 | **277** | 289 | 415 | 0 | 0 |
| epoch3 | 59 | **273** | 284 | 395 | 0 | 0 |
| epoch4 | **0** | 555 | 304 | **21,128** | **2** | **5** |
| epoch5 | **0** | **811** | 816 | 2,261 | **1** | **8** |

**baseline → epoch1**: 697 → 286 (**-59%**) — 학습이 응답을 절반 이상 간결화

**epoch1 ~ 3**: 매우 안정적 (avg 273~286, 분포 균등)

**epoch4**: bimodal — median 304 정상, but avg 555 (1.8배), max 21,128 (정상의 50배)

**epoch5**: uniform shift — median = avg ≈ 815, baseline보다도 길어짐

## 4.3 두 가지 붕괴 모드

| Epoch | 붕괴 모드 | 특징 |
|---|---|---|
| 4 | **Bimodal**: 정상 + 폭주 혼재 | median 정상, max 폭증, 빈 응답 등장 |
| 5 | **Uniform shift**: 전체 일관 길어짐 | median = avg, baseline보다 verbose |

epoch 4와 5의 붕괴 양상이 다름. epoch 4는 "확률적 폭주", epoch 5는 "안정화된 망가짐".

## 4.4 Token Collapse 실제 사례

epoch 4의 폭주 응답 4개 (`finetune/outputs/stage_b/responses.jsonl`):

### 사례 1: `nietzsche_000030` (21,128자)
정상 한국어로 시작 후 무한 생성:
```
당신은 지금 자신의 삶이 거대한 유기체의 소화와 clash하는 미세한
현상들이라고 재구성해야 합니다. 당신이 마주하는 이 지루한 일상과
무의미한 노동은 단순히 버려지는 시간이 아니라...
[중간 생략]
                                                                 (공백 폭주로 잘림)
```

### 사례 2: `nietzsche_002499` (1,667자) — 구문 반복
```
당신의 문제는 단순한 나태함이 아니라, 모든 것을 '반쯤' 해 own que의
낭구_en_nasse1m_of_the_half_way1s_of_the_half-hearted1s_of_the_half-hearted1s_
of_the_half-hearted1s_of_the_half-hearted1s_of_the_half-hearted1s...
```

### 사례 3: `nietzsche_001637` (1,518자) — 단일 토큰 반복
```
나에게는 한량 앞에서의 결연한 침묵을... 수ofofofofofofofofofofofof
ofofofofofofofofofofofofofofofofof...
```

### 사례 4: `nietzsche_000479` (1,508자) — 공백+문자 반복
```
그대의 상태를 진 Seriously 진단해보겠습니다... l l l l l l l l l l
l l l l l l l l l l l l l l l l l l l l l l l l l...
```

**진단**: **Token degeneration / token collapse**. 모델이 EOS 확률이 극단적으로 낮아져 종료를 못 하고 같은 토큰을 무한 생성하는 현상. 학습 데이터에 대한 과도한 fitting으로 분포 entropy가 감소하면서 발생.

## 4.5 가장 강력한 발견

| 변화 | 수치 |
|---|---|
| eval_loss (epoch 3 → 4) | +0.084 (미세) |
| 평균 응답 길이 (epoch 3 → 4) | +103% (273 → 555자) |
| Max 응답 길이 (epoch 3 → 4) | +5,247% (395 → 21,128자) |
| 빈 응답 (epoch 3 → 4) | 0 → 2 |

**의미**: eval_loss 0.08 증가가 token collapse라는 정성적 붕괴를 의미.

> **eval_loss는 모델 동작 변화를 과소평가한다.**
> Stage B 같은 직접 응답 평가 없이 loss curve만 봤다면 이 위험을 못 봤을 것.

이건 이 프로젝트의 **핵심 메타 인사이트**. 자세한 분석은 [SFT_STRATEGY §5](./SFT_STRATEGY.md) 참고.

## 4.6 결과 파일

```
ml/finetune/outputs/stage_b/
├── responses.jsonl       1.8M  828 응답 (전체)
└── responses.jsonl.bak    93K  baseline 백업

ml/finetune/outputs/stage_b_test/
├── test_a_baseline.jsonl  415K  Test A: vLLM baseline 검증 (138)
└── test_b2_epoch1.jsonl    10K  Test B2: epoch1 검증 (5)
```

### 응답 파일 스키마
```json
{
  "sample_id": "nietzsche_000489",
  "model_tag": "baseline",
  "input_messages": [
    {"role": "system",    "content": "..."},
    {"role": "user",      "content": "..."}
  ],
  "reference": "정답 응답 (eval.jsonl의 assistant)",
  "generated": "모델이 생성한 응답"
}
```

## 4.7 로그

```
ml/finetune/logs/
├── stage_b_run.log              마스터 로그 (350K)
├── stage_b_baseline.log         (18K)
├── stage_b_epoch1.log           (17K)
├── stage_b_epoch2.log           (17K)
├── stage_b_epoch3.log           (17K)
├── stage_b_epoch4.log           (21K)
├── stage_b_epoch5.log           (22K)
├── merge_epoch2.log             (57K)
├── merge_epoch3.log             (61K)
├── merge_epoch4.log             (60K)
└── merge_epoch5.log             (53K)
```

---

# 5. Stage C: 채점 결과 (예정)

> **상태**: 작성 예정
> **목표**: Stage B 응답 828개를 LLM judge로 채점, 6 모델 비교 리포트 생성

## 5.1 계획

**Judge 모델**: Gemma 4 26B-A4B (Stage A-2와 동일)

**채점 축**:
- Q1: Pattern Fidelity (응답이 reference 패턴 규칙을 따르는가)
- Q2: Q-A Coherence (질문-답변 정합성)
- Q3: Voice & Persona (니체 voice 구현)

**Breakdown 차원**:
- 모델 (6): baseline + epoch 1~5
- Voice (3): contemplative / polemical / hammer
- Use case
- Question type

## 5.2 예상 결과 (가설)

| Epoch | Q1 (Pattern) | Q2 (Coherence) | Q3 (Voice) | 종합 |
|---|---|---|---|---|
| baseline | 낮음 | 중간 | 낮음 | 기준선 |
| 1 | 중간 | 높음 | 낮음~중간 | 학습 부족 |
| **2** | **높음** | **높음** | **중간~높음** | **best (잠정)** |
| 3 | 높음 | 높음 | 중간~높음 | 미미한 차이 |
| 4 | 낮음 | 낮음 (token collapse) | 낮음 | 위험 |
| 5 | 매우 낮음 | 매우 낮음 | 매우 낮음 | 사용 불가 |

이 가설이 맞으면 **epoch 2가 final pick**으로 확정됨.

## 5.3 생성될 파일 (예정)

```
ml/finetune/outputs/stage_c/
├── scored.jsonl              828개 채점 결과
├── scored_report.json        모델별 평균 점수
└── breakdown_report.md       voice/question_type 별 상세 분석
```

## 5.4 작성될 스크립트

| 스크립트 | 역할 | 기반 |
|---|---|---|
| `finetune/scripts/run_judge_server.sh` | judge vLLM 서버 시작 | (신규) |
| `finetune/scripts/stage_c_score.py` | Q1/Q2/Q3 채점 | `stage_a_score.py` 복사 + 수정 |
| `finetune/scripts/stage_c_report.py` | breakdown 리포트 | (신규) |

---

# 6. 결과 파일 빠른 접근

## 6.1 데이터 자산

```bash
# 학습 데이터
ml/v2_data/sft_dataset/train.jsonl              # 2413 (3.6M)
ml/v2_data/sft_dataset/eval.jsonl               # 138 (208K)
ml/v2_data/sft_dataset/select_report.json       # 분포 통계 (2K)

# Stage A 중간 산출물
ml/v2_data/sft_candidates/candidates.jsonl      # 2780 (직후)
ml/v2_data/sft_candidates/cleaned.jsonl         # 2728 (Stage A-1)
ml/v2_data/sft_candidates/cleaned_report.json
ml/v2_data/sft_candidates/scored.jsonl          # 2728 (Stage A-2)
ml/v2_data/sft_candidates/scored_report.json
ml/v2_data/sft_candidates/deduped.jsonl         # 2725 (Stage A-3)
ml/v2_data/sft_candidates/dedup_report.json

# 데이터 생성 중간물
ml/v2_data/english_raw/                         # 5권 원전 (4M)
ml/v2_data/english_chunks/                      # 청킹 (3.6M)
ml/v2_data/filtered/                            # 3-Track 필터 (5.6M)
ml/v2_data/reconstructed/                       # 한국어 재구성 (5.4M)
```

## 6.2 모델 자산

```bash
# 로컬 (gitignore)
ml/finetune/outputs/nietzsche-lora-31b/checkpoint-144/   # epoch 1
ml/finetune/outputs/nietzsche-lora-31b/checkpoint-288/   # epoch 2 ⭐
ml/finetune/outputs/nietzsche-lora-31b/checkpoint-432/   # epoch 3
ml/finetune/outputs/nietzsche-lora-31b/checkpoint-576/   # epoch 4
ml/finetune/outputs/nietzsche-lora-31b/checkpoint-720/   # epoch 5

# HF Hub (private)
# https://huggingface.co/banzack/nietzsche-gemma4-31b-lora
# branches: epoch1 ~ epoch5
```

## 6.3 평가 결과

```bash
# Stage B
ml/finetune/outputs/stage_b/responses.jsonl              # 828 응답 (1.8M)
ml/finetune/outputs/stage_b/responses.jsonl.bak          # 백업 (93K)

ml/finetune/outputs/stage_b_test/test_a_baseline.jsonl   # vLLM 검증 (415K)
ml/finetune/outputs/stage_b_test/test_b2_epoch1.jsonl    # merge 검증 (10K)
```

## 6.4 로그

```bash
ml/finetune/logs/train_31b_full.log              # 학습 로그 (309K)
ml/finetune/logs/stage_b_run.log                 # Stage B 마스터 (350K)
ml/finetune/logs/stage_b_{baseline,epoch1~5}.log # 모델별 로그
ml/finetune/logs/merge_epoch{2~5}.log            # merge 로그
ml/finetune/logs/test_{a,b1,b1_unsloth,b2}.log   # 검증 테스트 로그
ml/finetune/logs/stage_b_generate.log            # 초기 generate 로그
```

---

# 7. 결과 검증 명령

## 7.1 빠른 점검 (1분)

```bash
cd /workspace/nietzche-sllm-project/ml

# 1. 데이터 무결성
wc -l v2_data/sft_dataset/train.jsonl    # 2413
wc -l v2_data/sft_dataset/eval.jsonl     # 138

# 2. Stage B 진행도
wc -l finetune/outputs/stage_b/responses.jsonl    # 828

# 3. 체크포인트 5개 모두 있는지
ls finetune/outputs/nietzsche-lora-31b/checkpoint-*/adapter_model.safetensors | wc -l    # 5
```

## 7.2 Stage A 분포 확인

```bash
source .venv/bin/activate

python -c "
import json
from collections import Counter

with open('v2_data/sft_dataset/train.jsonl') as f:
    samples = [json.loads(l) for l in f]

print(f'Total: {len(samples)}')
print()
for field in ['voice', 'question_type', 'response_pattern', 'grade']:
    print(f'{field}:')
    for k, v in Counter(s[field] for s in samples).most_common():
        print(f'  {k:<35} {v}')
    print()
"

deactivate
```

## 7.3 학습 결과 확인

```bash
# Loss 곡선 (마지막 100줄)
grep -E "'loss':|'eval_loss':" finetune/logs/train_31b_full.log | tail -100

# 학습 시간
grep -E "train_runtime" finetune/logs/train_31b_full.log
```

## 7.4 Stage B 응답 길이 통계

```bash
source .venv/bin/activate

python << 'PYEOF'
import json
import statistics
from collections import defaultdict

with open('finetune/outputs/stage_b/responses.jsonl') as f:
    rows = [json.loads(l) for l in f]

by_model = defaultdict(list)
for r in rows:
    by_model[r['model_tag']].append(len(r['generated']))

print(f'{"model":<12} {"count":>6} {"avg":>8} {"median":>8} {"max":>8} {"empty":>7}')
print('-' * 55)
for model in ['baseline', 'epoch1', 'epoch2', 'epoch3', 'epoch4', 'epoch5']:
    if model not in by_model:
        continue
    lens = sorted(by_model[model])
    empty = sum(1 for l in lens if l == 0)
    print(f'{model:<12} {len(lens):>6} {statistics.mean(lens):>8.0f} '
          f'{statistics.median(lens):>8.0f} {max(lens):>8} {empty:>7}')
PYEOF

deactivate
```

## 7.5 특정 응답 확인

```bash
source .venv/bin/activate

python << 'PYEOF'
import json

# 특정 sample_id의 모든 모델 응답 비교
TARGET = 'nietzsche_000030'   # 또는 다른 sample_id

with open('finetune/outputs/stage_b/responses.jsonl') as f:
    rows = [json.loads(l) for l in f]

for r in rows:
    if r['sample_id'] != TARGET:
        continue
    print(f"\n=== {r['model_tag']} ({len(r['generated'])} chars) ===")
    print(r['generated'][:300])
    if len(r['generated']) > 300:
        print(f"... [{len(r['generated']) - 600} chars omitted] ...")
        print(r['generated'][-300:])
PYEOF

deactivate
```

## 7.6 Token Collapse 사례 찾기

```bash
source .venv/bin/activate

python << 'PYEOF'
import json
from collections import defaultdict

with open('finetune/outputs/stage_b/responses.jsonl') as f:
    rows = [json.loads(l) for l in f]

# 1500자 이상인 응답만 (잠재적 폭주)
long_responses = [r for r in rows if len(r['generated']) > 1500]

print(f"1500자 초과 응답: {len(long_responses)}")
print()

by_model = defaultdict(list)
for r in long_responses:
    by_model[r['model_tag']].append(r)

for model in sorted(by_model.keys()):
    print(f'\n=== {model}: {len(by_model[model])}개 ===')
    for r in sorted(by_model[model], key=lambda r: -len(r['generated']))[:3]:
        print(f"  {r['sample_id']}: {len(r['generated'])} chars")
        print(f"    끝 100자: ...{r['generated'][-100:]}")
PYEOF

deactivate
```

## 7.7 Git 상태

```bash
cd /workspace/nietzche-sllm-project
git status
git log --oneline -10
```

---

## 부록: 결과를 발표 자료에 활용하기

### 슬라이드 1: 데이터 품질 관리
- §2.1 통과율 표 (2,780 → 2,551)
- §2.3 LLM Judge 점수 (Q1/Q2/Q3)
- §2.4 Dedup이 적은 이유 (상류 다양성 설계)

### 슬라이드 2: 학습 곡선
- §3.2 Eval Loss 곡선 (V자 → 역U자)
- §3.2 Train vs Eval 격차 (0 → 0.57)

### 슬라이드 3: 학습이 응답을 간결화 (긍정 결과)
- §4.2 baseline 697자 → epoch 2 277자 (-60%)

### 슬라이드 4: ⭐ 발표의 결정타 — eval_loss는 거짓말한다
- §4.5 eval_loss +0.084 vs 응답 길이 +103%
- §4.4 token collapse 실제 사례 4개
- "loss curve만 보면 안 된다" 메타 인사이트

### 슬라이드 5: Best Epoch 선택
- §3.2 epoch 2 = eval_loss 최저
- §4.2 epoch 2 = 응답 정상
- 두 기준 모두 만족 → epoch 2 확정

---

## 문서 끝

**최종 갱신**: 2026-04-11
**버전**: v1.0
**다음 갱신 예정**: Stage C 완료 후 §5 채워넣기
