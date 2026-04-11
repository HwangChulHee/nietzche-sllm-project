# 프로젝트 아키텍처

> 니체 페르소나 sLLM 캡스톤 프로젝트의 **구조 명세서**.
> "이 프로젝트가 뭐로 구성되어 있고 어디에 뭐가 있나"에 대한 답.
>
> 데이터셋 자체에 대한 내용은 [DATA_SPEC.md](./DATA_SPEC.md),
> 실행 명령은 [PIPELINE.md](./PIPELINE.md),
> 환경 설정은 [ENVIRONMENTS.md](./ENVIRONMENTS.md) 참고.

---

## 문서 목차

1. [프로젝트 한눈에 보기](#1-프로젝트-한눈에-보기)
2. [전체 데이터·코드 흐름](#2-전체-데이터코드-흐름)
3. [디렉토리 구조](#3-디렉토리-구조)
4. [컴포넌트 → 파일 매핑](#4-컴포넌트--파일-매핑)
5. [핵심 자산 위치 맵](#5-핵심-자산-위치-맵)
6. [외부 의존성](#6-외부-의존성)
7. [Git 추적 정책](#7-git-추적-정책)
8. [디스크 사용량](#8-디스크-사용량)
9. [재시작 후 빠르게 컨텍스트 잡기](#9-재시작-후-빠르게-컨텍스트-잡기)

---

# 1. 프로젝트 한눈에 보기

## 1.1 한 줄 요약

**니체 5권의 영어 원전을 한국어 SFT 데이터셋으로 변환하고, Gemma 4 31B에 LoRA로 학습시켜 니체 페르소나 한국어 sLLM을 만드는 캡스톤 프로젝트.**

## 1.2 핵심 숫자

| 항목 | 값 |
|---|---|
| 베이스 모델 | Gemma 4 31B (google/gemma-4-31B-it) |
| 학습 방식 | LoRA (r=16, 5 epochs) |
| 학습 데이터 | 2,413 샘플 |
| 평가 데이터 | 138 샘플 (held-out) |
| 원전 책 수 | 5권 (JW, BGE, GM, TI, EH) |
| 학습 시간 | 약 1시간 9분 (A100 80GB) |
| Stage B 평가 | 6 모델 × 138 샘플 = 828 응답 (94분) |
| Stage A 통과율 | 91.8% (2780 → 2551) |

## 1.3 발표 일정

- **발표일**: 2026-04-13
- **현재 단계**: Stage C 완료 (2026-04-11). 발표 자료 작성 단계.

## 1.4 주요 결정

| 결정 | 근거 |
|---|---|
| Gemma 4 31B 선택 | 한국어 성능 + 라이선스 + 적정 크기 |
| LoRA (not QLoRA) | A100 80GB 가용, bf16으로 정확도 보존 |
| 5 epoch 모두 보존 | best epoch 사후 결정, 오버핏 곡선 관찰 |
| 영어 원전 → 한국어 재구성 | 직역체 회피, 페르소나 반영 |
| LLM judge 기반 채점 | 스케일 가능, 인간 채점 비용 절감 |
| Stage A-Centric Dedup | 고품질 샘플 보존이 우선 |

---

# 2. 전체 데이터·코드 흐름

## 2.1 5단계 파이프라인

⚠️ **중요**: 실제 파이프라인은 아래 순서대로 실행됩니다. 데이터 생성 단계의
**한국어 재구성이 LLM 필터보다 먼저** 실행되며, 필터는 한국어 텍스트로 채점합니다.

```
[Stage 0]            [Stage 0.7]          [Stage 0.5]          [Stage 0.9]          [Stage A]            [학습]               [Stage B]            [Stage C]
원전 청킹       →    한국어 재구성   →    5축 LLM 채점   →    SFT 생성       →    품질 관리       →    LoRA 파인튜닝   →    응답 생성       →    채점

5권 영어 텍스트     Gemma 4 26B          Gemma 4 26B           청크당 3개          Clean → Score        Gemma 4 31B          baseline + 5        Gemma 4 26B judge
                    (한국어로 재작성)     (한국어로 채점)        (한 호출에 3개)      → Dedup → Select    + LoRA r=16          epochs 평가          Q1/Q2/Q3 + CoT
                                         + 책별 통과 조건                                                5 epochs                                  + collapse heuristic

v2_data/            v2_data/             v2_data/              v2_data/             v2_data/             finetune/            finetune/outputs/    finetune/outputs/
  english_raw/        reconstructed/       filtered/             sft_candidates/      sft_dataset/          outputs/              stage_b/              stage_c/
  english_chunks/     (973, 1:1)           (973 + scores         (~2780)             (train/eval)         nietzsche-lora-31b/   responses.jsonl       scored.jsonl
  (973)                                    + passed flag)                                                                       (828)                 scored_cot.jsonl
                                           928 passed                                                                                                 (828 × 2)
```

### filtered/ 디렉토리 주의사항

`filtered/`는 "통과한 청크만"이 아니라 "**채점 결과를 추가한 973개 전체**"를
담고 있습니다. `passed=True/False` 필드로 구분되며, 다음 단계(Stage 0.9)가
True인 928개만 사용합니다.

더 정확한 이름은 `scored_chunks/`였을 것. v11에서 리네이밍 검토.

## 2.2 단계별 입출력 요약

| 단계 | 코드 위치 | 입력 | 출력 | venv |
|---|---|---|---|---|
| Stage 0 | `v2_pipeline/english_chunker_*.py` × 5 | 원전 (txt) | 청크 (jsonl) | ml |
| **Stage 0.7** | `v2_pipeline/reconstructor.py` | english_chunks | reconstructed (한국어) | ml |
| **Stage 0.5** | `v2_pipeline/track_filter.py` | reconstructed | filtered (5축 채점 + passed) | ml |
| Stage 0.9 | `v2_pipeline/sft_generator.py` | filtered (passed만) | sft_candidates/candidates.jsonl | ml |
| Stage A-1 | `v2_pipeline/stage_a_clean.py` | candidates.jsonl | cleaned.jsonl | ml |
| Stage A-2 | `v2_pipeline/stage_a_score.py` | cleaned.jsonl | scored.jsonl | ml |
| Stage A-3 | `v2_pipeline/stage_a_dedup.py` | scored.jsonl | deduped.jsonl | ml |
| Stage A-4 | `v2_pipeline/stage_a_select.py` | deduped.jsonl | train/eval.jsonl | ml |
| 학습 | `finetune/scripts/train.py` | train.jsonl | LoRA 체크포인트 5개 | finetune |
| Merge | `finetune/scripts/merge_one.py` | LoRA + base | merged 모델 (62GB) | finetune |
| Stage B | `finetune/scripts/stage_b_generate.py` | merged + eval.jsonl | responses.jsonl | ml |
| Stage C | `finetune/scripts/stage_c_score.py` | responses.jsonl + eval.jsonl | `stage_c/scored*.jsonl` | ml |
| Stage C 리포트 | `finetune/scripts/stage_c_report.py` | scored.jsonl | `stage_c/report.md` | ml |

> ⚠️ **중요**: Stage 0.7이 Stage 0.5보다 **먼저** 실행됩니다. LLM judge는
> 한국어로 재구성된 텍스트를 채점합니다. 자세한 사항은 [DATA_SPEC.md §9.1](./DATA_SPEC.md) 참고.

**중요**: 학습은 `finetune` venv, 나머지는 모두 `ml` venv. 자세한 사항은 [ENVIRONMENTS.md](./ENVIRONMENTS.md).

## 2.3 외부 시스템과의 관계

```
                ┌───────────────────────────┐
                │   RunPod A100 80GB Pod    │
                │                           │
   GitHub  ←──→ │  /workspace/              │
                │    nietzche-sllm-project/ │
                │    └── ml/                │
                │         ├── v2_data/      │
                │         ├── v2_pipeline/  │
                │         ├── finetune/     │
                │         ├── docs/         │
                │         └── .venv/ × 2    │
                │                           │
                └───────────┬───────────────┘
                            │
            ┌───────────────┼─────────────────┐
            │               │                 │
            ↓               ↓                 ↓
       HF Hub          wandb            (Stage A 채점 시)
       LoRA 모델       학습 로그        로컬 vLLM judge 서버
       업로드          searchformaat
```

---

# 3. 디렉토리 구조

## 3.1 최상위 (`/workspace/nietzche-sllm-project/`)

```
nietzche-sllm-project/
├── ml/                   ⭐ ML 관련 모든 작업 (이 문서의 주 대상)
├── app/                  앱 (frontend + backend, 별도 워크스트림)
├── scripts/              setup 등 보조 스크립트
├── README.md             (오래됨, 발표 전 재작성 예정)
├── CLAUDE.md             AI 어시스턴트용 컨텍스트
├── docker-compose.yml    로컬 개발 환경 (app 용)
└── .gitignore            (Stage B 결과/로그 예외 처리됨)
```

**이 프로젝트의 모든 ML 작업은 `ml/` 안에서 일어납니다**. `app/`은 별도 워크스트림이며 발표 우선순위에서 후순위.

## 3.2 `ml/` 디렉토리 (정리 후)

```
ml/
├── docs/                          ⭐ 모든 문서 (지금 만들고 있는 곳)
│   ├── DATA_SPEC.md               데이터셋 명세 (v10.0.1)
│   ├── ARCHITECTURE.md            이 문서
│   ├── PIPELINE.md                실행 가이드
│   ├── SFT_STRATEGY.md            학습 전략
│   ├── ENVIRONMENTS.md            환경 설정
│   ├── RESULTS.md                 결과 정리
│   ├── LLM_ONBOARDING.md          새 LLM 세션용
│   ├── GLOSSARY.md                니체 용어 매핑
│   └── archived/
│       └── REFACTOR_PLAN.md       (참고용 보관)
│
├── v2_pipeline/                   ⭐ 데이터 파이프라인 코드 (Stage 0 + Stage A)
│   ├── english_chunker_bge.py     BGE 청커
│   ├── english_chunker_eh.py      EH 청커
│   ├── english_chunker_gm.py      GM 청커
│   ├── english_chunker_gs.py      JW 청커 (파일명만 gs)
│   ├── english_chunker_ti.py      TI 청커
│   ├── reconstructor.py           Stage 0.7: 한국어 재구성
│   ├── track_filter.py            Stage 0.5: 3-Track LLM 필터
│   ├── sft_generator.py           Stage 0.9: SFT 샘플 생성
│   ├── stage_a_clean.py           Stage A-1: 자동 검사
│   ├── stage_a_score.py           Stage A-2: LLM judge 채점
│   ├── stage_a_dedup.py           Stage A-3: A-centric dedup
│   ├── stage_a_select.py          Stage A-4: stratified split
│   ├── verify_chunks.py           청크 산출물 검증
│   ├── REFACTOR_PLAN.md           v2 리팩토링 계획 (보류)
│   ├── glossary.md                니체 용어 매핑 (원본)
│   ├── prompts/
│   │   └── reconstruction.txt     재구성 프롬프트
│   └── scripts/
│       └── test_reconstruct.py    재구성 테스트
│
├── v2_data/                       ⭐ 데이터 자산 (모든 중간 결과 포함)
│   ├── english_raw/               5권 영어 원전 (4.0M)
│   │   ├── beyond-good-and-evil.txt
│   │   ├── ecce-homo.txt
│   │   ├── the-genealogy-of-morals.txt
│   │   ├── the-joyful-wisdom.txt
│   │   └── the-twilight-of-the-idols.txt
│   ├── english_chunks/            Stage 0 결과 (3.6M)
│   │   ├── bge.jsonl
│   │   ├── eh.jsonl
│   │   ├── gm.jsonl
│   │   ├── gs.jsonl               (= JW)
│   │   └── ti.jsonl
│   ├── filtered/                  Stage 0.5 결과 (5.6M)
│   │   └── {bge,eh,gm,gs,ti}.jsonl
│   ├── reconstructed/             Stage 0.7 결과 (5.4M, 한국어)
│   │   └── {bge,eh,gm,gs,ti}.jsonl
│   ├── sft_candidates/            Stage A 중간 산출물 (18M)
│   │   ├── candidates.jsonl       (Stage 0.9 직후, 2780)
│   │   ├── cleaned.jsonl          (A-1 후, 2728)
│   │   ├── cleaned_report.json
│   │   ├── scored.jsonl           (A-2 후, 2728)
│   │   ├── scored_report.json
│   │   ├── deduped.jsonl          (A-3 후, 2725)
│   │   └── dedup_report.json
│   └── sft_dataset/               ⭐ 최종 데이터 (5.7M)
│       ├── train.jsonl            (2413, 학습용)
│       ├── eval.jsonl             (138, held-out)
│       └── select_report.json
│
├── finetune/                      ⭐ 학습 + Stage B 평가
│   ├── .venv/                     학습 전용 venv (gitignore)
│   ├── pyproject.toml             poetry 관리
│   ├── poetry.lock
│   ├── poetry.toml                in-project venv 설정
│   ├── setup.sh                   환경 설정 스크립트 (귀중)
│   ├── data/                      train.jsonl + eval.jsonl 복사본
│   │                              (v2_data/sft_dataset과 동일)
│   ├── scripts/
│   │   ├── train.py               LoRA 학습 (Unsloth)
│   │   ├── merge_one.py           Stage B-1: 단일 epoch merge
│   │   ├── stage_b_generate.py    Stage B-2: vLLM 추론
│   │   ├── run_stage_b.sh         Stage B 오케스트레이션
│   │   ├── stage_b_stats.py       Stage B 결과 통계
│   │   ├── upload_lora.py         HF Hub 업로드
│   │   ├── test_a_vllm_baseline.py  검증 테스트 A
│   │   ├── test_b1_merge_epoch1.py  검증 테스트 B1 (peft 시도)
│   │   ├── test_b1_merge_epoch1_unsloth.py  B1 (Unsloth, 성공)
│   │   ├── test_b2_vllm_merged.py   검증 테스트 B2
│   │   ├── run_judge_server.sh      Stage C: judge vLLM 서버
│   │   ├── stage_c_score.py         Stage C: 채점 (Q1/Q2/Q3 + CoT)
│   │   └── stage_c_report.py        Stage C: breakdown 리포트
│   ├── outputs/
│   │   ├── nietzsche-lora-31b/    ⭐ LoRA 체크포인트 (4.4G, gitignore)
│   │   │   ├── README.md          모델 카드
│   │   │   ├── checkpoint-144/    epoch 1
│   │   │   ├── checkpoint-288/    epoch 2 (eval loss 최저)
│   │   │   ├── checkpoint-432/    epoch 3
│   │   │   ├── checkpoint-576/    epoch 4
│   │   │   ├── checkpoint-720/    epoch 5 (오버핏)
│   │   │   └── final/             trainer 자동 저장 (= epoch 5)
│   │   ├── stage_b/               ⭐ Stage B 결과 (3.8M, git 추적)
│   │   │   ├── responses.jsonl    828 응답 (1.8M)
│   │   │   └── responses.jsonl.bak  baseline만의 백업 (93K)
│   │   └── stage_b_test/          검증 테스트 결과 (1.4M, git 추적)
│   │       ├── test_a_baseline.jsonl    (138 baseline 응답)
│   │       └── test_b2_epoch1.jsonl     (5 epoch1 비교용)
│   ├── logs/                      모든 실행 로그 (1.2M, git 추적)
│   │   ├── train_31b_full.log     학습 로그 (309K)
│   │   ├── stage_b_run.log        Stage B 마스터 로그 (350K)
│   │   ├── stage_b_baseline.log
│   │   ├── stage_b_epoch1.log ~ stage_b_epoch5.log
│   │   ├── merge_epoch2.log ~ merge_epoch5.log
│   │   ├── test_a.log
│   │   ├── test_b1.log, test_b1_unsloth.log
│   │   ├── test_b2.log
│   │   └── stage_b_generate.log
│   └── wandb/                     wandb run 캐시 (gitignore)
│
├── .venv/                         ml venv (gitignore)
├── pyproject.toml                 ml venv poetry
└── poetry.lock
```

## 3.3 두 venv 구조 (중요)

| venv | 경로 | 용도 | torch | 핵심 패키지 |
|---|---|---|---|---|
| **ml** | `ml/.venv/` | 데이터 생성, 평가 추론 | 2.10 | vllm 0.19, transformers 5.5, BGE-M3 |
| **finetune** | `ml/finetune/.venv/` | LoRA 학습, merge | 2.6 | unsloth, peft 0.18, trl, bitsandbytes |

**병합 불가**. torch 버전이 다르고, vLLM과 Unsloth는 서로 다른 torch를 요구합니다. 자세한 사항은 [ENVIRONMENTS.md](./ENVIRONMENTS.md) 참고.

---

# 4. 컴포넌트 → 파일 매핑

## 4.1 데이터 생성 (Stage 0 ~ 0.9)

| 컴포넌트 | 역할 | 파일 | venv | 입력 | 출력 |
|---|---|---|---|---|---|
| BGE Chunker | 선악의 저편 청킹 (296 expected) | `v2_pipeline/english_chunker_bge.py` | ml | `english_raw/beyond-good-and-evil.txt` | `english_chunks/bge.jsonl` |
| EH Chunker | 이 사람을 보라 청킹 (5 메인 챕터 + sub_chapter 자동 분리) | `v2_pipeline/english_chunker_eh.py` | ml | `english_raw/ecce-homo.txt` | `english_chunks/eh.jsonl` |
| GM Chunker | 도덕의 계보 청킹 (3 essay + preface) | `v2_pipeline/english_chunker_gm.py` | ml | `english_raw/the-genealogy-of-morals.txt` | `english_chunks/gm.jsonl` |
| JW Chunker | 즐거운 학문 청킹 (383 expected) | `v2_pipeline/english_chunker_gs.py` | ml | `english_raw/the-joyful-wisdom.txt` | `english_chunks/gs.jsonl` |
| TI Chunker | 우상의 황혼 청킹 (11 챕터, Antichrist 제외) | `v2_pipeline/english_chunker_ti.py` | ml | `english_raw/the-twilight-of-the-idols.txt` | `english_chunks/ti.jsonl` |
| **Verify Chunks** | **5권 청킹 결과 검증 (expected_total + 짧은/긴/빈/중복 검사)** | `v2_pipeline/verify_chunks.py` | ml | `english_chunks/*.jsonl` | (stdout) |
| **Reconstructor (Stage 0.7)** | **한국어 재구성 (Gemma 4 26B, temp 0.3)** | `v2_pipeline/reconstructor.py` | ml | `english_chunks/*.jsonl` | `reconstructed/*.jsonl` |
| **Track Filter (Stage 0.5)** | **5축 LLM 채점 + 책별 통과 조건 (TI 챕터별 11가지 조건 포함)** | `v2_pipeline/track_filter.py` | ml | `reconstructed/*.jsonl` | `filtered/*.jsonl` |
| SFT Generator | 청크당 3개 SFT 생성 (한 LLM 호출, temp 0.85) | `v2_pipeline/sft_generator.py` | ml | `filtered/*.jsonl` (passed만) | `sft_candidates/candidates.jsonl` |

> ⚠️ **순서 주의**: Reconstructor (0.7)가 Track Filter (0.5)보다 먼저 실행됩니다.
> 디렉토리 이름의 숫자(0.5, 0.7)는 설계 시점의 의도였고 실제 실행 순서는 다릅니다.

### 5축 평가 (track_filter.py)

LLM이 한국어로 재구성된 청크를 5축으로 채점:
1. `track_existential` — 현대인 고민에 응답 가능?
2. `track_philosophical` — 개념·논증 명확?
3. `track_biographical` — 자기 삶 서술?
4. `self_contained` — 청크 단독 의미 통함?
5. `density` — 통찰 압축도?

각 축 1~5점. 책별 통과 조건은 5권 모두 다름. 자세한 사항은
[DATA_SPEC.md §9.4](./DATA_SPEC.md) 참고.

### 통과율 (실측)

| 책 | 통과율 |
|---|---|
| EH | 65/66 (98.5%) — density 검사 없어 가장 높음 |
| JW | 376/383 (98.2%) — OR 조건 |
| TI | 143/151 (94.7%) — 챕터별 다른 조건 |
| BGE | 274/296 (92.6%) |
| GM | 70/77 (90.9%) — **가장 엄격** |
| **합계** | **928/973 (95.4%)** |

## 4.2 데이터 품질 관리 (Stage A)

| 컴포넌트 | 역할 | 파일 | venv | 입력 | 출력 |
|---|---|---|---|---|---|
| Stage A-1 Clean | 자동 검사 + enum 정규화 | `v2_pipeline/stage_a_clean.py` | ml | `candidates.jsonl` (2780) | `cleaned.jsonl` (2728) + `cleaned_report.json` |
| Stage A-2 Score | LLM judge 3축 채점 | `v2_pipeline/stage_a_score.py` | ml | `cleaned.jsonl` | `scored.jsonl` + `scored_report.json` |
| Stage A-3 Dedup | A-centric MinHash dedup | `v2_pipeline/stage_a_dedup.py` | ml | `scored.jsonl` | `deduped.jsonl` (2725) + `dedup_report.json` |
| Stage A-4 Select | Stratified split | `v2_pipeline/stage_a_select.py` | ml | `deduped.jsonl` | `train.jsonl` (2413) + `eval.jsonl` (138) + `select_report.json` |

## 4.3 학습

| 컴포넌트 | 역할 | 파일 | venv | 입력 | 출력 |
|---|---|---|---|---|---|
| Train | LoRA 학습 (Unsloth) | `finetune/scripts/train.py` | finetune | `finetune/data/train.jsonl` | `finetune/outputs/nietzsche-lora-31b/checkpoint-{144,288,432,576,720}` |
| Upload | HF Hub 업로드 | `finetune/scripts/upload_lora.py` | finetune | LoRA 체크포인트 5개 | HF Hub: `banzack/nietzsche-gemma4-31b-lora` (5 branches) |

**학습 설정**:
- LoRA r=16, alpha=32
- target_modules: q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj
- bf16 (not 4bit)
- 5 epochs, save_strategy=epoch
- learning_rate=2e-4, lr_scheduler=cosine
- batch_size=2, grad_accumulation=8 (effective 16)
- 학습 시간: 약 1시간 9분 (A100 80GB)
- wandb run: searchformaat

### Merge 메커니즘 (중요)

`merge_one.py`는 PyTorch + peft 사용자가 헤매기 쉬운 부분이 있어서 명시:

```python
# Unsloth는 checkpoint 경로를 직접 받음 (base 모델 + adapter 자동 처리)
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=str(checkpoint),  # = nietzsche-lora-31b/checkpoint-288
    max_seq_length=1024,         # 학습 시 384보다 길게
    dtype=None,                  # auto bf16
    load_in_4bit=False,
)

# bf16으로 merge + 저장 (한 줄)
model.save_pretrained_merged(
    str(output),
    tokenizer,
    save_method="merged_16bit",  # bf16
)
```

**주의 사항**:
- peft의 `PeftModel.merge_and_unload()` 사용 시 Gemma4ClippableLinear 에러 발생
- Unsloth만이 Gemma 4 신규 layer를 정상 merge
- merge 후 디렉토리 ~62GB. 검증(safetensors + config.json) 후 자동 cleanup
- idempotent: 이미 merge된 epoch는 SKIP

## 4.4 Stage B (응답 생성)

| 컴포넌트 | 역할 | 파일 | venv | 입력 | 출력 |
|---|---|---|---|---|---|
| Test A | vLLM baseline sanity check | `finetune/scripts/test_a_vllm_baseline.py` | ml | base 모델 + eval | `stage_b_test/test_a_baseline.jsonl` |
| Test B1 (peft) | merge 시도 (실패) | `finetune/scripts/test_b1_merge_epoch1.py` | finetune | LoRA + base | (실패: Gemma4ClippableLinear) |
| Test B1 (Unsloth) | merge 시도 (성공) | `finetune/scripts/test_b1_merge_epoch1_unsloth.py` | finetune | LoRA + base | merged 모델 |
| Test B2 | merged 모델 검증 | `finetune/scripts/test_b2_vllm_merged.py` | ml | merged 모델 + eval (5개) | `stage_b_test/test_b2_epoch1.jsonl` |
| Merge One | 단일 epoch merge (Unsloth checkpoint 직접 로드 + save_pretrained_merged) | `finetune/scripts/merge_one.py` | finetune | epoch N checkpoint | merged/epochN/ (62GB) |
| Generate | vLLM 추론 | `finetune/scripts/stage_b_generate.py` | ml | merged + eval.jsonl | `stage_b/responses.jsonl` (append) |
| Run Stage B | 오케스트레이션 | `finetune/scripts/run_stage_b.sh` | (둘 다) | — | 6 모델 × 138 응답 = 828 |
| Stats | 결과 통계 | `finetune/scripts/stage_b_stats.py` | ml | `stage_b/responses.jsonl` | (stdout) |

**Stage B 흐름**:
```
1. baseline 평가      (ml venv)        → responses.jsonl (138)
2. epoch1 merge       (finetune venv)  → merged/epoch1/
3. epoch1 평가        (ml venv)        → responses.jsonl (276)
4. epoch1 merged 삭제 (디스크 정리)
5. epoch2 merge       (finetune venv)  → merged/epoch2/
6. epoch2 평가        (ml venv)        → responses.jsonl (414)
... (epoch3, 4, 5 반복)
```

총 시간: 94분 (예상 170분의 절반, vLLM 캐시 효과)

## 4.5 Stage C

| 컴포넌트 | 역할 | 파일 | venv |
|---|---|---|---|
| Judge Server | Gemma 4 26B-A4B vLLM 서버 (Stage A와 동일) | `finetune/scripts/run_judge_server.sh` | ml |
| Stage C Score | Q1/Q2/Q3 채점 + collapse heuristic + CoT(`--with-reasoning`) | `finetune/scripts/stage_c_score.py` | ml |
| Stage C Report | 모델 × voice × pattern breakdown 마크다운 | `finetune/scripts/stage_c_report.py` | ml |

`stage_a_score.py` 패턴을 따르되, 입력은 `responses.jsonl × eval.jsonl` join,
출력은 `model_tag` 보존 + 점수만 / CoT 두 모드 분리(`scored.jsonl` / `scored_cot.jsonl`).
Collapse 응답은 judge 호출 없이 heuristic으로 (1,1,1)점 자동 부여.

---

# 5. 핵심 자산 위치 맵

## 5.1 데이터 자산

| 자산 | 경로 | 크기 | git | HF |
|---|---|---|---|---|
| 원전 (5권) | `ml/v2_data/english_raw/*.txt` | 4.0M | ✓ | — |
| 청크 | `ml/v2_data/english_chunks/*.jsonl` | 3.6M | ✓ | — |
| 필터 통과 청크 | `ml/v2_data/filtered/*.jsonl` | 5.6M | ✓ | — |
| 한국어 재구성 | `ml/v2_data/reconstructed/*.jsonl` | 5.4M | ✓ | — |
| Stage A 중간 (cleaned/scored/deduped) | `ml/v2_data/sft_candidates/*.jsonl` | 18M | ✓ | — |
| Stage A 리포트 | `ml/v2_data/sft_candidates/*_report.json` | 작음 | ✓ | — |
| **최종 train** | `ml/v2_data/sft_dataset/train.jsonl` | 3.6M | ✓ | — |
| **최종 eval** | `ml/v2_data/sft_dataset/eval.jsonl` | 208K | ✓ | — |
| Select 리포트 | `ml/v2_data/sft_dataset/select_report.json` | 2K | ✓ | — |

**중복**: `ml/finetune/data/{train,eval}.jsonl`은 위 train/eval과 동일 내용 (학습 편의용 복사본). `train.py`가 이것을 참조. 발표 후 정리 가능.

## 5.2 모델 자산

| 자산 | 경로 | 크기 | git | HF |
|---|---|---|---|---|
| LoRA epoch1 | `ml/finetune/outputs/nietzsche-lora-31b/checkpoint-144/` | 800M+ | ❌ | ✓ branch `epoch1` |
| LoRA epoch2 | `.../checkpoint-288/` | 800M+ | ❌ | ✓ `epoch2` |
| LoRA epoch3 | `.../checkpoint-432/` | 800M+ | ❌ | ✓ `epoch3` |
| LoRA epoch4 | `.../checkpoint-576/` | 800M+ | ❌ | ✓ `epoch4` |
| LoRA epoch5 | `.../checkpoint-720/` | 800M+ | ❌ | ✓ `epoch5` |
| LoRA final | `.../final/` | 800M+ | ❌ | (= epoch5) |
| **HF Hub 전체** | `banzack/nietzsche-gemma4-31b-lora` | — | — | private, 5 branches |

총 4.4G. gitignore로 제외 (대용량). 백업은 HF Hub.

## 5.3 평가 결과

| 자산 | 경로 | 크기 | git |
|---|---|---|---|
| **Stage B 응답** | `ml/finetune/outputs/stage_b/responses.jsonl` | 1.8M | ✓ |
| Stage B 백업 | `ml/finetune/outputs/stage_b/responses.jsonl.bak` | 93K | ✓ |
| Test A 결과 | `ml/finetune/outputs/stage_b_test/test_a_baseline.jsonl` | 415K | ✓ |
| Test B2 결과 | `ml/finetune/outputs/stage_b_test/test_b2_epoch1.jsonl` | 10K | ✓ |

828 레코드 (baseline + 5 epochs × 138 eval).

## 5.4 로그

| 자산 | 경로 | 크기 | git |
|---|---|---|---|
| 학습 로그 | `ml/finetune/logs/train_31b_full.log` | 309K | ✓ |
| Stage B 마스터 로그 | `ml/finetune/logs/stage_b_run.log` | 350K | ✓ |
| Stage B 모델별 로그 | `ml/finetune/logs/stage_b_{baseline,epoch1~5}.log` | 각 17~22K | ✓ |
| Merge 로그 (epoch2~5) | `ml/finetune/logs/merge_epoch{2,3,4,5}.log` | 각 53~61K | ✓ |
| Test 로그 | `ml/finetune/logs/test_{a,b1,b1_unsloth,b2}.log` | 각 7~62K | ✓ |
| Stage B 초기 로그 | `ml/finetune/logs/stage_b_generate.log` | 63K | ✓ |

총 1.2M, 모두 git 추적 (재현 가능성).

## 5.5 코드

| 자산 | 경로 | 크기 | git |
|---|---|---|---|
| Stage 0 + Stage A 코드 | `ml/v2_pipeline/*.py` (15 파일) | 2.2M (포함 prompts/scripts) | ✓ |
| 학습 + Stage B 코드 | `ml/finetune/scripts/*.py` (10 파일) | 60K | ✓ |
| 환경 설정 | `ml/finetune/setup.sh` | 4.6K | ✓ |
| Poetry 설정 | `ml/{,finetune/}pyproject.toml`, `poetry.lock` | — | ✓ |

## 5.6 문서

| 자산 | 경로 | 크기 | 상태 |
|---|---|---|---|
| **DATA_SPEC** | `ml/docs/DATA_SPEC.md` | 73K (v10.0.1) | ✓ 완료 |
| **ARCHITECTURE** | `ml/docs/ARCHITECTURE.md` | (이 문서) | ✓ 작성 중 |
| PIPELINE | `ml/docs/PIPELINE.md` | — | ✓ 완료 |
| SFT_STRATEGY | `ml/docs/SFT_STRATEGY.md` | — | ✓ 완료 |
| ENVIRONMENTS | `ml/docs/ENVIRONMENTS.md` | — | ✓ 완료 |
| RESULTS | `ml/docs/RESULTS.md` | — | ✓ 완료 (Stage C 결과 포함) |
| LLM_ONBOARDING | `ml/docs/LLM_ONBOARDING.md` | — | ✓ 완료 |
| GLOSSARY | `ml/docs/GLOSSARY.md` | 1K | ✓ |
| (보관) REFACTOR_PLAN | `ml/docs/archived/REFACTOR_PLAN.md` | 13K | ✓ |

---

# 6. 외부 의존성

## 6.1 필수 외부 시스템

| 시스템 | 용도 | 비고 |
|---|---|---|
| **RunPod** | A100 80GB GPU pod | 유럽 리전, /workspace 500GB volume |
| **HuggingFace Hub** | LoRA 모델 백업, 베이스 모델 다운로드 | `huggingface-cli login` 필요 |
| **wandb** | 학습 로그 추적 | run 이름: `searchformaat` |
| **GitHub** | 코드 관리 | `https://github.com/HwangChulHee/nietzche-sllm-project` |

## 6.2 베이스 모델

| 모델 | 출처 | 용도 |
|---|---|---|
| `google/gemma-4-31B-it` | HF Hub | 학습 베이스 + Stage B baseline |
| `google/gemma-4-26B-A4B-it` | HF Hub | Stage A judge + Stage C judge (점수만 + CoT) |
| `BAAI/bge-m3` | HF Hub | Stage A-3 dedup 임베딩 |

## 6.3 핵심 라이브러리

### ml venv
- vllm 0.19.0 (cu128 빌드, cu130은 driver 호환 X)
- torch 2.10
- transformers 5.5.0 (Gemma 4 지원 필수)
- BGE-M3 (sentence-transformers)
- datasets, jsonlines

### finetune venv
- unsloth (git installed)
- unsloth_zoo
- torch 2.6.0 (cu124 빌드)
- xformers 0.0.29.post3
- peft 0.18.1
- trl, accelerate, bitsandbytes
- torchao 0.12.0 (강제 다운그레이드, 0.13+는 torch 2.7 API 사용)
- triton 3.2.0

자세한 사항과 설치 함정은 [ENVIRONMENTS.md](./ENVIRONMENTS.md) 참고.

---

# 7. Git 추적 정책

## 7.1 추적 포함 (✓)

- 모든 코드 (`v2_pipeline/`, `finetune/scripts/`)
- 모든 데이터 (`v2_data/` 전체, 44M)
- 모든 문서 (`docs/`)
- 모든 로그 (`finetune/logs/`, 1.2M)
- Stage B 결과 (`finetune/outputs/stage_b/`, 3.8M)
- Stage B 테스트 결과 (`finetune/outputs/stage_b_test/`, 1.4M)
- LoRA 모델 카드 (`finetune/outputs/nietzsche-lora-31b/README.md`)
- 환경 설정 (`pyproject.toml`, `poetry.lock`, `setup.sh`)

## 7.2 추적 제외 (❌)

- LoRA 체크포인트 (`finetune/outputs/nietzsche-lora-31b/checkpoint-*/`, 4.4G) → HF Hub로 백업
- merged 모델 (`finetune/outputs/merged/`, 임시) — 이미 비어있음
- venv (`ml/.venv/`, `finetune/.venv/`)
- wandb 캐시 (`finetune/wandb/`)
- Unsloth 컴파일 캐시 (`finetune/unsloth_compiled_cache/`)
- Jupyter 캐시 (`.ipynb_checkpoints/`) — 가끔 다시 생김

## 7.3 .gitignore 핵심 규칙

```gitignore
# venv
ml/.venv/
ml/finetune/.venv/

# 대용량 모델
ml/finetune/outputs/nietzsche-lora-31b/
ml/finetune/outputs/merged/

# wandb / 컴파일 캐시
ml/finetune/wandb/
ml/finetune/unsloth_compiled_cache/

# Jupyter
.ipynb_checkpoints/

# === 예외: Stage B 결과는 추적 ===
!ml/finetune/outputs/stage_b/
!ml/finetune/outputs/stage_b/*.jsonl
!ml/finetune/outputs/stage_b/*.json
!ml/finetune/outputs/stage_b_test/
!ml/finetune/outputs/stage_b_test/*.jsonl
!ml/finetune/logs/
!ml/finetune/logs/*.log
```

## 7.4 커밋 히스토리 (주요)

```
efb9926 docs(spec): rewrite DATA_SPEC.md as v10.0.1
87106f2 chore: cleanup directory structure and organize docs
e1a0e98 logs(stage_b): execution logs for reproducibility
0f4245d data(stage_b): 828 model responses
9aa4fba feat(stage_b): evaluation pipeline for baseline + 5 LoRA epochs
5aa7ad9 gitignore: allow stage_b results and logs for reproducibility
```

---

# 8. 디스크 사용량

## 8.1 ml/ 안 (정리 후)

| 디렉토리 | 크기 | 비고 |
|---|---|---|
| `v2_data/` | 44M | 전체 데이터 자산 (입력~최종) |
| `v2_pipeline/` | 2.2M | 코드만 |
| `docs/` | 3.0M | 문서 (DATA_SPEC 73K 포함) |
| `finetune/` | **15G** | 대부분 venv + 체크포인트 |

## 8.2 finetune/ 내부

| 항목 | 크기 | git |
|---|---|---|
| `.venv/` | ~10G | ❌ |
| `outputs/nietzsche-lora-31b/` | 4.4G | ❌ |
| `outputs/stage_b/` | 3.8M | ✓ |
| `outputs/stage_b_test/` | 1.4M | ✓ |
| `logs/` | 1.2M | ✓ |
| `data/` | 4M | ✓ (중복) |
| `wandb/` | 작음 | ❌ |

## 8.3 정리 가능 항목 (필요 시)

| 항목 | 절약 가능 | 영향 |
|---|---|---|
| `finetune/data/` | 4M | train.py 수정 또는 symlink 필요 |
| `finetune/outputs/stage_b/responses.jsonl.bak` | 93K | 백업 (이미 main에 포함) |
| HF Hub 백업 후 LoRA 체크포인트 | 4.4G | 재다운로드 가능 |
| venv (재설치 가능) | 10G | `setup.sh` 재실행 필요 |

---

# 9. 재시작 후 빠르게 컨텍스트 잡기

## 9.1 새 LLM 세션 시작 시

이 순서로 읽으면 5분 안에 컨텍스트 확보:

1. **이 문서 (`ARCHITECTURE.md`)** — 전체 구조 파악
2. **`docs/DATA_SPEC.md`** — 데이터셋 상세
3. **`finetune/outputs/stage_b/responses.jsonl`** 한두 줄 — 실제 응답 확인
4. **`finetune/logs/stage_b_run.log`** 마지막 100줄 — 최근 작업 컨텍스트
5. **`docs/RESULTS.md`** (있으면) — 결과 요약

## 9.2 새 pod 시작 시

1. git safe directory:
   ```bash
   git config --global --add safe.directory /workspace/nietzche-sllm-project
   ```
2. venv 활성화:
   ```bash
   # 데이터/평가 작업
   source /workspace/nietzche-sllm-project/ml/.venv/bin/activate
   
   # 학습/merge 작업
   source /workspace/nietzche-sllm-project/ml/finetune/.venv/bin/activate
   ```
3. 환경 변수:
   ```bash
   export HF_HOME=/workspace/.cache/huggingface
   export PIP_CACHE_DIR=/workspace/.cache/pip
   ```
4. 현재 상태 확인:
   ```bash
   cd /workspace/nietzche-sllm-project/ml
   git log --oneline -5
   nvidia-smi
   df -h /workspace
   ```

## 9.3 작업 재개 점검 명령

```bash
cd /workspace/nietzche-sllm-project/ml

# 데이터 무결성
wc -l v2_data/sft_dataset/train.jsonl   # 2413
wc -l v2_data/sft_dataset/eval.jsonl    # 138

# Stage B 진행도
wc -l finetune/outputs/stage_b/responses.jsonl  # 828

# 학습 결과
ls finetune/outputs/nietzsche-lora-31b/checkpoint-*/adapter_model.safetensors
# (5개 나와야 함, gitignore라 git에는 없지만 디스크엔 있음)

# HF Hub 모델 확인 (선택)
# https://huggingface.co/banzack/nietzsche-gemma4-31b-lora
```

## 9.4 알려진 함정

| 증상 | 원인 | 해결 |
|---|---|---|
| `dubious ownership in repository` | pod 재시작 | `git config --global --add safe.directory ...` |
| `peft merge`가 Gemma4ClippableLinear 에러 | peft가 Gemma 4 신규 layer 미지원 | Unsloth `save_pretrained_merged` 사용 |
| vLLM cu130 빌드 driver 호환 X | RunPod의 driver가 12.7 | cu128 빌드 사용 |
| transformers 5.5 metadata 경고 | vllm 0.19와 metadata mismatch | 무시 가능 |
| Flash Attention 2 미작동 | Gemma 4 + Unsloth 호환 이슈 | Xformers fallback (자동) |
| `torch.utils._pytree.register_constant` AttributeError | torchao 0.13+ 가 torch 2.7 API 사용 | torchao 0.12.0 강제 다운그레이드 |

자세한 사항은 [ENVIRONMENTS.md](./ENVIRONMENTS.md).

---

## 문서 끝

**최종 갱신**: 2026-04-11
**버전**: v1.0
**다음 갱신 예정**: Stage C 완료 후 §4.5 컴포넌트 표 업데이트
