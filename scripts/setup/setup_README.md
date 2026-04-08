# 환경 설치 스크립트

RunPod 등 새 컨테이너 환경에서 프로젝트 셋업을 자동화하는 스크립트 모음.

## 파일 구조

```
scripts/setup/
├── README.md              ← 이 파일
├── install_all.sh         ← 전체 설치 orchestrator
├── 01_system_deps.sh      ← apt 패키지 (tesseract, ghostscript 등)
├── 02_python_poetry.sh    ← Python 3.12 + Poetry + 가상환경
├── 03_ml_deps.sh          ← Marker + vLLM + HuggingFace CLI
├── 04_dev_tools.sh        ← Claude Code + Git 설정
├── 05_warm_cache.sh       ← HF 모델 사전 다운로드 (e5, marker) ~3GB
├── 06_shell_init.sh       ← .bashrc 자동 설정 (auto-cd, venv, alias, env)
├── 07_sanity_check.sh     ← 30초 환경/데이터 무결성 확인
└── 08_warm_llm.sh         ← Gemma 4 LLM 모델 사전 다운로드 (~115GB)
```

## 사용법

### 신규 Pod 첫 셋업 (한 번만, ~30분)

```bash
cd /workspace/nietzche-sllm-project

# 1. 시스템 + Python + ML 의존성
bash scripts/setup/install_all.sh

# 2. 임베딩/OCR 모델 사전 다운로드 (~3GB, 1-2분)
bash scripts/setup/05_warm_cache.sh

# 3. 셸 자동화 설정 (bashrc)
bash scripts/setup/06_shell_init.sh
source ~/.bashrc

# 4. HF 로그인 (Gemma 4 다운로드용)
huggingface-cli login   # 또는 hf auth login
# 토큰 발급: https://huggingface.co/settings/tokens

# 5. LLM 모델 사전 다운로드 (~115GB, 5-15분)
bash scripts/setup/08_warm_llm.sh

# 6. 전체 검증
bash scripts/setup/07_sanity_check.sh
```

### Pod 재시작 후 (자주, ~30초)

`06_shell_init.sh`를 한 번 돌려놨다면 **새 셸 열면 자동으로**:
- `cd /workspace/nietzche-sllm-project/ml`
- `source .venv/bin/activate`
- `HF_HOME` / `VLLM_CACHE_ROOT` 환경변수 설정
- 유용한 alias 활성화

검증만 하면 됨:
```bash
bash scripts/setup/07_sanity_check.sh
```

`✅` 모두 나오면 바로 작업 시작.

### 옵션별 설치

```bash
# vLLM 스킵 (GPU 없거나 나중에)
bash scripts/setup/install_all.sh --skip-vllm

# Claude Code 스킵
bash scripts/setup/install_all.sh --skip-claude

# 시스템 패키지 스킵 (apt 권한 없을 때)
bash scripts/setup/install_all.sh --skip-system

# 임베딩 캐시 워밍 부분 스킵
SKIP_E5=true bash scripts/setup/05_warm_cache.sh
SKIP_MARKER=true bash scripts/setup/05_warm_cache.sh

# LLM 다운로드 옵션
DOWNLOAD_AWQ=true bash scripts/setup/08_warm_llm.sh   # 4-bit AWQ도 추가 (4090용)
SKIP_DISK_CHECK=true bash scripts/setup/08_warm_llm.sh # 디스크 체크 우회
```

## 사전 요구사항

- Ubuntu 22.04 이상 (또는 Debian 계열)
- root 권한 (apt 설치용)
- 인터넷 연결
- GPU 있을 경우: CUDA 드라이버 설치됨 (RunPod는 기본 제공)
- **네트워크 볼륨이 `/workspace`에 마운트되어 있어야 캐시 영구화 의미 있음**
- LLM 사전 다운로드 시: `/workspace`에 130GB+ 여유 공간

## 영구화되는 캐시 (모두 `/workspace`에)

| 캐시 | 경로 | 크기 | 내용 |
|---|---|---|---|
| HuggingFace | `/workspace/.cache/huggingface` | ~120GB | e5-large, Marker, Gemma 4 weights |
| vLLM | `/workspace/.cache/vllm` | ~수백MB | CUDA graph, kernel JIT 컴파일 |
| HF token | `/workspace/.cache/huggingface/token` | — | 로그인 자격증명 |

`06_shell_init.sh`가 환경변수(`HF_HOME`, `VLLM_CACHE_ROOT` 등)를 박아둬서 새 셸 열 때마다 자동으로 위 경로 사용.

## RunPod 새 Pod에서 시작하는 흐름

### 첫 셋업 (~30분, 대부분 다운로드 시간)

1. **새 Pod 생성** (RunPod 웹)
   - Template: PyTorch 또는 Ubuntu + CUDA
   - GPU: A100 80GB 추천 (Gemma 4 BF16 풀 정밀도)
   - **Volume**: 기존 네트워크 볼륨 마운트 (필수, 200GB+ 권장)
   - Image: `runpod/pytorch:2.4.0-py3.12-cuda12.4.1-devel-ubuntu22.04` 권장

2. **SSH 접속 후 위의 "신규 Pod 첫 셋업" 6단계 실행**

### 이후 재시작 (~30초)

1. SSH 접속 → 셸 열리면 자동으로 venv + cd 완료
2. `bash scripts/setup/07_sanity_check.sh` 로 검증
3. 작업 계속

## 자동화된 alias (06_shell_init.sh 적용 후)

```bash
# Daily use
ll          # ls -lah
gst         # git status
gd          # git diff
gl          # git log --oneline -20
py          # python
runs        # data/chunks, data/extracted 빠르게 보기

# Pipeline 단축어 (인자 다 박혀있음)
stage1      # PDF/Marker → ExtractedPage
stage2      # 섹션 분류
stage3      # 청크 분할
stage4      # 영어 anchor 매핑

# vLLM serve (Stage 5)
vllm-26b    # gemma-4-26B-A4B-it 서빙 (MoE, 빠름)
vllm-31b    # gemma-4-31B-it 서빙 (Dense, 품질 위)
```

## 설치 후 확인

`07_sanity_check.sh`가 자동으로 다 확인해주지만, 수동 확인하려면:

```bash
cd ml
source .venv/bin/activate

python --version              # Python 3.12.x
poetry --version              # Poetry 2.x
python -c "import fitz; print('fitz OK')"
python -c "import marker; print('marker OK')"
python -c "import vllm; print(vllm.__version__)"
nvidia-smi                    # GPU 인식 확인
echo $HF_HOME                 # /workspace/.cache/huggingface
echo $VLLM_CACHE_ROOT         # /workspace/.cache/vllm
ls $HF_HOME/hub | grep gemma  # 캐시된 Gemma 모델 확인
```

## GPU 권장 사양 (Gemma 4 서빙)

| 모델 | 정밀도 | 필요 VRAM | 추천 GPU |
|---|---|---|---|
| **gemma-4-26B-A4B-it** (MoE) | BF16 | ~70GB | A100 80GB, H100 80GB |
| **gemma-4-26B-A4B-it** (MoE) | 4-bit AWQ | ~18GB | RTX 4090 24GB |
| **gemma-4-31B-it** (Dense) | BF16 | ~80GB | A100 80GB, H100 80GB |
| **gemma-4-31B-it** (Dense) | 4-bit | ~20GB | RTX 4090 24GB (빠듯) |

**추천**: A100 80GB PCIe (BF16 풀 정밀도, 두 모델 다 여유롭게 돌아감)

26B MoE는 4B만 active라 31B Dense보다 **추론 빠름**. 품질은 Arena 1441 vs 1452로 비슷.

## 트러블슈팅

### Poetry 설치 후 `poetry` 명령을 찾을 수 없음

```bash
export PATH="$HOME/.local/bin:$PATH"
source ~/.bashrc
```

`06_shell_init.sh`를 돌렸다면 자동 처리됨.

### Python 3.12가 없음

RunPod의 `runpod/pytorch` 이미지는 보통 Python 3.10 또는 3.11. Python 3.12가 필요하면:

```bash
add-apt-repository -y ppa:deadsnakes/ppa
apt-get update
apt-get install -y python3.12 python3.12-venv python3.12-dev
```

또는 `runpod/pytorch:2.4.0-py3.12-cuda12.4.1-devel-ubuntu22.04` 같은 Python 3.12 이미지 사용.

### Marker 첫 실행이 느림

Marker는 첫 실행 시 모델을 자동 다운로드 (~2-5GB). `05_warm_cache.sh`로 미리 받아두면 해결.

캐시 경로 확인:
```bash
echo $HF_HOME
ls -lah $HF_HOME/hub
```

### Pod 재시작했는데 모델이 다시 다운로드됨

`HF_HOME`이 `/root/.cache`(휘발) 같은 곳을 가리키고 있을 가능성. `06_shell_init.sh`를 돌려서 `/workspace/.cache/huggingface`로 영구 설정.

확인:
```bash
echo $HF_HOME
# /workspace/.cache/huggingface 가 나와야 함
```

### Gemma 4 다운로드 실패 (403 / 401)

Gemma 4는 Apache 2.0이라 라이선스 동의는 불필요하지만, HF 토큰은 필요할 수 있음:

```bash
huggingface-cli login
# 또는 hf auth login
# 토큰: https://huggingface.co/settings/tokens
```

만약 그래도 403이면 모델 페이지 직접 방문해서 gating 여부 확인:
- https://huggingface.co/google/gemma-4-26B-A4B-it
- https://huggingface.co/google/gemma-4-31B-it

### 08_warm_llm.sh가 디스크 부족으로 실패

```bash
df -h /workspace
# 130GB 이상 여유 필요
```

옵션:
- `/workspace`에 다른 큰 파일 정리
- 둘 중 하나만 받기 (스크립트의 `MODELS_BF16` 배열 편집)
- `SKIP_DISK_CHECK=true bash scripts/setup/08_warm_llm.sh` (위험)

### vLLM 설치 실패

CUDA 버전 불일치가 흔한 원인. vLLM은 특정 CUDA 버전을 요구:

```bash
# CUDA 확인
nvcc --version
nvidia-smi  # Driver Version / CUDA Version

# Gemma 4 호환 vLLM (transformers >= 5.5.0 자동 포함)
pip install -U vllm
```

### vLLM이 Gemma 4 인식 못함 (`Unsupported model`)

`transformers` 버전이 너무 낮음. Gemma 4는 transformers >= 5.5.0 필요:

```bash
python -c "import transformers; print(transformers.__version__)"
# 5.5.0 이상이어야 함

pip install -U 'transformers>=5.5.0'
```

`08_warm_llm.sh`는 자동으로 체크/업데이트하지만, 수동 설치 시에는 직접 확인 필요.

### Sanity check에서 데이터 파일 missing

볼륨이 제대로 마운트 안 됐을 가능성:
```bash
ls -la /workspace/nietzche-sllm-project/ml/data
```

비어있다면 RunPod 콘솔에서 볼륨 마운트 확인.

### 첫 vllm serve가 느림

CUDA graph 컴파일 (1~2분). `VLLM_CACHE_ROOT`가 `/workspace/.cache/vllm`로 설정돼 있으면 한 번 컴파일된 결과가 저장돼 다음 실행부터는 빠름.

확인:
```bash
echo $VLLM_CACHE_ROOT
ls $VLLM_CACHE_ROOT 2>/dev/null
```
