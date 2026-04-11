# 환경 설정

> 이 문서는 **새 pod에서 환경을 재현**하기 위한 가이드 + **알려진 함정 카탈로그**입니다.
> 시행착오의 결과물이며, 새 LLM 세션이 같은 함정에 빠지지 않도록 하는 게 목적입니다.
>
> 실행 명령은 [PIPELINE.md](./PIPELINE.md), 구조는 [ARCHITECTURE.md](./ARCHITECTURE.md) 참고.

---

## 목차

1. [핵심 원칙: 두 venv 구조](#1-핵심-원칙-두-venv-구조)
2. [패키지 버전 매트릭스](#2-패키지-버전-매트릭스)
3. [ml venv 설치](#3-ml-venv-설치)
4. [finetune venv 설치](#4-finetune-venv-설치)
5. [환경 변수](#5-환경-변수)
6. [검증](#6-검증)
7. [알려진 함정 카탈로그](#7-알려진-함정-카탈로그)
8. [자주 쓰는 명령](#8-자주-쓰는-명령)

---

# 1. 핵심 원칙: 두 venv 구조

## 1.1 왜 두 개인가

**한 줄 요약**: torch 버전이 다르고 호환 불가능. vLLM은 torch 2.10을 요구하고, Unsloth는 torch 2.6을 강제하기 때문.

| venv | 용도 | torch | 핵심 의존성 |
|---|---|---|---|
| `ml/.venv/` | 데이터 생성, 평가 추론 | **2.10.0** | vllm 0.19, transformers 5.5 |
| `ml/finetune/.venv/` | LoRA 학습, merge | **2.6.0+cu124** | unsloth, peft 0.18 |

**병합 시도 = 시간 낭비**. 이미 시도했고, 둘 중 하나는 무조건 깨집니다.

## 1.2 어느 venv를 언제 쓰나

| 작업 | venv |
|---|---|
| Stage 0 청킹 | `ml` |
| Stage 0.5 3-Track 필터 (judge 서버 + 호출) | `ml` |
| Stage 0.7 한국어 재구성 (judge 서버 + 호출) | `ml` |
| Stage 0.9 SFT 생성 | `ml` |
| Stage A-1 Clean | `ml` |
| Stage A-2 Score (judge 서버 + 호출) | `ml` |
| Stage A-3 Dedup (BGE-M3 임베딩) | `ml` |
| Stage A-4 Select | `ml` |
| **LoRA 학습 (`train.py`)** | **`finetune`** |
| **LoRA merge (`merge_one.py`)** | **`finetune`** |
| Stage B 추론 (vLLM, `stage_b_generate.py`) | `ml` |
| HF Hub 업로드 (`upload_lora.py`) | `finetune` |
| Stage C 채점 (예정) | `ml` |

**핵심 원칙**:
- vLLM 추론 → `ml`
- Unsloth 학습/merge → `finetune`
- judge 서버는 `ml` (vLLM serve)

`run_stage_b.sh`는 `ml`과 `finetune`을 자동 전환합니다.

## 1.3 디렉토리

```
ml/
├── .venv/                       ⭐ ml venv (gitignore)
│   ├── bin/python
│   ├── bin/activate
│   └── lib/python3.12/site-packages/
├── pyproject.toml               poetry 1.x style
├── poetry.lock
│
└── finetune/
    ├── .venv/                   ⭐ finetune venv (gitignore)
    │   ├── bin/python
    │   ├── bin/activate
    │   └── lib/python3.12/site-packages/
    ├── pyproject.toml           PEP 621 style
    ├── poetry.lock
    ├── poetry.toml              in-project venv 설정
    └── setup.sh                 자동 설치 스크립트 (귀중)
```

---

# 2. 패키지 버전 매트릭스

**이 표는 실측 기반 (`pip list` 결과)이며, 모든 버전이 정확히 일치해야 호환됩니다.**

## 2.1 ml venv

| 패키지 | 버전 | 비고 |
|---|---|---|
| python | 3.12 | |
| torch | 2.10.0 | cu128 빌드 (cu130 X) |
| torchvision | 0.25.0 | |
| torchaudio | 2.10.0 | |
| **vllm** | **0.19.0** | PagedAttention |
| **transformers** | **5.5.0** | Gemma 4 지원 필수 |
| huggingface_hub | 1.10.1 | |
| sentence-transformers | 5.3.0 | BGE-M3용 |
| sentencepiece | 0.2.1 | |
| flashinfer-python | 0.6.6 | vLLM 가속 |
| flashinfer-cubin | 0.6.6 | |
| numpy | 2.2.6 | |
| pydantic | 2.12.5 | |
| tqdm | 4.67.3 | |

### 추가 의존성 (`ml/pyproject.toml`)

```toml
pymupdf = "^1.24.0"          # PDF 추출
pydantic = "^2.7.0"          # 데이터 검증
tqdm = "^4.66.0"
rich = "^13.7.0"             # 예쁜 로그
python-dotenv = "^1.0.0"
openai = "^2.0.0"            # vLLM/Ollama OpenAI 호환 API 클라이언트
httpx = "^0.27.0"
sentence-transformers = "^5.3.0"
kss = "^6.0.6"               # 한국어 문장 분리
pysbd = "^0.3.4"             # 영어 문장 분리
vllm = "^0.19.0"
```

### 개발 의존성

```toml
pytest = "^8.2.0"
ruff = "^0.4.0"
jupyter = "^1.0.0"
ipykernel = "^6.29.0"
```

## 2.2 finetune venv

| 패키지 | 버전 | 비고 |
|---|---|---|
| python | 3.12 | (3.13 미지원, 엄격) |
| **torch** | **2.6.0+cu124** | cu124 빌드 |
| torchvision | 0.21.0+cu124 | unsloth_zoo가 import |
| **xformers** | **0.0.29.post3** | Flash Attention fallback |
| **unsloth** | **2026.4.4** | git installed |
| **unsloth_zoo** | **2026.4.6** | unsloth 의존성 |
| **peft** | **0.18.1** | (Gemma 4 merge는 미지원, 경고만) |
| trl | 0.24.0 | SFTTrainer |
| accelerate | 1.13.0 | |
| bitsandbytes | 0.49.2 | adamw_8bit |
| **triton** | **3.2.0** | (3.3+ 호환 X) |
| **torchao** | **0.12.0** | ⚠️ 강제 다운그레이드 (0.13+은 torch 2.7 API 사용) |
| transformers | 5.5.0 | ml venv와 동일 |
| datasets | 4.3.0 | |
| wandb | 0.25.1 | |

### 핵심 의존성 (`finetune/pyproject.toml`)

```toml
[project]
name = "nietzsche-finetune"
requires-python = ">=3.12,<3.13"
dependencies = [
    "unsloth @ git+https://github.com/unslothai/unsloth.git",
    "wandb (>=0.25.1,<0.26.0)"
]
package-mode = false
```

**왜 의존성이 2개뿐인가**: Unsloth와 unsloth_zoo의 의존성 선언이 부실해서, 나머지 패키지(torch, peft, trl, bitsandbytes 등)는 `setup.sh`에서 **수동 설치**해야 합니다.

---

# 3. ml venv 설치

## 3.1 사전 조건

- Python 3.12
- Poetry 설치됨
- CUDA driver ≥ 12.4 (12.7~12.8 권장)
- A100 80GB 또는 호환

## 3.2 설치 명령

```bash
cd /workspace/nietzche-sllm-project/ml

# 1. venv 생성
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip

# 2. Poetry 의존성 설치
poetry install

# 3. vLLM 설치 (cu128 빌드 강제)
# ⚠️ 기본 pip는 cu130을 가져올 수 있으므로 명시적으로 cu128 지정
pip install vllm==0.19.0 \
    --extra-index-url https://download.pytorch.org/whl/cu128

# 4. transformers 5.5 (Gemma 4 지원)
pip install transformers==5.5.0

# 5. flashinfer (vLLM 가속, 선택)
pip install flashinfer-python==0.6.6
```

## 3.3 검증

```bash
source /workspace/nietzche-sllm-project/ml/.venv/bin/activate

python -c "
import torch
import vllm
import transformers
print('=' * 40)
print(f'torch:        {torch.__version__}')
print(f'cuda:         {torch.cuda.is_available()}')
print(f'GPU:          {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')
print(f'vllm:         {vllm.__version__}')
print(f'transformers: {transformers.__version__}')
print('=' * 40)
"
```

**기대 출력**:
```
torch:        2.10.0
cuda:         True
GPU:          NVIDIA A100 80GB PCIe
vllm:         0.19.0
transformers: 5.5.0
```

---

# 4. finetune venv 설치

## 4.1 자동 설치 (권장)

`setup.sh`가 모든 함정을 회피하도록 작성되어 있습니다. 이걸 그냥 돌리세요:

```bash
cd /workspace/nietzche-sllm-project/ml/finetune
bash setup.sh
```

**예상 시간**: 약 10~15분

**setup.sh의 8단계**:
1. Workspace 캐시 환경변수 설정
2. Python 3.12 설치 확인
3. Poetry 설치 확인
4. 기존 깨진 .venv 정리
5. Poetry 환경 생성 + 기본 의존성
6. **PyTorch 2.6.0 + xformers (cu124)** ← 핵심 1
7. Unsloth 스택 (의존성 수동 처리, 4단계)
8. **검증** (torch + Unsloth import)

## 4.2 수동 설치 (디버깅용)

setup.sh 실패 시 단계별 수동 실행:

```bash
cd /workspace/nietzche-sllm-project/ml/finetune

# === 환경 변수 ===
export PIP_CACHE_DIR=/workspace/.cache/pip
export TMPDIR=/workspace/tmp
export HF_HOME=/workspace/.cache/huggingface

# === Poetry venv 생성 ===
poetry config virtualenvs.in-project true --local
poetry env use python3.12
poetry install || true

# === PyTorch 2.6 + xformers (cu124) ===
poetry run pip install \
    torch==2.6.0 \
    xformers==0.0.29.post3 \
    --index-url https://download.pytorch.org/whl/cu124

# === 1단계: 기본 ML 스택 (수동) ===
poetry run pip install \
    bitsandbytes \
    "triton==3.2.0" \
    huggingface_hub \
    transformers \
    datasets \
    peft \
    trl \
    accelerate \
    sentencepiece \
    protobuf \
    wandb \
    psutil \
    ninja \
    einops

# === 2단계: torchvision (unsloth_zoo가 import) ===
poetry run pip install torchvision \
    --index-url https://download.pytorch.org/whl/cu124

# === 3단계: Unsloth 본체 ===
poetry run pip install \
    "unsloth @ git+https://github.com/unslothai/unsloth.git" \
    unsloth_zoo

# === 4단계 (반드시 마지막): torchao 다운그레이드 ===
# unsloth_zoo가 torchao>=0.13을 끌어옴 → 토치 2.7 API 사용 → 충돌
# 무조건 0.12로 강제 다운그레이드
poetry run pip install "torchao==0.12.0" --force-reinstall
```

**핵심 순서**:
1. torch 먼저 (cu124)
2. 일반 패키지
3. Unsloth (torchao 0.13+ 끌어옴)
4. **마지막에** torchao 0.12 강제 (위 단계에서 깨진 거 복구)

이 순서를 어기면 무조건 깨집니다.

## 4.3 검증

```bash
source /workspace/nietzche-sllm-project/ml/finetune/.venv/bin/activate

python -c "
import torch
from unsloth import FastLanguageModel
import peft, trl, transformers
print('=' * 40)
print(f'torch:         {torch.__version__}')
print(f'cuda:          {torch.cuda.is_available()}')
print(f'GPU:           {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')
print(f'peft:          {peft.__version__}')
print(f'trl:           {trl.__version__}')
print(f'transformers:  {transformers.__version__}')
print('=' * 40)
print('Unsloth import OK')
"
```

**기대 출력**:
```
torch:         2.6.0+cu124
cuda:          True
GPU:           NVIDIA A100 80GB PCIe
peft:          0.18.1
trl:           0.24.0
transformers:  5.5.0
Unsloth import OK
```

## 4.4 wandb 로그인 (선택)

```bash
cd /workspace/nietzche-sllm-project/ml/finetune
source .venv/bin/activate
wandb login
```

학습 추적용. 없어도 학습은 동작 (`report_to="none"`로 자동 전환).

---

# 5. 환경 변수

## 5.1 필수 환경 변수

`~/.bashrc`에 추가 (또는 매번 export):

```bash
# 캐시 위치 (volume에 저장 → pod 재시작 후에도 유지)
export PIP_CACHE_DIR=/workspace/.cache/pip
export TMPDIR=/workspace/tmp
export HF_HOME=/workspace/.cache/huggingface

# Poetry PATH
export PATH="/root/.local/bin:$PATH"
```

**왜 중요한가**:
- `HF_HOME`을 `/workspace`에 두면 베이스 모델(~30GB)을 volume에 캐시 → pod 재시작 후 재다운로드 안 함
- `PIP_CACHE_DIR`도 마찬가지 → pip 재설치 시 빠름

`setup.sh`는 자동으로 `~/.bashrc`에 추가합니다 (중복 체크).

## 5.2 인증

```bash
# HuggingFace (베이스 모델 다운로드 + LoRA 업로드)
huggingface-cli login

# Wandb (학습 추적, 선택)
wandb login

# Git safe directory (pod 재시작마다)
git config --global --add safe.directory /workspace/nietzche-sllm-project
```

---

# 6. 검증

## 6.1 빠른 통합 검증

```bash
cd /workspace/nietzche-sllm-project/ml

# 1. ml venv
source .venv/bin/activate
python -c "
import torch, vllm, transformers
assert torch.__version__.startswith('2.10'), f'torch={torch.__version__}'
assert vllm.__version__ == '0.19.0', f'vllm={vllm.__version__}'
assert transformers.__version__ == '5.5.0', f'transformers={transformers.__version__}'
assert torch.cuda.is_available()
print('✓ ml venv OK')
"
deactivate

# 2. finetune venv
source finetune/.venv/bin/activate
python -c "
import torch
from unsloth import FastLanguageModel
import peft, trl
assert torch.__version__.startswith('2.6'), f'torch={torch.__version__}'
assert peft.__version__ == '0.18.1', f'peft={peft.__version__}'
assert torch.cuda.is_available()
print('✓ finetune venv OK')
"
deactivate
```

## 6.2 디스크 공간 확인

```bash
df -h /workspace
# 최소 200GB 여유 권장 (학습 + Stage B 동시 작업 기준)
```

## 6.3 GPU 확인

```bash
nvidia-smi

# 기대: A100 80GB, driver >= 12.4
```

---

# 7. 알려진 함정 카탈로그

이 섹션은 실제 시행착오의 기록입니다. 새 LLM 세션이 같은 함정에 빠지지 않도록 정리.

## 7.1 vLLM cu130 빌드 vs driver 12.7

**증상**:
```
RuntimeError: CUDA driver version is insufficient for CUDA runtime version
```

**원인**: pip가 기본으로 vLLM의 cu130 빌드를 가져옴. RunPod의 driver는 12.7이라 호환 X.

**해결**:
```bash
pip install vllm==0.19.0 \
    --extra-index-url https://download.pytorch.org/whl/cu128
```

cu128 빌드가 driver 12.7과 호환됨.

**참고**: 호환 매트릭스
- driver 12.7 → cu128 빌드 OK, cu130 빌드 X
- driver 12.8+ → cu128, cu130 모두 OK

## 7.2 transformers 5.5 + vllm 0.19 metadata mismatch

**증상**:
```
WARNING: vllm 0.19.0 has requirement transformers<5.0, but you have transformers 5.5.0
```

**원인**: vllm 0.19의 metadata가 transformers <5.0을 요구한다고 잘못 명시.

**해결**: **무시 가능**. 실제로는 transformers 5.5.0과 잘 동작. Gemma 4를 위해 5.5.0이 필수.

```bash
# 그냥 5.5.0 설치
pip install transformers==5.5.0
# 경고는 무시
```

## 7.3 peft가 Gemma4ClippableLinear 미지원

**증상**:
```
TypeError: Cannot convert Gemma4ClippableLinear to peft module
```

**원인**: peft 0.18.1까지 Gemma 4의 신규 layer를 LoRA wrap 못 함.

**해결**: **Unsloth의 `save_pretrained_merged` 사용** (이미 적용됨).

```python
# 직접 peft merge (X)
model = PeftModel.from_pretrained(...)
merged = model.merge_and_unload()  # ❌ Gemma4ClippableLinear 에러

# Unsloth (✓)
from unsloth import FastLanguageModel
model, tokenizer = FastLanguageModel.from_pretrained(checkpoint_path, ...)
model.save_pretrained_merged(output_dir, tokenizer, save_method="merged_16bit")
```

`merge_one.py`가 이 패턴을 사용합니다.

## 7.4 torchao 0.13+ 와 torch 2.6 충돌

**증상**:
```
AttributeError: module 'torch.utils._pytree' has no attribute 'register_constant'
```

**원인**: torchao 0.13+ 가 torch 2.7의 신규 API (`register_constant`) 사용. torch 2.6에는 없음.

**해결**: **torchao 0.12.0 강제 다운그레이드**.

```bash
pip install "torchao==0.12.0" --force-reinstall
```

**중요**: 이 단계는 **반드시 unsloth 설치 후 마지막에** 실행. unsloth_zoo가 torchao>=0.13을 의존성으로 끌어오기 때문.

unsloth_zoo의 dependency warning은 무시 가능 (실제로 0.12에서 동작).

## 7.5 Flash Attention 2 미작동

**증상**: 학습 시 FA2 import 실패 또는 forward에서 에러.

**원인**: Gemma 4 + Unsloth 조합에서 FA2 호환 이슈.

**해결**: **자동 fallback** to xformers. 별도 조치 불필요.

```python
# train.py 내부에서 Unsloth가 자동 처리
# xformers 0.0.29.post3 사용
```

성능 영향: A100에서 약 5~10% 느려짐. Gemma 4 학습에는 큰 문제 없음.

## 7.6 Unsloth Gemma 2/3 chat template이 system role을 user에 합침

**증상**: 학습된 모델이 system message를 무시. `<start_of_turn>user` 안에 system이 들어가 있음.

**원인**: `unsloth.chat_templates.get_chat_template`이 Gemma 2/3 template를 반환. Gemma 4의 `<|turn|>` 토큰과 다름.

**해결**: **Unsloth의 `get_chat_template` 호출 안 함**. tokenizer의 native template 사용.

```python
# train.py
model, tokenizer = FastLanguageModel.from_pretrained(...)

# ❌ 호출 X
# tokenizer = get_chat_template(tokenizer, chat_template="gemma-2")

# ✓ tokenizer가 가진 native template 그대로 사용
tokenizer.apply_chat_template(messages, tokenize=False)
```

추가로 train.py에 **chat template sanity check 4개 assertion** 추가:
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
assert _test_text.index("SYSTEM_PROBE") < _test_text.index("USER_PROBE")  # 핵심
```

## 7.7 assistant_only_loss 미지원

**증상**:
```
ValueError: assistant_only_loss is not supported for VLM models
```

**원인**: trl의 `assistant_only_loss=True` 옵션이 multi-modal base model (Gemma 4 = VLM)을 지원 안 함.

**해결**: `assistant_only_loss=False`로 설정. **전체 텍스트에 loss 적용**.

```python
# train.py
cfg = SFTConfig(
    ...
    assistant_only_loss=False,   # 어쩔 수 없음
)
```

**영향**: 이론상 학습 효율 저하. 실제로는 큰 차이 없음 (응답이 메시지의 70%를 차지).

이건 [DATA_SPEC.md §15](./DATA_SPEC.md)와 학습 한계 섹션에 명시.

## 7.8 venv 두 개 사이에서 헷갈림

**증상**: `python: command not found` 또는 잘못된 패키지 설치.

**해결**: 항상 **명시적으로 activate**.

```bash
# 명확하게:
source /workspace/nietzche-sllm-project/ml/.venv/bin/activate           # ml
source /workspace/nietzche-sllm-project/ml/finetune/.venv/bin/activate  # finetune

# 어느 venv에 있는지 확인:
which python
echo $VIRTUAL_ENV
```

**팁**: 프롬프트 prefix로 구분 가능
- `(nietzsche-data-pipeline-py3.12)` → ml venv
- `(nietzsche-finetune-py3.12)` → finetune venv

`run_stage_b.sh`처럼 자동 전환하는 스크립트를 쓰면 실수 방지.

## 7.9 Pod 재시작 후 git ownership 에러

**증상**:
```
fatal: detected dubious ownership in repository at '/workspace/nietzche-sllm-project'
```

**원인**: 새 컨테이너의 user가 기존 디렉토리 owner와 다름.

**해결**: 매 pod 시작 시 한 번 실행.
```bash
git config --global --add safe.directory /workspace/nietzche-sllm-project
```

영구화하려면 `~/.bashrc`에 추가.

## 7.10 디스크 부족 (Stage B 도중)

**증상**: `No space left on device` (merge 중)

**원인**: Stage B가 merged 모델 (62GB) + 베이스 모델 (~30GB) + LoRA 체크포인트 (4.4GB) = 96GB+ 점유.

**해결**:
1. Stage B 시작 전 공간 확보
   ```bash
   df -h /workspace   # 200GB 여유 확인
   ```
2. 필요 시 임시 정리
   ```bash
   rm -rf /workspace/.cache/pip                   # ~5GB
   rm -rf finetune/wandb/run-*                    # ~수GB
   rm -rf finetune/outputs/merged/epoch*          # 작업 중 아니면
   ```

**주의**: HuggingFace 캐시(`/workspace/.cache/huggingface`)는 지우면 베이스 모델 재다운로드 (~30GB, ~10분).

## 7.11 학습 OOM

**증상**:
```
torch.cuda.OutOfMemoryError: CUDA out of memory
```

**원인**: A100 80GB여도 Gemma 4 31B + LoRA + grad checkpointing이 ~70GB 점유.

**해결**:
```python
# train.py 수정
BATCH = 1            # 2 → 1
GRAD_ACCUM = 16      # 8 → 16 (effective batch 16 유지)
```

또는 `MAX_SEQ_LEN`을 줄임 (현재 384는 이미 최소).

## 7.12 Python 3.13 호환 X

**증상**: Poetry가 의존성 해결 실패.

**원인**: `finetune/pyproject.toml`이 `requires-python = ">=3.12,<3.13"` 으로 엄격히 3.12만 허용. Unsloth가 3.13 미지원.

**해결**: Python 3.12 사용. 3.13 설치돼 있으면:
```bash
poetry env use python3.12
```

---

# 8. 자주 쓰는 명령

## 8.1 새 pod 시작 시 (체크리스트)

```bash
# 1. Git safe directory
git config --global --add safe.directory /workspace/nietzche-sllm-project

# 2. 환경 변수 export (없으면)
export PIP_CACHE_DIR=/workspace/.cache/pip
export TMPDIR=/workspace/tmp
export HF_HOME=/workspace/.cache/huggingface
export PATH="/root/.local/bin:$PATH"

# 3. venv 체크
ls /workspace/nietzche-sllm-project/ml/.venv/bin/python
ls /workspace/nietzche-sllm-project/ml/finetune/.venv/bin/python

# 4. (필요 시) HF 로그인
huggingface-cli whoami || huggingface-cli login

# 5. 디스크 확인
df -h /workspace
```

## 8.2 venv 활성화

```bash
# ml (데이터/평가)
source /workspace/nietzche-sllm-project/ml/.venv/bin/activate

# finetune (학습/merge)
source /workspace/nietzche-sllm-project/ml/finetune/.venv/bin/activate

# 종료
deactivate
```

## 8.3 패키지 버전 확인

```bash
# 현재 venv의 핵심 패키지
pip list | grep -iE "^(torch|vllm|transformers|unsloth|peft|trl)"
```

## 8.4 venv 재생성 (망가졌을 때)

```bash
# ml venv
cd /workspace/nietzche-sllm-project/ml
deactivate 2>/dev/null
rm -rf .venv
python3.12 -m venv .venv
# (위 §3 ml venv 설치 명령 다시 실행)

# finetune venv
cd /workspace/nietzche-sllm-project/ml/finetune
deactivate 2>/dev/null
rm -rf .venv
bash setup.sh
```

## 8.5 디스크 정리

```bash
# 안전한 정리
rm -rf /workspace/nietzche-sllm-project/ml/finetune/wandb/run-*
rm -rf /workspace/.cache/pip

# 주의 (재다운로드 필요)
# rm -rf /workspace/.cache/huggingface/hub/models--google--gemma*  # 30GB

# 작업 중 아니면 안전
rm -rf /workspace/nietzche-sllm-project/ml/finetune/outputs/merged/*
```

---

## 부록: 두 venv 핵심 차이 한 페이지 요약

```
┌────────────────────────────────────────────────────────┐
│  ml venv (/workspace/.../ml/.venv)                      │
├────────────────────────────────────────────────────────┤
│  용도: 데이터 생성, 평가 추론, judge 서버              │
│  torch: 2.10.0                                          │
│  핵심: vllm 0.19, transformers 5.5, sentence-transformers│
│  설치: pyproject.toml + cu128 vllm                      │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│  finetune venv (/workspace/.../ml/finetune/.venv)       │
├────────────────────────────────────────────────────────┤
│  용도: LoRA 학습, merge, HF 업로드                     │
│  torch: 2.6.0+cu124                                     │
│  핵심: unsloth, peft 0.18, trl 0.24, torchao 0.12       │
│  설치: setup.sh (8단계 자동)                            │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│  공통 (둘 다 깔려 있음)                                 │
├────────────────────────────────────────────────────────┤
│  python 3.12, transformers 5.5.0                        │
│  CUDA driver >= 12.4 (12.7~12.8 권장)                   │
│  GPU: A100 80GB                                         │
└────────────────────────────────────────────────────────┘
```

---

## 문서 끝

**최종 갱신**: 2026-04-11
**버전**: v1.0
**다음 갱신 예정**: 새 함정 발견 시 §7에 추가
