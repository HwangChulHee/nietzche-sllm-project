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
└── 04_dev_tools.sh        ← Claude Code + Git 설정
```

## 사용법

### 전체 설치 (신규 Pod)

```bash
cd /workspace/nietzche-sllm-project
bash scripts/setup/install_all.sh
```

### 옵션별 설치

```bash
# vLLM 스킵 (GPU 없거나 나중에)
bash scripts/setup/install_all.sh --skip-vllm

# Claude Code 스킵
bash scripts/setup/install_all.sh --skip-claude

# 시스템 패키지 스킵 (apt 권한 없을 때)
bash scripts/setup/install_all.sh --skip-system

# 조합 가능
bash scripts/setup/install_all.sh --skip-vllm --skip-claude
```

### 개별 단계만 실행

```bash
bash scripts/setup/01_system_deps.sh       # 시스템 패키지만
bash scripts/setup/02_python_poetry.sh     # Python + Poetry만
SKIP_VLLM=true bash scripts/setup/03_ml_deps.sh  # vLLM 빼고 ML 의존성
bash scripts/setup/04_dev_tools.sh         # Claude Code + Git만
```

## 사전 요구사항

- Ubuntu 22.04 이상 (또는 Debian 계열)
- root 권한 (apt 설치용)
- 인터넷 연결
- GPU 있을 경우: CUDA 드라이버 설치됨 (RunPod는 기본 제공)

## 설치 후 확인

```bash
cd ml
source .venv/bin/activate

python --version              # Python 3.12.x
poetry --version              # Poetry 2.x
python -c "import fitz; print('fitz OK')"
python -c "import marker; print('marker OK')"
python -c "import vllm; print(vllm.__version__)"  # vLLM 설치했을 때만
```

## RunPod 새 Pod에서 시작하는 흐름

1. **새 Pod 생성** (RunPod 웹)
   - Template: PyTorch 또는 Ubuntu + CUDA
   - GPU: A100 80GB 추천
   - Volume: 기존 네트워크 볼륨 마운트

2. **SSH 접속**

3. **환경 설치**
   ```bash
   cd /workspace/nietzche-sllm-project
   git pull  # 최신 스크립트 받기
   bash scripts/setup/install_all.sh
   ```

4. **작업 재개**
   ```bash
   cd ml
   source .venv/bin/activate
   ```

## GPU 권장 사양

Gemma 4 26B A4B 서빙 기준:

| 정밀도 | 필요 VRAM | 추천 GPU |
|--------|-----------|----------|
| BF16 (풀) | ~60-70GB | **A100 80GB**, H100 80GB |
| INT8 | ~35-40GB | RTX 6000 Ada 48GB, A100 40GB |
| INT4 | ~20-25GB | RTX 4090 24GB (빠듯) |

**추천**: A100 80GB PCIe (BF16 여유롭게 돌아감, 파인튜닝도 가능)

## 트러블슈팅

### Poetry 설치 후 `poetry` 명령을 찾을 수 없음

```bash
export PATH="$HOME/.local/bin:$PATH"
source ~/.bashrc
```

### Python 3.12가 없음

RunPod의 `runpod/pytorch` 이미지는 보통 Python 3.10 또는 3.11. Python 3.12가 필요하면:

```bash
add-apt-repository -y ppa:deadsnakes/ppa
apt-get update
apt-get install -y python3.12 python3.12-venv python3.12-dev
```

또는 `runpod/pytorch:2.4.0-py3.12-cuda12.4.1-devel-ubuntu22.04` 같은 Python 3.12 이미지 사용.

### Marker 첫 실행이 느림

Marker는 첫 실행 시 모델을 자동 다운로드 (~2-5GB). HF_HOME 환경변수로 캐시 경로 지정 가능:

```bash
export HF_HOME=/workspace/.cache/huggingface
```

### vLLM 설치 실패

CUDA 버전 불일치가 흔한 원인. vLLM은 특정 CUDA 버전을 요구:

```bash
# CUDA 확인
nvcc --version
nvidia-smi  # Driver Version / CUDA Version

# vLLM 특정 버전 설치
pip install vllm==0.6.3
```
