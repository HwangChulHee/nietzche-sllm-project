# AGENTS.md — LLM 세션 진입점 + 행동 규약

> **이 파일을 가장 먼저 읽으세요.** 새 LLM 세션이 이 프로젝트에서 작업하기 위한
> **단일 진입점**입니다. 30초 안에 컨텍스트를 잡고, 행동 규약을 이해하고,
> 필요한 추가 컨텍스트만 lazy load 하도록 설계되었습니다.
>
> **이 문서만 읽고 시작하세요.** 다른 문서는 §5 라우팅 표에 따라 필요할 때만.

---

## 0. 사용법

새 세션의 첫 행동:
1. 이 문서를 처음부터 끝까지 읽기 (~3분)
2. §3 행동 규약을 내재화하기 (CRITICAL)
3. 사용자의 첫 질문이 오면 §5 라우팅 표를 보고 추가 문서를 lazy load
4. 절대 §3.2의 write 작업을 사용자 확인 없이 시행하지 말 것

---

## 1. 30초 컨텍스트

**프로젝트**: 니체 페르소나 한국어 sLLM 캡스톤 (학부 졸업 프로젝트)

**무엇**: 니체 5권의 영어 원전을 한국어 SFT 데이터셋(2,413개)으로 변환하고,
Gemma 4 31B에 LoRA로 학습시켜 니체 페르소나 상담 sLLM을 만듦.

**핵심 숫자**:
| 항목 | 값 |
|---|---|
| 베이스 모델 | Gemma 4 31B |
| 학습 데이터 | 2,413 train + 138 eval |
| LoRA | r=16, 5 epochs |
| **Best epoch** | **1** (Stage C 평균 0.819) |
| Stage B 응답 | 828 (6 모델 × 138) |
| Stage C 채점 | 828 × 2 (점수만 + CoT) |

**Repo**: https://github.com/HwangChulHee/nietzche-sllm-project
**프로젝트 루트**: `/workspace/nietzche-sllm-project/`
**ML 디렉토리**: `/workspace/nietzche-sllm-project/ml/`

---

## 2. 현재 상태

**최종 갱신**: 2026-04-11 (Stage C 완료 시점)
**발표일**: 2026-04-13 (월)

### ✅ 완료
- Stage A 데이터 파이프라인 (train 2,413 + eval 138)
- LoRA 학습 5 epochs (1h 9m, A100 80GB)
- HF Hub 업로드 (`banzack/nietzsche-gemma4-31b-lora`, private, 5 branches)
- Stage B 평가 응답 생성 (828 응답)
- 7개 핵심 문서 작성 + 정정 작업 (Phase 1~5)
- **Stage C 채점 (점수만 + CoT, best=epoch1)**
- 모든 결과 git 커밋 + push

### 🟡 다음 우선순위
1. **발표 자료 (PPT)** ← 현재 우선순위
2. (선택) Stage C CoT reason 정량 분석 — voice별 어미 결함 비율 집계
3. (발표 후) v11 데이터셋 작업 — voice 정의 single source of truth

### 핵심 발견 (메타 인사이트 5가지)

1. **학습이 응답을 60% 간결화시킴** — baseline 697자 → epoch 1~3 ~280자
2. **epoch 4부터 token collapse** — 27/138(19.6%) → epoch 5는 92/138(66.7%) 붕괴, 단일 토큰 무한 반복 21,128자 폭주
3. **eval_loss는 거짓말한다 (Stage C로 확정)** — eval_loss 최저는 epoch 2(0.9358)였으나 Stage C 평균은 epoch 1이 1위(0.819 vs epoch 2의 0.800)
4. **데이터 검증 발견**: polemical_sharp voice 7%가 어미 일관성 결함 (DATA_SPEC §15.7)
5. **자가 검증 비대칭 (Phase 1 → Stage C CoT로 정량 확장)**: Stage C CoT 모드에서 모든 voice의 Q3 평균이 일괄 -0.3~-0.5점 하락 — 데이터셋 어미 결함이 voice 전반의 구조적 문제로 확인됨

---

## 3. 행동 규약 (CRITICAL)

### 3.1 작업 분류 — read-only는 자유, write는 논의

**자유롭게 시행**:
- 파일 읽기: `cat`, `head`, `tail`, `less`, `view`, `wc -l`
- 검색: `grep`, `find`, `git log`, `git diff`, `git status`
- 분석: jq, python으로 데이터 통계 산출
- 임시 진단 명령: 결과를 화면에만 출력

**반드시 사용자와 논의 후 시행**:
- **새 파일 생성** (스크립트, 문서, 데이터)
- **기존 파일 수정** (코드, 문서, 데이터, 설정)
- **파일/디렉토리 삭제** (`rm`, `git rm`)
- **git 작업** (`git add`, `commit`, `push`, `reset`, `rebase`)
- **데이터 생성/재생성** (모든 v2_pipeline 스크립트 실행)
- **모델 학습/추론** (LoRA 학습, vLLM 서빙)
- **설치/제거** (`pip install`, `apt`, `poetry add`)
- **환경 변수 변경**

**판단 기준**: "이 작업이 파일 시스템·git·외부 시스템에 영구적 변경을 만드나?" → Yes면 논의 필수.

### 3.2 write 작업 전 — 논의 프로토콜

write 작업이 필요한 상황에서 LLM이 따라야 할 순서:

1. **상황 파악** — 필요시 read-only 명령으로 먼저 살피기
2. **옵션 제시** — 2~3개 옵션을 **간결하게** 제시 (각 옵션 2~4줄, 풀코드 금지)
3. **추천 + 근거** — 어느 옵션을 추천하는지, 왜 그런지 한 단락
4. **사용자 확인 대기** — "이 방향으로 갈까요?" 또는 "어떤 옵션이 좋으세요?"
5. **승인 후 실행** — 그제서야 코드 작성·명령 실행

**금지 사항**:
- ❌ 옵션 제시 단계에서 풀코드 작성 (토큰 낭비, 사용자가 못 본 코드를 만들면 신뢰 저하)
- ❌ "일단 만들어볼게요" 후 사용자 확인 없이 진행
- ❌ 복잡한 작업을 한 번에 여러 단계 진행 (단계마다 확인)

### 3.3 코드 작성 시 원칙

설계 결정이 끝난 후 실제 코드를 작성할 때:

- **기존 코드 패턴 존중** — 새 코드는 기존 스크립트의 구조·스타일과 일치
- **재현성 우선** — 결정적이지 않은 작업(LLM 호출 등)은 resume 가능하도록 설계
- **친절한 에러** — 입력 파일 없으면 명확한 메시지로 종료, 추측하지 말 것
- **출력 분리** — 기존 결과를 절대 덮어쓰지 말 것, 새 모드는 새 파일로
- **로그 보존** — 진행도 출력은 stderr 또는 별도 로그 파일에

### 3.4 절대 하지 말 것 ⚠️

발표 임박이라 위험한 작업은 **절대 금지**:

1. **데이터 재생성 금지** — `python v2_pipeline/stage_a_*.py` 실행 시 LoRA 학습이 의존하는 train.jsonl 덮어씀
2. **LoRA 체크포인트 삭제 금지** — `finetune/outputs/nietzsche-lora-31b/` 4.4GB
3. **Stage B 결과 삭제 금지** — `finetune/outputs/stage_b/responses.jsonl` 828개
4. **Stage C 결과 삭제 금지** — `finetune/outputs/stage_c/scored*.jsonl`
5. **venv 병합 금지** — vLLM 0.19(torch 2.10) + Unsloth(torch 2.6) 충돌, 이미 시도해서 깨짐
6. **peft로 Gemma 4 직접 merge 시도 금지** — `Gemma4ClippableLinear` 에러, Unsloth만 사용
7. **Unsloth chat template 사용 금지** — system role이 user에 합쳐짐, native template만

자세한 함정 카탈로그는 `ml/docs/ENVIRONMENTS.md` §7.

### 3.5 응답 스타일 — 토큰 절약

LLM은 친절하려는 본능 때문에 과잉 응답하기 쉬움. 이 프로젝트에선 **다음 규칙 엄격 준수**:

- **간결 우선** — 초반 제안·답변은 핵심만. 사용자가 "자세히"라고 하면 그때 깊이 들어가기.
- **다음 단계 미리보기 금지** — 사용자가 묻기 전에 "다음엔 이걸 할 거예요"를 먼저 펼치지 말 것. 단계는 한 번에 하나만.
- **결정사항은 한 줄 옵션으로** — "OK / NO / A안 / B안" 같이 사용자가 빠르게 답할 수 있도록. 옵션마다 긴 trade-off 분석 금지.
- **사용자가 요청하기 전엔 분석·집계 자동 실행 금지** — "이런 분석도 가능해요"는 한 줄로만 언급, 실행은 사용자 요청 시.
- **자랑·감탄 금지** — "완벽해요!", "강력합니다!" 같은 표현은 결과가 객관적으로 두드러질 때만.
- **이미 한 말 반복 금지** — 결정 끝난 사항을 다음 응답에서 다시 정리·요약하지 말 것.

이 규칙들은 사용자가 "토큰 아깝다"고 명시했기 때문이며, 위반은 곧 신뢰도 손상.

### 3.6 커뮤니케이션 원칙

- **솔직하게** — 데이터/모델 결함 발견하면 숨기지 말고 알리기. 사용자는 메타 인사이트를 좋아함.
- **확인 후 진행** — 큰 변경 전엔 항상 사용자 OK 받기.
- **실행 가능한 명령** — 추상적 설명보다 복붙 가능한 명령 선호.
- **사용자가 이끌게 두기** — LLM이 작업 흐름을 주도하지 말 것. 사용자가 다음 작업을 결정하고 LLM은 따라가는 구조.

---

## 4. 작업자 정보

- **이름**: 황철희, 학부생
- **호칭**: "철희님"
- **언어**: 한국어 (존댓말 기본, 가끔 반말 섞음)
- **스타일**: 페어 프로그래밍 파트너. 솔직한 비판 환영. 데이터 품질에 엄격.
- **선호**:
  - 자세한 설명은 명시적으로 요청할 때만
  - 옵션 선택 후 진행
  - 메타 인사이트 의식적 추구
  - 실무 표준이 무엇인지 항상 궁금해함
  - **토큰 효율 매우 중시** — 불필요한 미리보기·반복 요약·과잉 친절 싫어함

---

## 5. 컨텍스트 lazy loading

### 5.1 질문 → 문서 라우팅

| 사용자 질문 유형 | 먼저 읽을 문서 | 읽기 깊이 |
|---|---|---|
| "이 프로젝트가 뭐 하는 거야?" | 이 문서 §1, §2 | 이미 읽음 |
| "데이터셋 구조는?" | `ml/docs/DATA_SPEC.md` §1~§3 | 부분 |
| "학습 결과는?" | `ml/docs/RESULTS.md` §3~§5 | 전체 |
| "Stage C 결과가 뭐야?" | `ml/docs/RESULTS.md` §5 | 전체 |
| "best epoch 뭐야? 왜?" | `ml/docs/RESULTS.md` §5.5 + `SFT_STRATEGY.md` §6 | 부분 |
| "Stage A는 어떻게 돌아가?" | `ml/docs/DATA_SPEC.md` §9~§10 | 전체 |
| "코드/파일 어디 있어?" | `ml/docs/ARCHITECTURE.md` §3, §5 | 부분 |
| "어떻게 실행해?" | `ml/docs/PIPELINE.md` 해당 단계 | 부분 |
| "환경 에러 났어" | `ml/docs/ENVIRONMENTS.md` §7 | 부분 |
| "발표 자료 어떻게 만들어?" | `ml/docs/RESULTS.md` 부록 + 5번 슬라이드 outline | 전체 |
| "데이터셋 한계는?" | `ml/docs/DATA_SPEC.md` §15 | 부분 |
| "메타 인사이트 자세히" | `ml/docs/SFT_STRATEGY.md` §5 + 이 문서 §2 | 전체 |
| "자주 쓰는 명령은?" | `ml/docs/LLM_ONBOARDING.md` §4 | 부분 |
| "Stage C 코드 어떻게 짜여 있어?" | `cat ml/finetune/scripts/stage_c_score.py` | 전체 |

### 5.2 "모르면 먼저 살피고 결정"

문서를 통째로 읽기 전에, **read-only 명령으로 최소 컨텍스트만 먼저 잡는 게 효율적**:

```bash
# 프로젝트 디렉토리 구조 한눈에
find ml/ -maxdepth 2 -type d -not -path '*/.*' -not -path '*/.venv*' | sort

# 최근 git 작업
git log --oneline -10

# 데이터 무결성 빠른 체크
wc -l ml/v2_data/sft_dataset/{train,eval}.jsonl
wc -l ml/finetune/outputs/stage_b/responses.jsonl
wc -l ml/finetune/outputs/stage_c/scored.jsonl

# 특정 파일의 한 샘플만 보고 스키마 파악
head -1 ml/v2_data/sft_dataset/eval.jsonl | python -m json.tool

# 특정 키워드가 어느 문서에 있나
grep -l "best epoch" ml/docs/*.md
```

원칙: **확실하지 않은 정보는 추측하지 말고 grep·cat으로 확인**. 5초로 정확한 답을 얻을 수 있는데 추측해서 틀리면 더 큰 손실.

### 5.3 더 깊은 컨텍스트가 필요할 때

`ml/docs/LLM_ONBOARDING.md`로 가기. 거기에는:
- 프로젝트 진행 단계별 자세한 설명
- 자주 쓰는 명령 카탈로그 (상태 확인, 응답 비교, 통계)
- FAQ
- 부록 (복구 방법, 디스크 정리)

이 문서(AGENTS.md)는 진입점, ONBOARDING은 깊은 참조.

---

## 6. 환경 빠른 진입

### 6.1 pod 재시작 후 (체크리스트)

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
nvidia-smi 2>/dev/null || echo "CPU 모드"
```

### 6.2 venv 두 개 (CRITICAL)

**venv 두 개를 절대 합치려 하지 말 것** (§3.4 참고).

| 작업 | venv | 활성화 |
|---|---|---|
| 데이터 / 평가 / judge 서버 | `ml/.venv/` | `source ml/.venv/bin/activate` |
| LoRA 학습 / merge | `ml/finetune/.venv/` | `source ml/finetune/.venv/bin/activate` |

### 6.3 GPU 사용 노트

이 프로젝트는 GPU 환경이 자주 바뀜:
- **A100 80GB** — 학습·추론 최적
- **RTX PRO 6000 (Blackwell sm_120)** — 호환성 이슈 있을 수 있음. 현재 vLLM 0.19로 Gemma 4 26B-A4B는 작동 확인됨 (TRITON_ATTN backend로 자동 fallback)
- **CPU 모드** — 문서 작업 전용

GPU 작업 시작 전 `nvidia-smi`로 모드 확인.

---

## 부록 A: 핵심 숫자 (외워두면 좋음)

| 항목 | 값 |
|---|---|
| 베이스 모델 | Gemma 4 31B |
| Judge 모델 | Gemma 4 26B-A4B (Stage A·C 동일) |
| 학습 데이터 | 2,413 train + 138 eval |
| 원전 책 | 5권 (JW, BGE, GM, TI, EH) |
| LoRA rank | 16 (alpha 32) |
| Epochs | 5 (모두 보존) |
| **Best epoch** | **1** (Stage C mean 0.819) |
| 학습 시간 | 1h 9m 54s |
| Stage B 응답 | 828 (6 모델 × 138) |
| Stage B 시간 | 94분 |
| Stage C 응답 | 828 × 2 (점수만 + CoT) |
| Stage C 시간 | 점수만 6분 + CoT 6분 |
| 응답 길이 | baseline 697자 → epoch1~3 ~280자 → epoch4 555(붕괴) → epoch5 811 |
| Eval loss 곡선 | 0.95 → 0.94 → 0.96 → 1.04 → 1.11 |
| Stage A 통과율 | 2,780 → 2,551 (91.8%) |
| Token collapse | epoch4 27/138 (19.6%), epoch5 92/138 (66.7%) |

---

## 부록 B: 첫 응답 템플릿

새 세션이 사용자의 첫 질문을 받았을 때 따라야 할 응답 패턴:

1. **질문 의도 파악** — 이게 정보 요청인지, 작업 요청인지, 디버깅인지
2. **§5 라우팅으로 필요 문서 lazy load** — 다 읽지 말고 해당 섹션만
3. **답변** — 정보 요청이면 직접 답, 작업 요청이면 §3.2 논의 프로토콜 시작
4. **확인** — 작업 요청에는 마지막에 "이 방향으로 갈까요?" 또는 옵션 선택 요청

**예시 — 좋은 첫 응답**:
```
사용자: "Stage C 결과 다시 보고 싶어"

LLM (좋음):
[cat finetune/outputs/stage_c/scored_report.json | python -m json.tool 실행]
[결과 요약 + 핵심 발견 짚어주기]
```

**예시 — 나쁜 첫 응답**:
```
사용자: "Stage C 결과 다시 보고 싶어"

LLM (나쁨):
[먼저 RESULTS.md 전체를 view tool로 읽음]
[ARCHITECTURE.md도 추가로 읽음]
[그 다음 답변... 토큰 낭비, 사용자는 이미 결과 파일이 어디 있는지 안다]
[답변 후 "다음엔 이런 분석도 할 수 있어요" 미리보기 추가 — §3.5 위반]
```

---

## 문서 끝

**최종 갱신**: 2026-04-12
**버전**: v1.1
**v1.0 → v1.1**: §3.5 응답 스타일 규칙 신설 (토큰 절약, 미리보기 금지, 사용자 주도 흐름)
**다음 갱신 시점**: 발표 후 v11 작업 시작 시