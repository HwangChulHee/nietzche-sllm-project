# 파이프라인 실행 가이드

> 이 문서는 **명령어 중심**의 실행 가이드입니다.
> "이 프로젝트를 처음부터 끝까지 어떻게 돌리나"에 대한 답.
>
> 구조 이해: [ARCHITECTURE.md](./ARCHITECTURE.md)
> 데이터셋 명세: [DATA_SPEC.md](./DATA_SPEC.md)
> 환경 설정: [ENVIRONMENTS.md](./ENVIRONMENTS.md)

---

## 목차

1. [사전 준비](#1-사전-준비)
2. [Stage 0: 데이터 생성](#2-stage-0-데이터-생성)
3. [Stage A: 데이터 품질 관리](#3-stage-a-데이터-품질-관리)
4. [학습: LoRA 파인튜닝](#4-학습-lora-파인튜닝)
5. [Stage B: 응답 생성 평가](#5-stage-b-응답-생성-평가)
6. [Stage C: 채점](#6-stage-c-채점)
7. [재시작과 디버깅](#7-재시작과-디버깅)
8. [시간/리소스 측정](#8-시간리소스-측정)

---

# 1. 사전 준비

## 1.1 Pod 설정

**필수 사양**:
- GPU: A100 80GB (sm_80 이상)
- Volume: 500GB 이상 (`/workspace`)
- RAM: 200GB 이상 권장
- OS: Ubuntu 24.04 또는 호환

**RunPod 권장 템플릿**:
- "RunPod PyTorch 2.4 + CUDA 12.4" 기반
- Region: Europe (가용성 + 가격)

## 1.2 Git 클론 + 환경 설정

```bash
# 1. 작업 디렉토리 이동
cd /workspace

# 2. 클론 (또는 이미 있으면 pull)
git clone https://github.com/HwangChulHee/nietzche-sllm-project.git
cd nietzche-sllm-project

# 3. git safe directory (pod 재시작마다 필요)
git config --global --add safe.directory /workspace/nietzche-sllm-project

# 4. ml venv 생성 (vllm + transformers)
cd /workspace/nietzche-sllm-project/ml
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
# vllm + 의존성 설치 (자세한 사항은 ENVIRONMENTS.md 참고)
deactivate

# 5. finetune venv 생성 (Unsloth)
cd /workspace/nietzche-sllm-project/ml/finetune
bash setup.sh    # 모든 종속성 자동 설치 (~10분)
```

자세한 venv 설정과 함정은 [ENVIRONMENTS.md](./ENVIRONMENTS.md) 참고.

## 1.3 인증

```bash
# HuggingFace 로그인 (베이스 모델 다운로드 + LoRA 업로드)
huggingface-cli login

# wandb 로그인 (학습 추적, 선택)
cd /workspace/nietzche-sllm-project/ml/finetune
poetry run wandb login
```

## 1.4 환경 변수

`~/.bashrc`에 추가 (또는 매번 export):

```bash
export PIP_CACHE_DIR=/workspace/.cache/pip
export TMPDIR=/workspace/tmp
export HF_HOME=/workspace/.cache/huggingface
export PATH="/root/.local/bin:$PATH"
```

## 1.5 디렉토리 사전 점검

```bash
cd /workspace/nietzche-sllm-project/ml

# 원전 5권 존재 확인
ls -la v2_data/english_raw/
# 5개 .txt 파일이 있어야 함

# venv 두 개 존재 확인
ls -la .venv/bin/python finetune/.venv/bin/python
```

---

# 2. Stage 0: 데이터 생성

> **목적**: 영어 원전 5권 → 한국어 SFT 후보 2780개 생성
>
> **venv**: `ml`
>
> **예상 시간**: 약 2~4시간 (LLM judge + 재구성 비용 큼)

**현재 상태**: 이미 완료되어 `v2_data/`에 결과물 보관됨. 재실행할 필요 없음.

> ⚠️ **데이터 재생성 주의**: Stage 0 ~ Stage A를 다시 돌리면 기존 데이터가 덮어써집니다. 발표 전이라면 절대 재실행하지 마세요. 현재 학습/평가가 의존하는 `v2_data/sft_dataset/{train,eval}.jsonl`이 변경되면 모든 결과가 무효화됩니다.

## 2.1 Stage 0: 원전 청킹

```bash
cd /workspace/nietzche-sllm-project/ml
source .venv/bin/activate

# 5권 청커 순차 실행 (각 책 전용 청커)
python v2_pipeline/english_chunker_gs.py    # JW (즐거운 학문) → 383 청크
python v2_pipeline/english_chunker_bge.py   # BGE (선악의 저편) → 296 청크
python v2_pipeline/english_chunker_gm.py    # GM (도덕의 계보) → 77 청크
python v2_pipeline/english_chunker_ti.py    # TI (우상의 황혼) → 151 청크
python v2_pipeline/english_chunker_eh.py    # EH (이 사람을 보라) → 66 청크

# 결과 검증 (expected_total과 비교)
python v2_pipeline/verify_chunks.py
```

**출력**: `v2_data/english_chunks/{bge,eh,gm,gs,ti}.jsonl` (총 973 청크)

**예상 시간**: 5분 미만 (단순 텍스트 처리, LLM 호출 없음)

## 2.2 Stage 0.7: 한국어 재구성 (필터보다 먼저!)

> ⚠️ **순서 주의**: 한국어 재구성이 LLM 필터보다 먼저 실행됩니다.
> 다음 단계의 LLM judge가 한국어 텍스트로 채점하기 때문입니다.

**선결**: vLLM judge 서버가 떠 있어야 함.

```bash
# 별도 터미널에서 judge 서버 띄우기 (이후 모든 LLM 단계에서 재사용)
cd /workspace/nietzche-sllm-project/ml
source .venv/bin/activate

vllm serve google/gemma-4-26B-A4B-it \
    --port 8000 \
    --max-model-len 4096 \
    --gpu-memory-utilization 0.85
```

서버 준비 후 (`curl http://127.0.0.1:8000/v1/models` 응답 확인):

```bash
# 새 터미널에서 재구성 실행
cd /workspace/nietzche-sllm-project/ml
source .venv/bin/activate

python v2_pipeline/reconstructor.py
```

**입력**: `english_chunks/*.jsonl` (973 청크)
**출력**: `reconstructed/*.jsonl` (973개, 1:1 매핑, `text_ko_reconstructed` 필드 추가)

**LLM 설정**: Gemma 4 26B, temperature 0.3, concurrency 16, retry 3

**프롬프트**: `v2_pipeline/prompts/reconstruction.txt` (5권 동일 프롬프트)

**예상 시간**: 1~2시간 (가장 비용 큰 단계)

**재시작 가능**: `aph_num` 기반 자동 skip. 중단 후 재실행 가능.

## 2.3 Stage 0.5: 5축 LLM 채점 + 책별 통과 조건

```bash
# vLLM judge 서버 그대로 유지
cd /workspace/nietzche-sllm-project/ml
source .venv/bin/activate

python v2_pipeline/track_filter.py
```

**입력**: `reconstructed/*.jsonl` (한국어로 재구성된 청크)
**출력**: `filtered/*.jsonl` (973 채점 결과 + passed/use_case 필드)

**LLM 설정**: Gemma 4 26B, temperature 0.2, max_tokens 150, concurrency 16

**5축 평가**:
- track_existential, track_philosophical, track_biographical (use_case 결정)
- self_contained, density (품질 게이트)

**책별 통과 조건**: 5권 모두 다름. 특히 TI는 챕터별 11가지 조건.
자세한 사항: [DATA_SPEC.md §9.4](./DATA_SPEC.md)

**예상 시간**: 30~60분

**책별 실측 통과율**:
```
JW:  376/383 (98.2%)
BGE: 274/296 (92.6%)
GM:   70/77  (90.9%)  ← 가장 엄격한 조건
TI:  143/151 (94.7%)
EH:   65/66  (98.5%)
Total: 928/973 (95.4%)
```

## 2.4 Stage 0.9: SFT 샘플 생성

```bash
python v2_pipeline/sft_generator.py
```

**입력**: `filtered/*.jsonl` (passed=True인 928개만 자동 필터)
**출력**: `sft_candidates/candidates.jsonl` (~2,780 SFT 샘플)

**핵심 메커니즘**:
- **청크당 3개**를 한 LLM 호출에 생성 (3번 호출 X)
- temperature **0.85** (다양성 우선)
- `USE_CASE_TO_PATTERNS` 매핑으로 패턴 제한
- voice별 system prompt **9개** 중 random.choice

**예상 시간**: 30~60분

# 3. Stage A: 데이터 품질 관리

> **목적**: 2780 candidates → 2551 selected (train 2413 + eval 138)
>
> **venv**: `ml`
>
> **예상 시간**: 약 30~60분 (Score 단계 LLM 호출 비중)

## 3.1 Stage A-1: Clean

```bash
cd /workspace/nietzche-sllm-project/ml
source .venv/bin/activate

python v2_pipeline/stage_a_clean.py
```

**입력**: `v2_data/sft_candidates/candidates.jsonl` (2780)
**출력**:
- `v2_data/sft_candidates/cleaned.jsonl` (2728)
- `v2_data/sft_candidates/cleaned_report.json`

**검사 항목**:
- enum 정규화 (자동 수정)
- 길이 제약
- 5-gram 표절 검사
- 위로 표현 차단
- invalid concept 검사

**예상 시간**: 1~2분 (LLM 호출 없음)

## 3.2 Stage A-2: Score

**선결**: vLLM judge 서버 (Stage 0.5와 동일)

```bash
# judge 서버가 떠 있는지 확인
curl http://127.0.0.1:8000/v1/models

python v2_pipeline/stage_a_score.py
```

**입력**: `cleaned.jsonl` (2728)
**출력**:
- `scored.jsonl` (2728, Q1/Q2/Q3 점수 + grade 필드 추가)
- `scored_report.json`

**채점 모델**: Gemma 4 26B-A4B (judge 서버)

**예상 시간**: 20~40분 (2728건 × 비동기 호출, 16 concurrency)

**파라미터**:
- temperature=0.2 (결정성 + 약간의 변동)
- 16 concurrency
- 최대 3회 재시도

## 3.3 Stage A-3: Dedup

```bash
python v2_pipeline/stage_a_dedup.py
```

**입력**: `scored.jsonl` (2728)
**출력**:
- `deduped.jsonl` (2725)
- `dedup_report.json`

**알고리즘**: A-centric MinHash + BGE-M3 임베딩 dedup

**예상 시간**: 5~10분 (BGE-M3 임베딩 계산)

## 3.4 Stage A-4: Select

```bash
python v2_pipeline/stage_a_select.py
```

**입력**: `deduped.jsonl` (2725)
**출력**:
- `v2_data/sft_dataset/train.jsonl` (2413)
- `v2_data/sft_dataset/eval.jsonl` (138)
- `v2_data/sft_dataset/select_report.json`

**알고리즘**: Stratified split (voice × question_type × pattern × use_case × difficulty × source)

**예상 시간**: 1~2분

## 3.5 Stage A 결과 검증

```bash
# 샘플 수 확인
wc -l v2_data/sft_dataset/train.jsonl   # 2413
wc -l v2_data/sft_dataset/eval.jsonl    # 138

# 분포 확인
python -c "
import json
from collections import Counter
with open('v2_data/sft_dataset/train.jsonl') as f:
    samples = [json.loads(l) for l in f]
print('Voice:', Counter(s['voice'] for s in samples))
print('Grade:', Counter(s['grade'] for s in samples))
"
```

## 3.6 학습 데이터 복사 (또는 symlink)

`train.py`가 `finetune/data/`를 참조하므로 sync 필요:

```bash
# 옵션 A: 단순 복사 (권장, 발표 전 안전)
cp v2_data/sft_dataset/train.jsonl finetune/data/train.jsonl
cp v2_data/sft_dataset/eval.jsonl  finetune/data/eval.jsonl

# 옵션 B: symlink (발표 후 권장)
# rm -rf finetune/data
# ln -s ../v2_data/sft_dataset finetune/data
```

---

# 4. 학습: LoRA 파인튜닝

> **venv**: `finetune`
>
> **모델**: Gemma 4 31B + LoRA r=16
>
> **예상 시간**: ~1시간 9분 (A100 80GB)

## 4.1 학습 설정 요약

| 파라미터 | 값 | 비고 |
|---|---|---|
| Base model | `google/gemma-4-31B-it` | bf16 |
| LoRA rank | 16 | |
| LoRA alpha | 32 | scale 2.0 |
| LoRA dropout | 0.0 | Unsloth fast patching |
| Target modules | q/k/v/o + gate/up/down | 7 modules |
| Max seq length | 384 | 데이터 max=355 |
| Epochs | 5 | 모든 체크포인트 보존 |
| Batch size | 2 | per device |
| Grad accumulation | 8 | effective batch 16 |
| Learning rate | **1e-4** | 작은 데이터셋 보수적 |
| LR scheduler | cosine | |
| Warmup | 20 steps | ~3% |
| Weight decay | 0.01 | |
| Optimizer | adamw_8bit | |
| Precision | bf16 | not 4bit |
| Val split | 5% | loss monitoring only |
| Seed | 42 | |

## 4.2 학습 전 sanity check (SMOKE 모드)

**권장**: 본 학습 전에 50 샘플 1 epoch로 환경 검증.

```bash
cd /workspace/nietzche-sllm-project/ml/finetune
source .venv/bin/activate

# Smoke test (50 샘플, 1 epoch, eval/save 없음)
SMOKE=1 poetry run python scripts/train.py
```

**예상 시간**: 5~10분

**확인 사항**:
- Chat template sanity check 4개 assertion 통과 (system/user/assistant 토큰 보존)
- 학습 loss 정상 감소
- GPU 메모리 ~70GB 사용
- 에러 없이 종료

## 4.3 본 학습

```bash
cd /workspace/nietzche-sllm-project/ml/finetune
source .venv/bin/activate

# nohup으로 백그라운드 실행 + 로그 저장
nohup poetry run python scripts/train.py \
    > logs/train_31b_full.log 2>&1 &

# PID 기록
echo $! > train.pid
echo "PID: $(cat train.pid)"

# 진행 모니터링 (별도 터미널)
tail -f logs/train_31b_full.log
nvidia-smi -l 5
```

**또는 wandb 대시보드에서 실시간 모니터링**: https://wandb.ai/{user}/nietzsche-sllm

## 4.4 학습 산출물

```
finetune/outputs/nietzsche-lora-31b/
├── checkpoint-144/    epoch 1 (~14분 후)
├── checkpoint-288/    epoch 2 (eval loss 최저)
├── checkpoint-432/    epoch 3
├── checkpoint-576/    epoch 4
├── checkpoint-720/    epoch 5
├── final/             trainer 자동 저장 (= epoch 5)
└── README.md          모델 카드
```

각 체크포인트 ~800MB. 총 약 4.4GB.

## 4.5 학습 완료 후

### Loss 곡선 확인 (wandb)

| Epoch | Train loss | Eval loss |
|---|---|---|
| 1 | ~0.98 | ~1.05 |
| 2 | ~0.78 | **~0.94** (최저) |
| 3 | ~0.65 | ~0.97 |
| 4 | ~0.58 | ~1.04 |
| 5 | ~0.54 | ~1.11 (오버핏) |

`load_best_model_at_end=False`이므로 모든 체크포인트 보존. Stage B로 사후 선택.

### HF Hub 업로드

```bash
cd /workspace/nietzche-sllm-project/ml/finetune
source .venv/bin/activate

# 5개 epoch 모두 업로드 (각각 별도 branch)
poetry run python scripts/upload_lora.py
```

**결과**: `https://huggingface.co/banzack/nietzsche-gemma4-31b-lora` (private)

각 epoch는 별도 branch로 저장:
- `epoch1`, `epoch2`, `epoch3`, `epoch4`, `epoch5`

---

# 5. Stage B: 응답 생성 평가

> **목적**: 6 모델(baseline + 5 epochs) × 138 eval = **828 응답** 생성
>
> **venv**: `ml` (추론) + `finetune` (merge)
>
> **예상 시간**: ~94분 (실측, vLLM 캐시 효과로 예상의 절반)

## 5.1 Stage B 흐름

```
1. baseline 평가         (ml venv)         → 138 응답
2. epoch1 merge          (finetune venv)   → merged/epoch1/ (62GB)
3. epoch1 평가           (ml venv)         → 138 응답
4. epoch1 merged 삭제    (디스크 회수)
5. epoch2 merge → 평가 → 삭제
6. epoch3 merge → 평가 → 삭제
7. epoch4 merge → 평가 → 삭제
8. epoch5 merge → 평가 → 삭제
```

각 epoch마다 merge → 평가 → 삭제 인터리브. 디스크 사용량을 62GB로 제한.

## 5.2 추론 설정

| 파라미터 | 값 | 비고 |
|---|---|---|
| Engine | vLLM 0.19 | PagedAttention |
| Max model len | 1280 | prompt ~400 + gen 768 + 여유 |
| Max new tokens | 768 | |
| Temperature | **0.0** | greedy (Stage A와 일치) |
| GPU mem util | 0.90 | |

## 5.3 본 실행 (오케스트레이션 스크립트)

```bash
cd /workspace/nietzche-sllm-project/ml

# 백그라운드 실행 + 마스터 로그
nohup bash finetune/scripts/run_stage_b.sh \
    > finetune/logs/stage_b_run.log 2>&1 &

echo $! > stage_b.pid

# 진행 모니터링
tail -f finetune/logs/stage_b_run.log
```

**스크립트가 자동으로 처리하는 것**:
- venv 전환 (ml ↔ finetune)
- 디스크 정리 (각 epoch 평가 후 merged 삭제)
- 모델별 로그 분리 (`stage_b_baseline.log`, `stage_b_epoch1.log`, ...)
- 시간 측정

## 5.4 모델별 단독 실행 (디버깅용)

오케스트레이션 없이 한 모델만 돌리고 싶을 때:

```bash
cd /workspace/nietzche-sllm-project/ml

# baseline (HF 모델 직접)
source .venv/bin/activate
python finetune/scripts/stage_b_generate.py \
    --model-tag baseline \
    --model-path google/gemma-4-31B-it
deactivate

# 또는 특정 epoch (이미 merged 되어 있어야 함)
# 1) merge 먼저
cd /workspace/nietzche-sllm-project/ml/finetune
source .venv/bin/activate
python scripts/merge_one.py --epoch 2
deactivate

# 2) 추론
cd /workspace/nietzche-sllm-project/ml
source .venv/bin/activate
python finetune/scripts/stage_b_generate.py \
    --model-tag epoch2 \
    --model-path /workspace/nietzche-sllm-project/ml/finetune/outputs/merged/epoch2
deactivate
```

## 5.5 산출물

```
finetune/outputs/stage_b/
├── responses.jsonl       (1.8M, 828 응답)
└── responses.jsonl.bak   (백업)

finetune/logs/
├── stage_b_run.log               (마스터 로그, 350K)
├── stage_b_baseline.log          (18K)
├── stage_b_epoch1.log ~ epoch5.log
└── merge_epoch2.log ~ epoch5.log
```

## 5.6 결과 통계

```bash
cd /workspace/nietzche-sllm-project/ml
source .venv/bin/activate

python finetune/scripts/stage_b_stats.py
```

**예상 출력**:
| 모델 | 평균 토큰 | 잘림률 |
|---|---|---|
| baseline | 489 | 5% |
| epoch1 | 162 | 0% |
| epoch2 | 156 | 0% |
| epoch3 | 153 | 0% |
| epoch4 | ~155 | 0% |
| epoch5 | 572 | **72%** (오버핏) |

---

# 6. Stage C: 채점

> **상태**: 작성 예정
>
> **목적**: Stage B 응답 828개를 LLM judge로 채점, breakdown 리포트 생성
>
> **venv**: `ml`
>
> **예상 시간**: 30~60분

## 6.1 계획

```bash
# 1. judge 서버 띄우기 (Stage A-2와 동일)
cd /workspace/nietzche-sllm-project/ml
source .venv/bin/activate
vllm serve google/gemma-4-26B-A4B-it --port 8000

# 2. Stage C 채점 (별도 터미널)
python finetune/scripts/stage_c_score.py
# → finetune/outputs/stage_c/scored.jsonl

# 3. Breakdown 리포트
python finetune/scripts/stage_c_report.py
# → finetune/outputs/stage_c/report.md
```

## 6.2 작성할 스크립트

| 스크립트 | 역할 | 기반 |
|---|---|---|
| `stage_c_score.py` | Q1/Q2/Q3 채점 | `stage_a_score.py` 복사 + 입력 변경 |
| `stage_c_report.py` | 6 모델 × 3 axis × breakdown | 신규 |

세부 구현은 Stage C 작성 시 별도 문서화 예정.

---

# 7. 재시작과 디버깅

## 7.1 학습 재시작

학습 도중 실패 시:

```bash
# 1. 상태 확인
ls finetune/outputs/nietzsche-lora-31b/checkpoint-*

# 2. 마지막 체크포인트 결정
# train.py는 자동 resume 미지원 → 수동으로 다시 시작

# 3. 또는 마지막 체크포인트부터 이어가기 (별도 수정 필요)
```

**현재 train.py는 resume 미지원**. 처음부터 재시작 필요.

## 7.2 Stage B 재시작

`stage_b_generate.py`는 **자동 resume 지원**:

```bash
# 그냥 다시 실행
bash finetune/scripts/run_stage_b.sh
```

**작동 방식**: `stage_b_generate.py`가 시작 시 `responses.jsonl`을 읽어서 `(sample_id, model_tag)` 조합 이미 처리된 것을 skip. 따라서 어느 시점에 중단되어도 재실행하면 이어집니다.

## 7.3 Merge 실패 디버깅

가장 흔한 에러: **`Gemma4ClippableLinear` 미지원**

```
TypeError: Cannot convert Gemma4ClippableLinear to peft module
```

**원인**: peft 0.18 이하가 Gemma 4의 신규 layer 미지원.

**해결**: Unsloth 사용 (이미 적용됨):
```python
# merge_one.py가 사용하는 방식
from unsloth import FastLanguageModel
model.save_pretrained_merged(merged_dir, tokenizer, save_method="merged_16bit")
```

## 7.4 vLLM 로딩 실패

**에러**: `cu130 build does not support driver 12.7`

**해결**: cu128 빌드 사용
```bash
pip install vllm==0.19.0 --extra-index-url https://download.pytorch.org/whl/cu128
```

자세한 사항은 [ENVIRONMENTS.md](./ENVIRONMENTS.md)

## 7.5 디스크 부족

```bash
# 1. merged 디렉토리 정리
rm -rf finetune/outputs/merged/epoch*

# 2. wandb 캐시 정리
rm -rf finetune/wandb/run-*

# 3. pip 캐시 정리
pip cache purge

# 4. HuggingFace 캐시 정리 (주의: 베이스 모델 재다운로드 필요)
rm -rf /workspace/.cache/huggingface/hub/models--google--gemma*
```

## 7.6 GPU 메모리 부족 (OOM)

학습 시:
```python
# train.py에서
BATCH = 1            # 2 → 1
GRAD_ACCUM = 16      # 8 → 16 (effective batch 유지)
```

추론 시:
```python
# stage_b_generate.py에서
GPU_MEM_UTIL = 0.85  # 0.90 → 0.85
MAX_MODEL_LEN = 1024  # 1280 → 1024
```

---

# 8. 시간/리소스 측정

## 8.1 단계별 시간

| 단계 | 예상 | 실측 (A100 80GB) |
|---|---|---|
| Stage 0 청킹 | 5분 | 3분 |
| Stage 0.5 필터 | 30~60분 | ~45분 |
| Stage 0.7 재구성 | 1~2시간 | ~90분 |
| Stage 0.9 SFT 생성 | 30~60분 | ~50분 |
| Stage A-1 Clean | 1~2분 | 1분 |
| Stage A-2 Score | 20~40분 | ~30분 |
| Stage A-3 Dedup | 5~10분 | 7분 |
| Stage A-4 Select | 1~2분 | 1분 |
| **학습 (5 epochs)** | 1~2시간 | **1시간 9분** |
| LoRA 업로드 | 5~10분 | 7분 |
| Stage B (전체) | 170~205분 | **94분** |
| Stage C (예상) | 30~60분 | — |

**총 데이터 + 학습 + 평가**: 약 8~10시간 (Stage 0부터)
**학습 + 평가만**: 약 3~4시간 (데이터가 이미 있을 때)

## 8.2 GPU 메모리 사용량

| 작업 | 메모리 | 비고 |
|---|---|---|
| 학습 (LoRA r=16, batch 2) | ~70GB | bf16, gradient checkpointing |
| Merge (Unsloth) | ~65GB | 일시적 피크 |
| Stage B 추론 (vLLM) | ~72GB | gpu_mem_util 0.90 |
| Judge 서버 (Gemma 26B-A4B) | ~55GB | gpu_mem_util 0.85 |

## 8.3 디스크 사용량

| 시점 | 누적 |
|---|---|
| Pod 시작 | 0 |
| venv 설치 후 | ~10GB |
| 베이스 모델 다운로드 후 | ~75GB |
| 학습 완료 (LoRA 5개) | ~80GB |
| Stage B 중 (merged 1개) | ~145GB |
| Stage B 완료 (정리 후) | ~80GB |

**핵심**: Stage B 도중 merged 디렉토리(62GB)가 일시적으로 점유. 인터리브 + 즉시 삭제로 관리.

## 8.4 비용 추정 (RunPod A100 80GB 기준)

A100 80GB 시간당 ~$1.5~2.0 가정:

| 작업 | 시간 | 비용 |
|---|---|---|
| 데이터 생성 (Stage 0~0.9) | ~3시간 | $4.5~6 |
| Stage A | ~40분 | $1~1.3 |
| 학습 | 1시간 9분 | $1.7~2.3 |
| Stage B | 94분 | $2.3~3.1 |
| Stage C | ~45분 | $1.1~1.5 |
| **총** | **~7시간** | **$10~14** |

---

## 부록: 빠른 명령 cheatsheet

### 새 pod에서 환경 복구
```bash
git config --global --add safe.directory /workspace/nietzche-sllm-project
cd /workspace/nietzche-sllm-project/ml
source .venv/bin/activate    # ml 작업
# 또는
source finetune/.venv/bin/activate    # 학습 작업
```

### 현재 진행도 빠른 확인
```bash
cd /workspace/nietzche-sllm-project/ml
wc -l v2_data/sft_dataset/train.jsonl                    # 2413
wc -l v2_data/sft_dataset/eval.jsonl                     # 138
wc -l finetune/outputs/stage_b/responses.jsonl           # 828 (Stage B 완료 시)
ls finetune/outputs/nietzsche-lora-31b/checkpoint-*/adapter_model.safetensors | wc -l   # 5
```

### 학습 로그 확인
```bash
tail -50 finetune/logs/train_31b_full.log
```

### Stage B 진행 확인
```bash
tail -50 finetune/logs/stage_b_run.log
ls finetune/logs/stage_b_*.log
```

### Git 상태 + 푸시
```bash
cd /workspace/nietzche-sllm-project
git status
git log --oneline -10
git push origin main
```

---

## 문서 끝

**최종 갱신**: 2026-04-11
**버전**: v1.0
**다음 갱신 예정**: Stage C 스크립트 작성 후 §6 확정
