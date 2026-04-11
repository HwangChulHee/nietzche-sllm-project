# 새 세션 핸드오프 프롬프트

> 이 프롬프트를 새 Claude 세션의 첫 메시지로 복붙하세요.

---

안녕. 니체 페르소나 한국어 sLLM 캡스톤 프로젝트를 이어서 작업할 거야. 이 프롬프트로 컨텍스트 공유할게.

## 프로젝트 한 줄 요약

니체 5권의 영어 원전을 한국어 SFT 데이터셋(2,413개)으로 변환하고, Gemma 4 31B에 LoRA로 학습시켜 니체 페르소나 상담 sLLM을 만드는 학부 졸업 캡스톤. **발표일 2026-04-13**.

## 작업자 (나)

- 황철희, 학부생, "철희님"으로 불러줘
- 한국어 존댓말 + 가끔 반말 섞임
- 페어 프로그래밍 스타일, 솔직한 비판 환영
- 데이터 품질에 엄격하고, 메타 인사이트 좋아함
- 자세한 설명 선호 ("아주 자세하게")
- 큰 작업 전엔 옵션 제시받고 선택하는 거 선호

## 현재 상태 (2026-04-11 기준)

### ✅ 완료
- Stage A 데이터 파이프라인 (train 2,413 + eval 138)
- LoRA 학습 5 epochs (1h 9m, A100 80GB)
- HF Hub 업로드 (`banzack/nietzsche-gemma4-31b-lora`, private, 5 branches)
- Stage B 평가 응답 생성 (6 모델 × 138 = 828 응답, 94분)
- **문서 7개 작성 완료** (`ml/docs/` 안에 전부)
- **문서 정정 작업 완료 (Phase 1~5)** — 코드 직접 검토로 부정확한 부분 34개 정정. DATA_SPEC v10.0.2.

### 🟡 다음에 할 것
1. **Stage C** (LLM judge 채점) — 스크립트 작성부터
2. **발표 자료 PPT** 작성

### 핵심 발견 (이 프로젝트의 메타 인사이트 5가지)

1. **학습이 응답을 60% 간결화**: baseline 697자 → epoch 1~3 ~280자
2. **epoch 4부터 token collapse**: 단일 토큰 무한 반복, max 21,128자 폭주
3. **eval_loss는 거짓말한다**: eval_loss +0.084가 실제론 응답 길이 +103%, 정성적 붕괴 의미
4. **데이터 자기검증 발견**: polemical_sharp voice 7%(63/872)가 어미 일관성 결함
5. **자가 검증 비대칭 발견 (Phase 1)**: 데이터 생성 시점(reconstruction.txt)과 평가 시점(stage_a_score.py VOICE_DESCRIPTIONS)의 voice 정의가 달랐음. 후자만 어미를 명시하고 전자는 안 함. 이게 4번 결함의 정확한 원인. v11에서 voice 정의를 single source of truth로 추출 예정.

## 작업 환경

- **RunPod A100 80GB** (유럽 리전, /workspace 500GB volume)
- **상황별 GPU/CPU 전환**: 문서 작업은 CPU, 학습/추론은 GPU
- **Repo**: `https://github.com/HwangChulHee/nietzche-sllm-project`
- **프로젝트 루트**: `/workspace/nietzche-sllm-project/`
- **ML 디렉토리**: `/workspace/nietzche-sllm-project/ml/`

## 가장 먼저 할 일

이 프로젝트의 모든 컨텍스트는 `ml/docs/` 안에 7개 문서로 정리되어 있어. **반드시 다음 두 파일을 먼저 읽어**:

```bash
# 1. 새 세션 진입점 (필수, 가장 먼저)
cat /workspace/nietzche-sllm-project/ml/docs/LLM_ONBOARDING.md

# 2. 전체 구조 (필수, 두 번째)
cat /workspace/nietzche-sllm-project/ml/docs/ARCHITECTURE.md
```

이 두 파일이면 5분 안에 프로젝트 전체 컨텍스트 잡혀. 그리고 상황에 따라 나머지 문서 참고:

| 문서 | 답하는 질문 |
|---|---|
| `DATA_SPEC.md` | 데이터셋 어떻게 생겼나? **(v10.0.2, 코드와 1:1 정합)** |
| `PIPELINE.md` | 어떻게 돌리나? 명령어는? |
| `SFT_STRATEGY.md` | 왜 이렇게 학습? Stage B 결과 분석 |
| `ENVIRONMENTS.md` | venv 두 개 + 12개 함정 카탈로그 |
| `RESULTS.md` | 결과 파일 어디 + 검증 명령 + 발표 매핑 |

> ⚠️ **중요**: 데이터 파이프라인의 실제 순서는 **청킹 → 한국어 재구성 → 5축 LLM 채점 → SFT 생성**입니다. 재구성이 필터보다 먼저예요. 자세한 사항은 DATA_SPEC.md §9.

## 환경 빠른 설정

```bash
# 1. Git safe directory (pod 재시작마다 필요)
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
```

## venv 두 개 (중요)

이 프로젝트는 venv가 두 개야. 작업에 따라 다른 걸 써야 함:

| 작업 | venv | 핵심 패키지 |
|---|---|---|
| 데이터 / 평가 추론 / judge 서버 | `ml/.venv/` | vllm 0.19 + torch 2.10 + transformers 5.5 |
| LoRA 학습 / merge | `ml/finetune/.venv/` | unsloth + torch 2.6 + peft 0.18 |

```bash
# 활성화
source /workspace/nietzche-sllm-project/ml/.venv/bin/activate           # 데이터/평가
source /workspace/nietzche-sllm-project/ml/finetune/.venv/bin/activate  # 학습
```

**병합 시도 금지** — torch 버전 충돌로 깨짐. 이미 시도했음.

## 절대 하지 말 것 ⚠️

발표 임박이라 위험한 작업은 **반드시 확인 후** 진행:

1. **데이터 재생성 금지** — `python v2_pipeline/stage_a_*.py` 실행 시 LoRA 학습이 의존하는 train.jsonl 덮어씀
2. **LoRA 체크포인트 삭제 금지** — `finetune/outputs/nietzsche-lora-31b/` 4.4GB
3. **Stage B 결과 삭제 금지** — `finetune/outputs/stage_b/responses.jsonl` 828개
4. **peft로 Gemma 4 직접 merge 시도 금지** — Gemma4ClippableLinear 에러, Unsloth만 사용
5. **Unsloth chat template 사용 금지** — system role이 user에 합쳐짐, native template만

자세한 사항은 `LLM_ONBOARDING.md §5 절대 하지 말 것` 참고.

## 다음 우선순위 (선택)

발표일 4/13까지 며칠 남음. 아래 옵션 중에 어떤 거 진행할지 물어봐줘:

### 옵션 A: Stage C 진행 (정량 평가)
- 작성할 스크립트:
  - `finetune/scripts/run_judge_server.sh` (Gemma 4 26B-A4B vLLM 서버)
  - `finetune/scripts/stage_c_score.py` (`stage_a_score.py` 복사 + 입력/필드 수정 + model_tag 보존)
  - `finetune/scripts/stage_c_report.py` (6 모델 × Q1~Q3 × breakdown)
- Stage B 응답 828개를 Q1/Q2/Q3 채점
- 발표 자료의 정량 데이터 강화
- 예상 시간: 3~4시간

### 옵션 B: 발표 자료 (PPT) 작성
- `RESULTS.md` 부록에 5 슬라이드 outline 이미 있음
- Stage C 없이도 발표 가능 (정성 분석으로도 충분히 강함)
- 예상 시간: 1~2일

### 옵션 C: 둘 다 (Stage C → PPT)
- Stage C 먼저 (오늘), PPT 내일/모레
- 가장 안전한 선택

## 핵심 숫자 (외워두면 좋음)

| 항목 | 값 |
|---|---|
| 베이스 모델 | Gemma 4 31B |
| 학습 데이터 | 2,413 train + 138 eval |
| LoRA | r=16, alpha=32, 5 epochs |
| Best epoch (잠정) | **2** (eval_loss 0.9358) |
| 학습 시간 | 1h 9m 54s |
| Stage B 응답 | 828 |
| 평균 응답 길이 | baseline 697 → epoch2 277 → epoch4 555(붕괴) → epoch5 811 |
| Eval loss 곡선 | 0.95 → **0.94** → 0.96 → 1.04 → 1.11 |
| Stage 0 청크 | 973 (5권) |
| Stage 0.5 통과율 | 928/973 (95.4%) |
| Stage A 통과율 | 2,780 → 2,551 (91.8%) |

## 빠른 진행도 확인

```bash
cd /workspace/nietzche-sllm-project/ml

# 데이터 무결성
wc -l v2_data/sft_dataset/train.jsonl   # 2413
wc -l v2_data/sft_dataset/eval.jsonl    # 138

# Stage B 진행도
wc -l finetune/outputs/stage_b/responses.jsonl   # 828

# 체크포인트 5개
ls finetune/outputs/nietzsche-lora-31b/checkpoint-*/adapter_model.safetensors | wc -l   # 5

# git 상태
cd /workspace/nietzche-sllm-project
git log --oneline -10
```

## 마지막 세션에서 한 작업 (요약)

이전 세션에서 **8~10시간 동안 문서화 + 정정 작업**을 했어:

### 1차: 문서화 (6시간)
1. 디렉토리 정리 (smoke test 잔재 ~970MB 삭제, .ipynb_checkpoints 정리)
2. 데이터 자기검증 (polemical_sharp voice 7% 어미 결함 발견)
3. 7개 핵심 문서 작성 (LLM_ONBOARDING + ARCHITECTURE + PIPELINE + DATA_SPEC + ENVIRONMENTS + SFT_STRATEGY + RESULTS)
4. 모든 작업 git 커밋 + 푸시

### 2차: 정정 작업 (Phase 1~5, 3~4시간)
1. **Phase 1**: DATA_SPEC.md v10.0.1 → v10.0.2. 코드 직접 검토로 34개 항목 정정
   - Stage 0.7과 0.5 순서가 뒤바뀌어 있었음
   - 5축 평가 정의 추가
   - 책별 통과 조건 추가 (TI 챕터별 11가지 포함)
   - Stage A 4단계 모두 정확하게 정정 (15-char ngram, 3축 stratification, 점수 기반 train/eval 등)
2. **Phase 2**: ARCHITECTURE.md + PIPELINE.md 정정
3. **Phase 3**: RESULTS.md에 §2.0 Stage 0~0.9 통과율 추가
4. **Phase 4**: SFT_STRATEGY.md에 자가 검증 비대칭 인사이트 추가
5. **Phase 5**: HANDOFF + LLM_ONBOARDING 갱신

학습이나 데이터 작업은 안 했어. **현재 상태는 학습 + Stage B 끝난 시점 그대로**, 다음은 Stage C 또는 발표 자료 작성.

---

## 첫 메시지 응답으로 해줘

이 프롬프트 다 읽었으면 다음 두 가지 해줘:

1. **`LLM_ONBOARDING.md`와 `ARCHITECTURE.md` 읽기** (필수)
2. **읽은 후, 다음 작업 옵션(A/B/C) 중 어떤 거 진행할지 나에게 물어봐**

질문 받으면 그때 결정할게.