# 새 LLM 세션을 위한 온보딩

> **이 파일을 가장 먼저 읽으세요.**
>
> 이 문서는 새 Claude(또는 다른 LLM) 세션이 이 프로젝트에서 작업을 이어가기 위한
> **진입점**입니다. 30초 안에 컨텍스트를 잡고, 5분 안에 작업을 시작할 수 있도록
> 설계되었습니다.

---

# 30초 요약

**프로젝트**: 니체 페르소나 한국어 sLLM 캡스톤 (학부 졸업 프로젝트)

**무엇을 만드는가**: 니체 5권의 영어 원전을 한국어 SFT 데이터셋으로 변환하고,
Gemma 4 31B에 LoRA로 학습시켜 니체 페르소나 상담 sLLM을 만듦.

**현재 상태** (2026-04-11 기준):
- ✅ 데이터 파이프라인 완료 (Stage 0 ~ Stage A)
- ✅ LoRA 학습 완료 (5 epochs, 1h 9m)
- ✅ Stage B 평가 응답 생성 완료 (828 응답)
- 🟡 **Stage C (LLM judge 채점) 진행 예정**
- 🟡 **발표 자료 준비 중**

**발표일**: **2026-04-13** (남은 시간 확인 필요!)

**작업자**: 황철희 (한국어 존댓말 + 가끔 반말, 페어 프로그래밍 스타일)

**Repo**: https://github.com/HwangChulHee/nietzche-sllm-project

---

# 1분: 프로젝트가 어디까지 왔나

## 1.1 완료된 것 ✅

| 단계 | 상태 | 결과물 |
|---|---|---|
| Stage 0 (청킹/필터/재구성/SFT 생성) | ✅ | 2,780 candidates |
| Stage A (Clean/Score/Dedup/Select) | ✅ | train 2,413 + eval 138 |
| LoRA 학습 (5 epochs) | ✅ | 5 체크포인트 + HF Hub 업로드 |
| Stage B (응답 생성, 6 모델 × 138) | ✅ | 828 응답 |
| 모든 작업 문서화 (6 문서) | ✅ | `ml/docs/` |
| **문서 정정 작업 (Phase 1~5)** | ✅ | DATA_SPEC v10.0.2, 34개 항목 정정 |

## 1.2 진행 중/예정 🟡

- Stage C (LLM judge 채점)
- 발표 자료 (PPT)

## 1.3 핵심 발견 (이 프로젝트의 메타 인사이트)

1. **학습이 응답을 60% 간결화시킴** — baseline 697자 → epoch 1~3 ~280자
2. **epoch 4부터 token collapse** — 단일 토큰 무한 반복, 21,128자 폭주 등
3. **eval_loss는 거짓말한다** — eval_loss +0.084가 실제론 응답 길이 +103%를 의미
4. **데이터 검증 발견**: polemical_sharp voice 7%가 어미 일관성 결함 (DATA_SPEC §15.7)
5. **자가 검증 비대칭 (Phase 1 발견)**: 데이터 생성 시점(reconstruction.txt)과 평가 시점(stage_a_score.py VOICE_DESCRIPTIONS)의 voice 정의가 달랐음. 후자만 어미를 명시. 이게 4번 결함의 정확한 원인 — 단순 버그가 아닌 파이프라인 설계 원칙의 문제. v11에서 voice 정의를 single source of truth로 통합 예정.

---

# 2분: 어떤 문서를 읽을지

## 2.1 6개 핵심 문서

`ml/docs/` 안에 있습니다.

| 문서 | 답하는 질문 | 분량 |
|---|---|---|
| **DATA_SPEC.md** | 데이터셋이 어떻게 생겼나? 필드/분포/생성 규칙은? | ~50K |
| **ARCHITECTURE.md** | 이 프로젝트는 뭐로 구성되어 있고 어디에 뭐가 있나? | ~30K |
| **PIPELINE.md** | 어떻게 처음부터 끝까지 돌리나? 명령어는? | ~22K |
| **SFT_STRATEGY.md** | 왜 이렇게 학습했나? 결과를 어떻게 해석? | ~30K |
| **ENVIRONMENTS.md** | venv 두 개? 함정은 뭐? 새 pod 설정은? | ~22K |
| **RESULTS.md** | 결과 파일이 어디 있고 어떻게 검증? | ~25K |

## 2.2 상황별 진입점

### "이 프로젝트가 뭐 하는 건지 알고 싶다"
1. 이 파일 (LLM_ONBOARDING.md) — 지금 이 문서
2. `ARCHITECTURE.md` §1 (한 페이지 요약)

### "데이터셋에 대해 알고 싶다"
- `DATA_SPEC.md` (전체)
- 또는 빠르게: `RESULTS.md` §2

### "학습 결과 보고 싶다"
- `RESULTS.md` §3 (학습) + §4 (Stage B)
- 깊게: `SFT_STRATEGY.md` §4-5

### "코드/파일 어디 있는지 모르겠다"
- `ARCHITECTURE.md` §3 (디렉토리 구조), §4 (컴포넌트 매핑), §5 (자산 위치)

### "뭔가 돌리고 싶다"
- `PIPELINE.md` (해당 단계 섹션)

### "환경 문제, 에러"
- `ENVIRONMENTS.md` §7 (12개 함정 카탈로그)

### "발표 자료 만들 재료"
- `RESULTS.md` 부록 (5 슬라이드 매핑)
- `SFT_STRATEGY.md` §5 (token collapse 발견)

### "데이터셋 자체에 대한 한계"
- `DATA_SPEC.md` §15 (7개 한계)

### "Stage C 진행"
- `PIPELINE.md` §6 (예정 명령)
- `SFT_STRATEGY.md` §6 (best epoch 가설)
- `RESULTS.md` §5 (placeholder + 예상 결과)

## 2.3 5분 ramp-up 추천 순서

새 LLM 세션이 5분 안에 작업을 시작하려면:

1. **이 파일** (LLM_ONBOARDING.md) — 30초
2. **ARCHITECTURE.md §1, §3** — 1분 (전체 그림, 디렉토리)
3. **RESULTS.md §1** — 1분 (모든 결과 한 페이지)
4. **DATA_SPEC.md §1, §3.6, §15.7** — 1분 (데이터셋 핵심)
5. **사용자 질문에 따라 해당 문서 깊게** — 1.5분

---

# 3분: 환경 빠른 설정

## 3.1 새 pod 시작 시 (체크리스트)

```bash
# 1. Git safe directory (pod 재시작마다 필요!)
git config --global --add safe.directory /workspace/nietzche-sllm-project

# 2. 환경 변수
export PIP_CACHE_DIR=/workspace/.cache/pip
export TMPDIR=/workspace/tmp
export HF_HOME=/workspace/.cache/huggingface
export PATH="/root/.local/bin:$PATH"

# 3. 프로젝트로 이동
cd /workspace/nietzche-sllm-project/ml

# 4. 현재 상태 확인
git log --oneline -10
nvidia-smi 2>/dev/null || echo "CPU 모드"
df -h /workspace | tail -1
```

## 3.2 venv 활성화

**중요**: 이 프로젝트는 **venv가 두 개**입니다. 작업에 따라 다른 걸 써야 합니다.

```bash
# 데이터 작업, 평가 추론, judge 서버
source /workspace/nietzche-sllm-project/ml/.venv/bin/activate

# LoRA 학습, merge
source /workspace/nietzche-sllm-project/ml/finetune/.venv/bin/activate

# 종료
deactivate
```

| 작업 | venv | 이유 |
|---|---|---|
| 데이터 생성 / 평가 / judge | `ml` | vLLM 0.19 + torch 2.10 + transformers 5.5 |
| 학습 / merge | `finetune` | Unsloth + torch 2.6 + peft 0.18 |

자세한 사항: `ENVIRONMENTS.md`

## 3.3 GPU vs CPU 모드

이 pod는 **상황에 따라 GPU와 CPU를 전환**합니다:
- **문서 작업, 코드 편집** → CPU (저렴)
- **학습, 추론, judge 서버** → GPU (A100 80GB)

`nvidia-smi`로 현재 모드 확인. CPU 모드에서 GPU 작업을 시도하면 실패합니다.

---

# 4분: 자주 쓰는 명령

## 4.1 빠른 진행도 확인

```bash
cd /workspace/nietzche-sllm-project/ml

# 데이터 무결성
wc -l v2_data/sft_dataset/train.jsonl   # 2413
wc -l v2_data/sft_dataset/eval.jsonl    # 138

# Stage B 진행도
wc -l finetune/outputs/stage_b/responses.jsonl   # 828 (완료 시)

# 체크포인트 5개
ls finetune/outputs/nietzsche-lora-31b/checkpoint-*/adapter_model.safetensors 2>/dev/null | wc -l   # 5
```

## 4.2 git 작업

```bash
cd /workspace/nietzche-sllm-project

# 상태 확인
git status
git log --oneline -10

# 커밋 (변경 후)
git add <file>
git commit -m "..."
git push origin main
```

## 4.3 학습 로그 확인

```bash
cd /workspace/nietzche-sllm-project/ml

# 학습 마지막 50줄
tail -50 finetune/logs/train_31b_full.log

# Eval loss 곡선
grep "eval_loss" finetune/logs/train_31b_full.log

# Stage B 마스터 로그
tail -100 finetune/logs/stage_b_run.log
```

## 4.4 Stage B 응답 통계

```bash
source /workspace/nietzche-sllm-project/ml/.venv/bin/activate

python << 'PYEOF'
import json
import statistics
from collections import defaultdict

with open('/workspace/nietzche-sllm-project/ml/finetune/outputs/stage_b/responses.jsonl') as f:
    rows = [json.loads(l) for l in f]

by_model = defaultdict(list)
for r in rows:
    by_model[r['model_tag']].append(len(r['generated']))

print(f'{"model":<12} {"count":>6} {"avg":>8} {"median":>8} {"max":>8}')
print('-' * 50)
for model in ['baseline', 'epoch1', 'epoch2', 'epoch3', 'epoch4', 'epoch5']:
    if model not in by_model:
        continue
    lens = sorted(by_model[model])
    print(f'{model:<12} {len(lens):>6} {statistics.mean(lens):>8.0f} '
          f'{statistics.median(lens):>8.0f} {max(lens):>8}')
PYEOF

deactivate
```

## 4.5 특정 응답 비교 (모델별)

```bash
source /workspace/nietzche-sllm-project/ml/.venv/bin/activate

python << 'PYEOF'
import json

TARGET = 'nietzsche_000489'   # 변경 가능

with open('/workspace/nietzche-sllm-project/ml/finetune/outputs/stage_b/responses.jsonl') as f:
    rows = [json.loads(l) for l in f]

for r in rows:
    if r['sample_id'] != TARGET:
        continue
    print(f"\n=== {r['model_tag']} ({len(r['generated'])} chars) ===")
    print(r['generated'][:400])
PYEOF

deactivate
```

---

# 5분: 절대 하지 말 것 ⚠️

## 5.1 데이터 재생성 금지 ⚠️⚠️⚠️

**발표 전에는 절대로 Stage 0 ~ Stage A를 재실행하지 마세요.**

```bash
# ❌ 절대 실행 금지
python v2_pipeline/sft_generator.py        # candidates.jsonl 덮어씀
python v2_pipeline/stage_a_clean.py        # cleaned.jsonl 덮어씀
python v2_pipeline/stage_a_score.py        # scored.jsonl 덮어씀
python v2_pipeline/stage_a_select.py       # train.jsonl, eval.jsonl 덮어씀
```

**왜**: LoRA 학습이 현재 `train.jsonl` (2,413개)에 fitted되어 있습니다.
재생성하면 데이터가 바뀌고, 모든 학습/평가 결과가 무효화됩니다.

**LLM 채점은 결정적이지 않음** (temperature=0.2). 같은 명령을 다시 돌려도 결과가
달라질 수 있습니다.

## 5.2 venv 병합 금지

```bash
# ❌ 시도하면 시간 낭비
pip install vllm unsloth   # torch 버전 충돌로 깨짐
```

**왜**: vLLM 0.19는 torch 2.10을 요구하고, Unsloth는 torch 2.6을 강제합니다.
이미 시도했고 둘 다 깨졌습니다. ENVIRONMENTS.md §1.1 참고.

## 5.3 LoRA 체크포인트 삭제 금지

```bash
# ❌ 절대 실행 금지
rm -rf finetune/outputs/nietzsche-lora-31b/
```

**왜**: 4.4GB. 재학습 시 1시간 9분 + GPU 비용. HF Hub에 백업되어 있긴 하지만
다운로드 + 재배치도 시간 걸림.

**HF Hub**: `banzack/nietzsche-gemma4-31b-lora` (private, 5 branches)

## 5.4 Stage B 결과 삭제 금지

```bash
# ❌ 발표 전에 절대 실행 금지
rm -f finetune/outputs/stage_b/responses.jsonl
```

**왜**: 828개 응답을 다시 생성하려면 94분 + GPU 비용. Stage C 채점의 입력이며,
발표의 핵심 데이터입니다.

## 5.5 Gemma 4를 peft로 직접 merge 시도 금지

```python
# ❌ Gemma4ClippableLinear 에러 발생
from peft import PeftModel
model = PeftModel.from_pretrained(...)
merged = model.merge_and_unload()
```

**왜**: peft 0.18까지 Gemma 4의 신규 layer 미지원.

**해결**: Unsloth 사용 (이미 적용됨, `merge_one.py`):
```python
from unsloth import FastLanguageModel
model, tokenizer = FastLanguageModel.from_pretrained(checkpoint_path, ...)
model.save_pretrained_merged(output_dir, tokenizer, save_method="merged_16bit")
```

## 5.6 Unsloth chat template 사용 금지

```python
# ❌ system role이 user에 합쳐짐
from unsloth.chat_templates import get_chat_template
tokenizer = get_chat_template(tokenizer, chat_template="gemma-2")
```

**왜**: Gemma 4의 native template (`<|turn|>`)과 다른 Gemma 2/3 template (`<start_of_turn>`)이 적용됩니다. system message가 무시됩니다.

**해결**: 호출하지 않음. tokenizer가 가진 native template 사용. SFT_STRATEGY §3 참고.

---

# 6분: 작업자에 대한 정보

## 6.1 사용자 (황철희)

- **언어**: 한국어 (존댓말 기본, 친해지면 반말 섞음)
- **호칭**: "철희님" 선호
- **스타일**: 페어 프로그래밍 파트너. 솔직한 비판 환영. 데이터 품질에 엄격
- **선호**:
  - 자세한 설명 ("아주 자세하게")
  - 옵션 선택 후 진행 ("옵션 B로 해줘")
  - 메타 인사이트 의식적 추구
- **시간 압박**: 발표 4/13까지

## 6.2 사용자만의 개발 환경 특징

- **RunPod A100 80GB pod** (유럽 리전, 500GB volume)
- **GPU/CPU 전환**: 문서 작업은 CPU, 학습/추론은 GPU
- **HF Hub**: `banzack` 계정, private 모델
- **wandb**: `searchformaat` run

## 6.3 커뮤니케이션 팁

- **솔직히 말하기**: 데이터 결함이나 한계를 발견하면 솔직히 알려야 함
- **메타 인사이트**: 사용자가 자기 데이터/모델의 결함을 메타 관점으로 정리하는 것을
  좋아함 (예: polemical_sharp 어미 결함 → v11 계획)
- **확인 후 진행**: 큰 변경 전엔 항상 확인 받기
- **실행 가능한 명령**: 추상적 설명보다 복붙 가능한 명령 선호

---

# 7분: 다음에 할 일

## 7.1 즉시 우선순위 (발표 전)

1. **Stage C 파이프라인 작성**
   - `finetune/scripts/run_judge_server.sh`: judge vLLM 서버
   - `finetune/scripts/stage_c_score.py`: Q1/Q2/Q3 채점 (`stage_a_score.py` 복사 + 수정)
   - `finetune/scripts/stage_c_report.py`: 6 모델 × 3 axis breakdown
2. **Stage C 본 실행** (30~60분 예상)
3. **결과를 RESULTS.md §5에 채워넣기**
4. **발표 자료 (PPT) 작성**

## 7.2 발표 자료 핵심 슬라이드 (5장)

`RESULTS.md` 부록 참고:

1. **데이터 품질 관리** — Stage A 통과율 + LLM Judge 점수
2. **학습 곡선** — Eval loss V자 → 역U자
3. **간결화 효과** — baseline 697자 → epoch 2 277자 (-60%)
4. ⭐ **eval_loss는 거짓말한다** — token collapse 사례 (이게 가장 강력)
5. **Best epoch 선택** — epoch 2 = eval_loss 최저 + 응답 정상

## 7.3 발표 후 정리 작업

- `finetune/data/` 중복 제거 (train.py 수정 또는 symlink)
- HF Hub 모델 공개 전환 (현재 PRIVATE=True)
- v11 데이터셋 개선:
  - reconstructor.py voice별 어미 명시
  - stage_a_clean.py 어미 검사 추가
  - 기존 polemical_sharp 경어체 7% 재생성

---

# 8분: 빠른 컨텍스트 잡기 (선택)

작업을 시작하기 전에 추가로 컨텍스트가 필요하면:

```bash
# 1. 최근 git 작업
cd /workspace/nietzche-sllm-project
git log --oneline -20

# 2. 최근 학습/평가 로그
tail -30 ml/finetune/logs/train_31b_full.log
tail -30 ml/finetune/logs/stage_b_run.log

# 3. 현재 디렉토리 구조 (정리된 후)
cd /workspace/nietzche-sllm-project/ml
find . -maxdepth 2 -type d \
  -not -path '*/\.*' \
  -not -path '*/.venv*' \
  -not -path '*/__pycache__*' \
  -not -path '*/wandb*' | sort

# 4. 첫 학습 샘플 확인
head -1 v2_data/sft_dataset/train.jsonl | python -m json.tool | head -30
```

---

# 부록 A: 실수했을 때 복구

## A.1 git 작업 실수
```bash
# 마지막 커밋 취소 (변경사항 유지)
git reset --soft HEAD~1

# 마지막 커밋 메시지 수정
git commit --amend

# 강제로 원격 동기화 (최후의 수단)
git fetch origin
git reset --hard origin/main
```

## A.2 venv 깨졌을 때
```bash
# ml venv 재생성
cd /workspace/nietzche-sllm-project/ml
rm -rf .venv
python3.12 -m venv .venv
source .venv/bin/activate
# (PIPELINE.md §1.2 참고)

# finetune venv 재생성
cd /workspace/nietzche-sllm-project/ml/finetune
rm -rf .venv
bash setup.sh   # 자동 (10~15분)
```

## A.3 디스크 부족
```bash
# 안전한 정리
rm -rf /workspace/nietzche-sllm-project/ml/finetune/wandb/run-*
rm -rf /workspace/.cache/pip
rm -rf /workspace/nietzche-sllm-project/ml/finetune/outputs/merged/*

# 위험: 베이스 모델 재다운로드 필요
# rm -rf /workspace/.cache/huggingface/hub/models--google--gemma*
```

## A.4 Stage B 중간에 실패
```bash
# 자동 resume 가능. 그냥 다시 실행
cd /workspace/nietzche-sllm-project/ml
nohup bash finetune/scripts/run_stage_b.sh > finetune/logs/stage_b_run.log 2>&1 &

# 작동 방식: stage_b_generate.py가 시작 시 responses.jsonl을 읽고
# (sample_id, model_tag) 조합 이미 처리된 것을 자동 skip
```

---

# 부록 B: 핵심 숫자 외워두면 좋은 것

| 항목 | 값 |
|---|---|
| 베이스 모델 | Gemma 4 31B |
| 학습 데이터 | 2,413 train + 138 eval |
| 원전 책 | 5권 (JW, BGE, GM, TI, EH) |
| LoRA rank | 16 (alpha 32) |
| Epochs | 5 (모두 보존) |
| Best epoch | 2 (eval_loss 0.9358) |
| 학습 시간 | 1h 9m 54s |
| Stage B 응답 | 828 (6 모델 × 138) |
| Stage B 시간 | 94분 |
| 핵심 통계 | baseline 697자 → epoch2 277자 → epoch4 555자(붕괴) |

---

# 부록 C: 자주 묻는 질문 (예상)

### Q: "지금 어디까지 됐어?"
A: Stage A/학습/Stage B 모두 완료. Stage C와 발표 자료가 남음. 위 §1.1 참고.

### Q: "best epoch 뭐야?"
A: 잠정적으로 **epoch 2** (eval_loss 0.9358 + 응답 안정). Stage C 결과 후 확정.
SFT_STRATEGY §6 참고.

### Q: "데이터셋에 문제 있어?"
A: 7개 한계가 있음. 가장 흥미로운 건 polemical_sharp voice의 어미 일관성 결함 (7%).
DATA_SPEC §15 참고.

### Q: "이걸 어떻게 발표할 거야?"
A: 5장 슬라이드 outline이 RESULTS.md 부록에 있음. 핵심은 "eval_loss는 거짓말한다"
메타 인사이트.

### Q: "환경 어떻게 설정해?"
A: ENVIRONMENTS.md (자동 setup.sh + 12개 함정 카탈로그). venv 두 개임을 잊지 말 것.

### Q: "Stage C 어떻게 진행해?"
A: PIPELINE.md §6 + SFT_STRATEGY.md §6.3 가설 + RESULTS.md §5 placeholder.
스크립트 작성부터 시작 (`stage_c_score.py`, `stage_c_report.py`).

---

## 문서 끝

**최종 갱신**: 2026-04-11
**버전**: v1.0
**다음 갱신 예정**: Stage C 완료 후 §1.2 상태 업데이트, §7.1 우선순위 갱신

---

> **새 LLM에게**: 이 문서를 읽었다면, 이제 다른 문서들로 갈 준비가 됐습니다.
> 사용자의 첫 질문에 응답하기 전에 **최소한 ARCHITECTURE.md §1과 RESULTS.md §1을 더
> 읽으세요**. 그러면 거의 모든 질문에 정확히 답할 수 있을 것입니다.
>
> 그리고 한 가지: **이 프로젝트는 발표가 임박한 캡스톤입니다**. 작업의 모든 결정이
> "발표 전에 안전한가?"를 우선해야 합니다. 위험한 작업(데이터 재생성, 학습 재실행 등)
> 은 반드시 사용자 확인을 받으세요.
