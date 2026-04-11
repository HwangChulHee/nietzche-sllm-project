# SFT 학습 전략

> 이 문서는 니체 페르소나 LoRA 파인튜닝의 **모든 학습 결정과 근거**를 기록합니다.
> "왜 이렇게 학습했나"의 답이며, 학습 곡선 해석과 best epoch 선택 근거까지 포함합니다.
>
> 모든 숫자는 **실측 기반** (`finetune/logs/train_31b_full.log`,
> `finetune/outputs/stage_b/responses.jsonl`).

---

## 목차

1. [학습 목표](#1-학습-목표)
2. [핵심 결정 6가지](#2-핵심-결정-6가지)
3. [Chat Template 사가](#3-chat-template-사가)
4. [학습 곡선 해석](#4-학습-곡선-해석)
5. [Stage B 결과 분석](#5-stage-b-결과-분석)
6. [Best Epoch 결정 근거](#6-best-epoch-결정-근거)
7. [알려진 한계](#7-알려진-한계)
8. [향후 개선 방향](#8-향후-개선-방향)

---

# 1. 학습 목표

## 1.1 무엇을 학습시키려 했나

**한 줄**: Gemma 4 31B의 일반 한국어 능력을 유지하면서, 니체 페르소나(문체 + 사유 방식)를 입히는 것.

**구체적 목표**:
1. **문체 학습**: contemplative_aphorism, polemical_sharp, hammer_intensified 3가지 voice
2. **사유 방식 학습**: niche의 응답 패턴 8가지 (reflection_reframing, diagnostic, ...)
3. **한국어 자연성 보존**: 영어식 직역체 회피
4. **원전 인용 회피**: 학습 데이터의 5-gram 표절을 모델이 그대로 외우지 않도록

## 1.2 무엇을 학습시키지 않으려 했나

**의도적 회피**:
- ❌ 위로·공감 표현 ("힘드시겠어요" 등) — Stage A-1에서 차단
- ❌ "AI로서 말씀드리면" 같은 메타 발화
- ❌ 영어 원문 직접 인용
- ❌ 모든 질문에 동일 voice로 답변하는 단조로움

## 1.3 데이터 제약

| 항목 | 값 |
|---|---|
| 학습 샘플 | **2,413개** (작음) |
| 평가 샘플 | 138개 (held-out) |
| 평균 응답 길이 | ~280자 |
| 데이터 분포 | DATA_SPEC.md §11.2 참고 |

**핵심 제약**: 데이터셋이 **2,413개**로 작습니다. 일반적인 SFT는 수만~수십만 샘플을 쓰는데, 이건 그 1/10~1/100 수준. 따라서 **오버핏을 막는 것**이 가장 큰 도전이었습니다.

---

# 2. 핵심 결정 6가지

각 결정에는 **근거**와 **트레이드오프**를 함께 기록합니다.

## 2.1 LoRA (not QLoRA), bf16

**선택**: LoRA r=16 on bf16 base model

**이유**:
- A100 80GB로 충분 — QLoRA 없이도 OOM 안 남
- bf16이 4bit보다 학습 정확도 높음 (특히 작은 데이터셋에서)
- 메모리: ~70GB peak (여유 있음)
- 시간: bf16 직접 forward가 4bit dequant보다 빠름

**트레이드오프**:
- ✗ 4bit quantization 노하우 미축적
- ✓ 데이터 작은 상황에서 최대한 정밀하게 학습

**대안 검토**:
- QLoRA (4bit base): 메모리 절감되지만 시간/정확도 손해
- Full fine-tune: 31B 파라미터 → A100 1대로 불가능

## 2.2 LoRA Rank 16 (작게)

**선택**: r=16, alpha=32 (scale 2.0)

**이유**:
- 데이터 2,413개에 대해 r=64+는 **확실한 오버핏**
- r=16은 약 0.5~1% 파라미터 학습 → 페르소나 학습엔 충분
- alpha/r=2.0은 표준 (LoRA 논문 권장)

**트레이드오프**:
- ✗ 더 정교한 패턴 학습은 r=32~64이 유리할 수 있음
- ✓ 작은 데이터에 대한 안전한 선택

**Target modules** (7개):
```
q_proj, k_proj, v_proj, o_proj  (attention)
gate_proj, up_proj, down_proj    (MLP)
```

모든 linear projection을 학습. attention만 학습하는 것보다 페르소나 학습이 잘 됨.

## 2.3 Learning Rate 1e-4 (보수적)

**선택**: LR 1e-4 + cosine scheduler + warmup 20 steps

**이유**:
- 데이터셋 작음 → **공격적인 LR은 오버핏 가속**
- 일반 권장 LoRA LR는 2e-4~5e-4. 우리는 그보다 보수적인 1e-4
- Cosine 스케줄러로 후반부 미세 조정 가능
- Warmup 20 steps (~3% of 720) — 짧은 학습이라 길게 안 함

**검증**: 학습 로그에서 처음 step부터 안정적 감소
```
step 144 (0.07 epoch): loss 5.755 (시작)
step 720 (0.49 epoch): loss 1.002 (1 epoch 안에 ~80% 수렴)
```

## 2.4 5 Epochs 모두 보존, `load_best_model_at_end=False`

**선택**: 5 epochs 학습, 모든 체크포인트 저장 (save_total_limit=5)

**이유**:
- **eval_loss로 best epoch 선택을 신뢰하지 않음**
- LoRA는 이론상 작은 변화이지만, **응답의 질적 변화는 비선형**
- 사후에 Stage B로 직접 응답 비교 후 best 선택
- 학습 시간이 짧음 (~1시간) → 다 보존해도 비용 OK

**결정의 정당성** (사후 검증):
- eval_loss 최저는 **epoch 2** (0.9358)
- 그러나 epoch 4부터 응답에서 token collapse 발생 (§5.4 참고)
- **eval_loss와 응답 품질이 어긋남** → 이 결정이 옳았음을 보여줌

자세한 분석은 [§4 학습 곡선 해석](#4-학습-곡선-해석)과 [§5 Stage B 결과 분석](#5-stage-b-결과-분석) 참고.

## 2.5 `assistant_only_loss=False` (어쩔 수 없음)

**선택**: 전체 텍스트에 loss 적용 (assistant 토큰만이 아닌 system + user + assistant 전부)

**이유**: trl이 VLM (Vision-Language Model) 베이스에서 `assistant_only_loss=True` 미지원. Gemma 4가 multi-modal base model이라 영향 받음.

**에러 메시지**:
```
ValueError: assistant_only_loss is not supported for VLM models
```

**우회**:
```python
cfg = SFTConfig(
    ...
    assistant_only_loss=False,   # 어쩔 수 없음
)
```

**영향 분석**:
- **이론상**: system + user 토큰에도 loss → 모델이 user 질문을 외우려는 압력
- **실제**: 응답이 메시지의 ~70% 차지 → loss 가중치가 자연스럽게 응답에 쏠림
- **관찰**: 학습된 모델이 user 질문을 그대로 반복하지 않음 → 큰 문제 없음

**한계 명시**: [§7 알려진 한계](#7-알려진-한계)에 기록.

## 2.6 Native Chat Template + 4-assertion 검증

**선택**: Unsloth의 `get_chat_template` 호출 안 함. tokenizer가 가진 **native Gemma 4 template** 사용.

**이유**: Unsloth의 `get_chat_template("gemma-2")` 또는 `("gemma-3")`이 Gemma 4와 호환 안 됨. 자세한 사가는 [§3 Chat Template 사가](#3-chat-template-사가) 참고.

**보호 장치** (`train.py`):
```python
_test_msgs = [
    {"role": "system",    "content": "SYSTEM_PROBE"},
    {"role": "user",      "content": "USER_PROBE"},
    {"role": "assistant", "content": "ASSISTANT_PROBE"},
]
_test_text = tokenizer.apply_chat_template(_test_msgs, tokenize=False)
assert "SYSTEM_PROBE" in _test_text
assert "USER_PROBE" in _test_text
assert "ASSISTANT_PROBE" in _test_text
assert _test_text.index("SYSTEM_PROBE") < _test_text.index("USER_PROBE"), \
    "system appears after user — likely merged into user message"
```

**왜 4번째 assertion이 핵심인가**: Unsloth Gemma 2/3 template은 system role을 user에 합쳐버립니다. 단순히 "SYSTEM_PROBE가 텍스트에 존재"만 검사하면 통과되지만, 순서 검사를 추가하면 잡힙니다.

### 추가 교훈 (Phase 1 정정에서 발견)

이 4-assertion 검증 패턴은 **데이터 생성 단계와 평가 단계의 voice 정의가 일치
해야 한다**는 더 일반적인 원칙의 한 사례입니다. Phase 1 코드 검토에서 발견한
또 다른 비대칭은 **§7.3 polemical_sharp 어미 일관성**에서 다룹니다.

핵심 원칙:
> **데이터 생성 시점의 기준**과 **데이터 평가 시점의 기준**이 일치해야 한다.
> 그렇지 않으면 작은 결함이 누적되어 최종 데이터 품질을 잠식한다.

이 프로젝트의 v11에서는 이 원칙을 **single source of truth**로 구현할 예정.
voice 정의를 별도 모듈(`voices.py`)로 추출해서 reconstructor와 score가 모두
같은 정의를 import하도록 리팩토링.

---

# 3. Chat Template 사가

## 3.1 문제 발견

학습 초기, 처음엔 Unsloth의 권장 패턴을 따라 작성:
```python
from unsloth.chat_templates import get_chat_template
tokenizer = get_chat_template(tokenizer, chat_template="gemma-2")
```

학습은 정상 진행. 그러나 inference 시 **응답이 system message를 무시**하는 현상.

## 3.2 원인 추적

`tokenizer.apply_chat_template()` 출력을 직접 확인:

**Gemma 2/3 형식** (Unsloth):
```
<start_of_turn>user
SYSTEM_CONTENT

USER_CONTENT<end_of_turn>
<start_of_turn>model
ASSISTANT_CONTENT<end_of_turn>
```

**문제**: system role이 user 토큰 안으로 **합쳐짐** (`<start_of_turn>user` 안에 system + user가 같이). 모델이 system을 별도로 인지 못함.

**Gemma 4 native 형식**:
```
<bos><|turn|>system
SYSTEM_CONTENT<|turn|>
<|turn|>user
USER_CONTENT<|turn|>
<|turn|>assistant
ASSISTANT_CONTENT<|turn|>
```

`<|turn|>` 토큰으로 명확히 구분. system이 별도 turn으로 들어감.

## 3.3 해결

**조치**:
1. `unsloth.chat_templates.get_chat_template` **호출 제거**
2. tokenizer의 native template 그대로 사용
3. 4 assertion 검증 추가

## 3.4 교훈

- **라이브러리 문서를 너무 믿지 말 것**. Unsloth 문서에 "Gemma 시리즈는 gemma-2 template 사용"이라고 적혀 있지만, Gemma 4는 다름.
- **검증 코드를 학습 스크립트에 영구 추가**. 미래의 나(또는 새 LLM 세션)가 같은 실수를 반복하지 않도록.
- **assertion은 양적 + 질적 둘 다**. 단순 존재 확인 (`in text`) + 순서 확인 (`index <`) 두 가지.

---

# 4. 학습 곡선 해석

## 4.1 학습 메타데이터

| 항목 | 값 |
|---|---|
| 학습 시작 → 종료 | 2026-04-10 |
| 총 시간 | **1시간 9분 54초** (4194초) |
| Total steps | 720 |
| Steps/sec | 0.172 |
| Samples/sec | 2.733 |
| Final train loss | **0.8648** |
| GPU | A100 80GB |
| Memory peak | ~70GB |

## 4.2 Train Loss 곡선 (실측)

학습 진행에 따른 loss (10 step마다 로깅, 일부만 발췌):

| Step | Epoch | Train Loss | LR |
|---|---|---|---|
| 10 | 0.07 | **5.755** (시작) | 4.5e-05 |
| 20 | 0.14 | 2.894 | 9.5e-05 |
| 30 | 0.21 | 1.580 | 9.996e-05 |
| 40 | 0.28 | 1.215 | 9.982e-05 |
| 50 | 0.35 | 1.093 | 9.958e-05 |
| 70 | 0.49 | **1.002** (1차 안정) | 9.88e-05 |
| 100 | 0.70 | 1.000 | 9.689e-05 |
| 144 | 1.00 | ~0.95 | — |
| 200 | 1.39 | 0.860 | 8.471e-05 |
| 288 | 2.00 | ~0.85 | — |
| 432 | 3.00 | ~0.70 | — |
| 530 | 3.68 | 0.601 | 1.727e-05 |
| 600 | 4.17 | 0.560 | 7.193e-06 |
| 700 | 4.86 | 0.547 | 2.219e-07 |
| 720 | 5.00 | **0.5411** (종료) | 6.092e-08 |

**관찰**:
- **첫 30 step (0.21 epoch)** 에 가장 큰 학습 (5.755 → 1.580, **72% 감소**)
- epoch 1 종료 시점에 ~0.95로 거의 수렴
- epoch 2~5는 0.95 → 0.54로 **40% 추가 감소** (느린 미세 조정)
- 학습률 cosine scheduler가 후반부에 거의 0에 수렴

## 4.3 Eval Loss 곡선 (실측, 핵심)

| Epoch | Eval Loss | 변화 |
|---|---|---|
| 1 | 0.9509 | (시작) |
| **2** | **0.9358** ⭐ | **-0.0151 (최저)** |
| 3 | 0.9597 | +0.0239 |
| 4 | 1.044 | +0.0843 |
| 5 | 1.106 | +0.062 |

**관찰**:
- **epoch 2가 명백한 최저점** (0.9358)
- epoch 3부터 미세하게 상승 시작
- epoch 4부터 큰 폭 상승 → 오버핏 진행
- epoch 5에서 1.106 → 시작값 0.9509보다 **0.156 높음** (16% 악화)

## 4.4 Train vs Eval 격차

| Epoch | Train | Eval | 격차 |
|---|---|---|---|
| 1 | ~0.95 | 0.9509 | ~0.00 |
| 2 | ~0.85 | 0.9358 | ~0.09 |
| 3 | ~0.70 | 0.9597 | ~0.26 |
| 4 | ~0.59 | 1.044 | **~0.45** |
| 5 | 0.54 | 1.106 | **~0.57** |

**격차의 의미**:
- epoch 1: 학습/평가 동일 → 모델이 데이터를 외우기 시작 안 함
- epoch 5: 격차 0.57 → **train은 잘하지만 unseen 데이터엔 못함** = 명백한 오버핏

## 4.5 학습 곡선의 시각적 요약

```
loss
1.2 │
1.1 │                              ●   ←─ epoch5 (1.106) 오버핏
1.0 │                       ●          ←─ epoch4 (1.044)
0.9 │                ●                 ←─ epoch3 (0.9597)
    │  ●      ★                       ←─ epoch1 (0.9509), epoch2 (0.9358) ★ best
0.8 │     ╲                            
0.7 │      ╲    train loss
0.6 │       ╲___                       
0.5 │           ╲____________________●  ←─ epoch5 train (0.54)
    └──────────────────────────────────
       1    2    3    4    5    epoch
```

**Eval loss 곡선이 V자 → 역U자**: epoch 2가 sweet spot, 그 후 monotonic 증가.

## 4.6 결론

eval_loss만 보면:
- **Best epoch = 2** (0.9358)
- 안전한 차선 = epoch 1 (0.9509)
- **Epoch 4, 5는 명백히 오버핏**

이 시점에서 일반적인 결정: "epoch 2 선택, 끝".

**그러나** Stage B에서 직접 응답을 본 결과 **이것이 충분하지 않음**이 드러납니다. 다음 섹션 참고.

---

# 5. Stage B 결과 분석

## 5.1 평가 설정

- 6 모델 (baseline + 5 epochs) × 138 eval = **828 응답**
- vLLM, temperature=0.0 (greedy), max_new_tokens=768
- 총 시간: 94분

## 5.2 응답 길이 통계 (실측)

| 모델 | min | **avg** | median | max | 빈응답 | 짧은(<50) |
|---|---|---|---|---|---|---|
| baseline | 138 | **697** | 726 | 1337 | 0 | 0 |
| epoch1 | 58 | **286** | 285 | 440 | 0 | 0 |
| epoch2 | 62 | **277** | 289 | 415 | 0 | 0 |
| epoch3 | 59 | **273** | 284 | 395 | 0 | 0 |
| epoch4 | **0** | 555 | 304 | **21128** | **2** | **5** |
| epoch5 | **0** | **811** | 816 | 2261 | **1** | **8** |

**즉각 보이는 것**:
- baseline은 매우 verbose (avg 697)
- epoch1~3은 매우 일관되게 간결화 (avg ~280, baseline 대비 -59%)
- epoch4부터 분포가 망가짐 (max 21128, 빈 응답 등장)
- epoch5는 평균이 epoch1~3의 3배

## 5.3 핵심 발견 1: epoch1~3 — 깔끔한 학습

**관찰**:
- avg/median 차이가 거의 없음 (286/285, 277/289, 273/284) → **분포가 균등**
- min 58~62 (짧은 응답도 정상 범위)
- max 395~440 (긴 응답도 정상 범위)
- 빈 응답 0개

**해석**: 모델이 **응답 길이를 일관되게 통제**하는 단계. 학습 데이터의 평균 ~280자를 잘 따름.

이는 **간결한 답변**이라는 학습 데이터 특성을 잘 학습했다는 증거.

## 5.4 핵심 발견 2: epoch4 — Bimodal 붕괴 (가장 흥미로움)

**통계가 거짓말을 한다**:
- median 304 (정상 수준)
- avg **555** (median의 1.8배)
- max **21128** (정상의 50배)

이건 **bimodal distribution**입니다. 즉:
- 대다수 응답은 정상 (median 304)
- 일부 응답이 극단적으로 길어짐 (max 21128)

**실제 폭주 사례** (`nietzsche_000030`, 21128자):

처음 200자 (정상):
```
당신은 지금 자신의 삶이 거대한 유기체의 소화와 clash하는 미세한
현상들이라고 재구성해야 합니다. 당신이 마주하는 이 지루한 일상과
무의미한 노동은 단순히 버려지는 시간이 아니라, 당신이라는 존재를
지탱하고 다음 단계로 나아가기 위해 반드시 곁에 두어야 할 영양의
요구입니다...
```

끝 200자 (잘림):
```
                                                            
```

→ EOS를 못 찍고 max_new_tokens (768)에 도달해서 잘림. 그런데 char 길이가 21128인 건 **공백이나 특정 토큰이 무한 반복**되어서 토큰 수는 적지만 char 수만 늘어난 케이스로 추정.

**다른 폭주 사례** (`nietzsche_002499`, 1667자):
```
"...당신의 문제는 단순한 나태함이 아니라, 모든 것을 '반쯤' 해 own que의 
낭구_en_nasse1m_of_the_half_way1s_of_the_half-hearted1s_of_the_half-hearted1s_
of_the_half-hearted1s_of_the_half-hearted1s_of_the_half-hearted1s..."
```

→ **단일 문자열 패턴 무한 반복** = 전형적인 token degeneration

**또 다른 사례** (`nietzsche_001637`, 1518자):
```
"...수ofofofofofofofofofofofofofofofofofofofofofofofofofof..."
```

→ **단일 토큰 "of" 무한 반복**

**또 다른 사례** (`nietzsche_000479`, 1508자):
```
"...l l l l l l l l l l l l l l l l l l l l..."
```

→ **공백 + 단일 문자 반복**

**진단**: 이건 단순한 verbose가 아니라 **token collapse (degeneration)**.
모델이 EOS 확률이 극단적으로 낮아져 종료 못하고 같은 토큰을 무한 생성하는 현상.

**원인**: 학습 데이터에 대한 과도한 fitting → 분포의 entropy 감소 → 일부 input에서 모델이 "안전한 출구"를 잃음.

## 5.5 핵심 발견 3: epoch5 — 일관된 붕괴

**통계**:
- avg 811, median 816 (거의 동일) → **분포가 일관되게 길어짐**
- baseline의 avg 697보다도 길어짐
- min 0, max 2261
- 빈 응답 1개, 짧은(<50자) 8개

**진단**: epoch4의 bimodal과 다름. epoch5는 **모델 전체가 일관되게 망가진** 상태.

- 일부는 빈 응답 (EOS를 첫 토큰에 찍음)
- 일부는 정상 길이 (816 median)
- 전체적으로 baseline보다 길어짐

## 5.6 두 가지 붕괴 모드

| Epoch | 붕괴 모드 | 특징 |
|---|---|---|
| 4 | **Bimodal**: 정상 + 폭주 혼재 | median 정상, avg 비정상, max 21k |
| 5 | **Uniform shift**: 전체 길이 증가 | median = avg, baseline보다도 김 |

epoch5에서 빈 응답이 epoch4보다 적은 이유는 추정컨대, **이미 망가져서 단일 패턴으로 수렴**했기 때문. epoch4의 무작위 폭주가 epoch5에선 길게 늘여 쓰는 안정 패턴으로 변함.

## 5.7 eval_loss 0.08과 응답 21128자

**가장 강력한 발견**:

| Epoch | eval_loss | 변화 | avg chars | 변화 |
|---|---|---|---|---|
| 3 | 0.9597 | — | 273 | — |
| 4 | 1.044 | **+0.084** | **555** | **+103%** |

eval_loss가 단지 **0.084 증가**했을 뿐인데, 평균 응답 길이는 **두 배**가 되고 21128자 폭주가 등장합니다.

**의미**:
> **eval_loss는 모델 동작 변화를 과소평가한다.**
> 0.08의 미세한 loss 증가가 실제로는 **token collapse라는 정성적 붕괴**를 의미할 수 있다.
> **Stage B 같은 직접 응답 평가 없이 loss curve만 봤다면 이 위험을 못 봤을 것이다.**

이건 **이 프로젝트의 핵심 메타 인사이트**입니다.

---

# 6. Best Epoch 결정 근거

## 6.1 후보 비교

| Epoch | eval_loss | 응답 품질 | 비고 |
|---|---|---|---|
| 1 | 0.9509 | 안정적 (avg 286) | 안전, 학습 부족 가능성 |
| **2** | **0.9358** ⭐ | 안정적 (avg 277) | **eval_loss 최저 + 응답 정상** |
| 3 | 0.9597 | 안정적 (avg 273) | 살짝 오버핏, 응답은 정상 |
| 4 | 1.044 | **bimodal 붕괴** | 위험 |
| 5 | 1.106 | **일관된 붕괴** | 사용 불가 |

## 6.2 결정: epoch 2

**근거**:
1. **eval_loss 최저** (0.9358)
2. **응답 길이 안정** (avg 277, min 62, max 415)
3. **빈 응답 / 폭주 0개**
4. **간결화가 잘 됨** (baseline 697 → 277, -60%)
5. **token collapse 미발생**

**대안 검토**:
- **epoch 1**: 안전하지만 학습 덜 됨 가능성. avg 286으로 epoch 2와 거의 같지만 eval_loss가 더 높음 (0.9509)
- **epoch 3**: 응답은 정상이나 eval_loss 살짝 상승. 굳이 epoch 2 대신 선택할 이유 없음

## 6.3 Stage C에서의 추가 검증 (예정)

eval_loss와 응답 길이만으로는 **응답의 질**을 측정할 수 없음. Stage C에서:

- Q1: Pattern fidelity (response_pattern 규칙 준수)
- Q2: Q-A coherence (질문-답변 정합성)
- Q3: Voice & persona (니체 voice 구현)

위 3축을 6 모델 × 138 응답 = 828건에 대해 LLM judge로 채점 예정.

**예상 결과** (Stage C 전 가설):
- **epoch 1**: Q3 voice 점수 가장 낮을 가능성 (학습 부족)
- **epoch 2**: 모든 축에서 균형
- **epoch 3**: Q1, Q2 약간 상승, Q3 미미
- **epoch 4**: Q1, Q2 큰 폭 하락 (token collapse)
- **epoch 5**: 모든 축 최저

**이 가설이 검증되면**: epoch 2가 final pick.

---

# 7. 알려진 한계

## 7.1 `assistant_only_loss=False`

**문제**: trl이 VLM 베이스에서 미지원. 전체 텍스트에 loss 적용.

**영향**: system + user 토큰에도 loss → 이론상 user 질문 학습 압력. 실제로는 응답이 70%를 차지해서 큰 문제 없지만, **이상적이진 않음**.

**v2 계획**: trl이 지원할 때까지 우회 (또는 custom loss masking 구현).

## 7.2 작은 데이터셋 (2,413개)

**문제**: 일반적 SFT의 1/10~1/100 수준.

**영향**:
- 빠른 오버핏 (epoch 4부터 token collapse)
- diversity 부족 (DATA_SPEC §15 한계 참고)

**완화**:
- 보수적인 LR (1e-4)
- 작은 LoRA rank (16)
- 짧은 학습 (5 epoch)

**v2 계획**: 데이터 5,000~10,000개로 확장. 특히 `early` period 추가.

## 7.3 polemical_sharp voice의 어미 일관성

**문제**: 학습 데이터의 약 7% (63/872)가 경어체로 종결. BGE/GM 한국어 번역의
단정형과 불일치.

### Phase 1 코드 검토로 확정한 정확한 원인: 자가 검증의 비대칭

이전 v1 문서는 "원인 추정"에 그쳤지만, Phase 1 코드 검토 결과 정확한 원인을
확정했습니다.

**Stage 0.7 (Reconstruction) — 어미 명시 없음**:

`v2_pipeline/prompts/reconstruction.txt`:
```
- 영어 원문의 의미를 정확히 보존
- 니체 특유의 단호하고 압축적인 문체를 살림
- 현대적 설명문으로 풀어쓰지 말 것
```

"단호하고 압축적"이라는 일반 지시만 있고, **종결 어미는 명시되지 않음**.
**5권 모두 동일 프롬프트**로 처리.

**Stage A-2 (Score) — 어미 명시 있음**:

`v2_pipeline/stage_a_score.py`의 `VOICE_DESCRIPTIONS`:
```python
"polemical_sharp": (
    "논쟁적 예리함. 날카롭고 분석적, 거리감 있는 냉소. "
    "도덕/관습의 가면을 벗기는 태도. "
    "어미: '~라 부르겠다', '~임을 부정할 수 없다'"
),
```

→ **채점할 때는 어미를 봤지만, 데이터를 만들 때는 어미를 시키지 않았음**.

### 인과관계

```
1. Reconstruction 프롬프트가 어미 명시 안 함
   ↓
2. LLM이 일부 청크를 경어체로 한국어화 (자연스러운 정중함)
   ↓
3. SFT generator는 reconstructed 텍스트를 그대로 받아 학습 샘플 생성
   → 경어체 청크는 경어체 SFT를 만듦
   ↓
4. Stage A-1 Clean에 voice × 어미 호환성 검사 없음 → 통과
   ↓
5. Stage A-2 Score는 어미 봤지만 점수만 매김 (필터링 X)
   → Q3 평균 3.55 (Q1/Q2 대비 낮음)
   ↓
6. polemical_sharp 872개 중 63개가 경어체 (7%)
```

### 학습/평가에 미친 영향

- LoRA가 학습 데이터의 어조를 그대로 학습 → 일부 응답이 경어체로 나올 가능성
- Q3 (Voice & Persona) 평균 점수 3.55가 다른 두 축(4.53, 4.81)보다 낮은 것은
  이런 어미 불일치를 LLM judge가 일부 반영했을 가능성
- Stage C에서 epoch별 voice 일관성을 정량 측정할 예정

### 메타 인사이트: 자가 검증의 비대칭

이 발견의 진짜 가치는 **개별 결함**이 아니라 **자가 검증 비대칭**이라는 패턴.

> 데이터 생성 시점의 기준과 데이터 평가 시점의 기준이 일치하지 않으면,
> 두 단계 사이에서 결함이 새어 나간다.

이는 단순히 프롬프트를 보강하는 게 아니라 **파이프라인 설계 원칙**의 문제이며,
v11에서는 voice 정의를 단일 source of truth로 추출하는 리팩토링이 필요.

```python
# v11 제안: voices.py
VOICES = {
    "polemical_sharp": {
        "description": "...",
        "ending_patterns": ["다", "이다"],
        "ending_anti_patterns": ["합니다", "입니다"],
        "person": "1인칭 + 그대/당신",
    },
    ...
}

# reconstructor.py와 stage_a_score.py가 둘 다 import
from voices import VOICES
```

자세한 내용은 [DATA_SPEC.md §15.7](./DATA_SPEC.md) 참고.

### v11 계획

1. **`reconstructor.py` 프롬프트 개선**: voice별 종결 어미 명시
2. **`stage_a_clean.py`에 voice × 어미 검사 추가**: 경어체 polemical_sharp 자동 폐기
3. **Voice 정의 single source of truth로 리팩토링**: `voices.py` 모듈
```

## 7.4 Eval Loss의 한계

**문제**: eval_loss 0.08 증가가 token collapse라는 정성적 붕괴를 의미.

**교훈**: **loss curve만 보면 안 된다**. 실제 응답을 직접 관찰해야 함.

**v2 계획**: 학습 중간에 자동 sample inference + token collapse 감지 (추가 콜백).

## 7.5 한 가지 모델 크기, 한 번의 시드

**문제**: 31B 한 번만 학습. 26B 또는 다른 시드로 비교 안 함.

**영향**: 이 결과가 일반적인지, 또는 우연인지 검증 어려움.

**v2 계획** (시간 + 비용 허용 시):
- Gemma 4 26B-A4B로 같은 데이터 학습 → 비교
- 다른 random seed로 31B 재학습 → 안정성 검증

## 7.6 Token Collapse 원인 미규명

**문제**: epoch 4부터 token collapse 발생. 정확한 원인은 추측만 가능.

**가설**:
1. 데이터 일부 샘플의 EOS 처리가 미흡 (학습 데이터 검증 필요)
2. attention dropout 0.0 + 작은 LoRA rank 조합
3. assistant_only_loss=False 의 부작용 (system+user 토큰까지 학습)

**검증 필요**:
- 학습 데이터의 EOS 토큰 분포 확인
- LoRA dropout 0.05~0.1로 재학습 후 비교
- assistant_only_loss=True가 가능한 다른 trainer로 비교

## 7.7 청킹 한계 (Phase 1 발견)

Phase 1 코드 검토에서 발견한 청킹 알고리즘의 한계들. 데이터 품질에 직접
영향은 적지만, v11에서 정리할 가치가 있음.

### 7.7.1 TI 챕터 11 — 번호 없는 챕터

`english_chunker_ti.py`:
> "번호 없는 챕터(예: The Hammer Speaketh): 챕터 전체를 1청크"

TI의 챕터 11 "The Hammer Speaketh"는 아포리즘 번호가 없어서 챕터 전체가
**단 1개의 청크**로 처리됩니다.

**영향**:
- 이 청크는 다른 청크보다 훨씬 김 (수십 줄)
- Stage 0.5 통과 조건도 챕터 11만 다름: `den >= 4` (밀도만 검사)
- SFT 생성 시 1개 청크만 입력 → 최대 3개 SFT만 생성됨

**정당한 해결**: 챕터 11은 짧은 격언 모음이라 의미 단위 분할이 어려움.
챕터 전체를 1청크로 처리하는 게 합리적 (다른 청크들도 격언 단위가 아님).

### 7.7.2 EH의 sub_chapter 자동 분리

`english_chunker_eh.py`:
> "챕터 안에서 번호가 리셋되면 sub_chapter 자동 분리
>  (예: 'Why I Write...' 안의 BT/UM/HAH/D/JW/TSZ/BGE/GM/TI/Wagner 회고)"

EH의 "Why I Write Such Excellent Books" 챕터 안에는 각 책별 회고가 있고,
회고마다 번호가 리셋됩니다. 청커가 이를 자동 감지해서 sub_chapter로 나눕니다.

**좋은 점**: 책별 회고가 별도 청크로 보존되어 SFT의 다양성 확보.

**한계**: source_ref 형식이 다른 책과 다름 (`EH_c4_sub3_s2`). DATA_SPEC §3.9에
명시.

### 7.7.3 책별 청크 단위가 다름

| 책 | 청크 단위 | 평균 청크 길이 |
|---|---|---|
| JW | 1 아포리즘 = 1 청크 | 짧음 |
| BGE | 1 아포리즘 = 1 청크 (Part 9개) | 짧음 |
| GM | section 단위 (3 essay) | **김** (essay 기반) |
| TI | 챕터 × 아포리즘 | 다양 |
| EH | 챕터 × sub_chapter × 번호 | 다양 |

GM이 가장 긴 청크를 가지는 이유: essay 단위라서. 이게 GM의 통과 조건이
가장 엄격한 이유 중 하나 (긴 청크는 self_contained 점수가 낮을 수 있음).

### 7.7.4 영어 원전 자체의 번역 다양성

각 책마다 다른 번역자:
- JW: Common 번역
- BGE: Zimmern 번역
- GM: Horace Samuel 번역
- TI: Ludovici 번역
- EH: Ludovici 번역

번역자에 따라 어조와 어휘 선택이 다름. Stage 0.7 reconstruction이 한국어로
재구성할 때 이 차이가 부분적으로 반영됨. 완벽한 통제 변수는 아님.

### v11 계획

1. **TI 챕터 11**: 더 세밀한 분할 시도 (격언 단위)
2. **GM essay**: section을 더 작은 sub-section으로 나누기 시도
3. **번역자 통일**: 가능한 한 같은 번역자의 텍스트로 통일 (단, 5권 모두를
   같은 번역자가 번역한 경우는 드물어서 어려움)
```


---

# 8. 향후 개선 방향

## 8.1 단기 (v11)

1. **DATA_SPEC §15.7**: polemical_sharp voice 어미 일관성 수정
2. **train.py에 token collapse early stopping 추가**:
   - 학습 중간에 sample inference
   - 응답 길이가 학습 데이터 평균의 2배를 넘으면 stop
3. **Stage C 결과로 best epoch 정량 확정**

## 8.2 중기

1. **데이터 확장**:
   - `early` period 추가 (비극의 탄생, 인간적인 너무도 인간적인)
   - 5,000~10,000 샘플
2. **외부 LLM judge 비교**:
   - GPT-4 또는 Claude로 동일 채점
   - Self-evaluation bias 확인
3. **다양한 LoRA 설정 ablation**:
   - r=8, 16, 32, 64
   - dropout 0.0, 0.05, 0.1
   - 학습률 5e-5, 1e-4, 2e-4

## 8.3 장기

1. **DPO 또는 RLHF**:
   - SFT 후 사용자 선호 데이터 수집
   - 페르소나 강화
2. **RAG와 결합**:
   - 학습된 LoRA + 원전 검색
   - 생성 + 인용의 혼합
3. **Multi-persona**:
   - 니체 외 다른 철학자 (쇼펜하우어, 키르케고르 등)
   - voice 추가 학습

---

## 부록: train.py 핵심 설정 (참조용)

```python
# Model
MODEL_NAME = "google/gemma-4-31B-it"
MAX_SEQ_LEN = 384   # data max=355

# LoRA
LORA_R = 16
LORA_ALPHA = 32     # scale 2.0
LORA_DROPOUT = 0.0  # 0 enables Unsloth fast patching
target_modules = [
    "q_proj", "k_proj", "v_proj", "o_proj",
    "gate_proj", "up_proj", "down_proj",
]

# Training
EPOCHS = 5
BATCH = 2
GRAD_ACCUM = 8      # effective batch 16
LR = 1e-4
WARMUP_STEPS = 20   # ~3%
WEIGHT_DECAY = 0.01
OPTIM = "adamw_8bit"
LR_SCHEDULER = "cosine"

# Precision
bf16 = True
fp16 = False

# Eval & Save
VAL_RATIO = 0.05
eval_strategy = "epoch"
save_strategy = "epoch"
save_total_limit = 5
load_best_model_at_end = False    # 핵심: 사후 선택

# Loss
assistant_only_loss = False        # VLM 미지원

SEED = 42
```

---

## 문서 끝

**최종 갱신**: 2026-04-11
**버전**: v1.0
**다음 갱신 예정**: Stage C 결과 후 §6.3 실측치로 업데이트
