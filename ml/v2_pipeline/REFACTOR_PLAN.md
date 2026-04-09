# v2_pipeline 리팩토링 계획 (Option A)

이 문서는 v2_pipeline 디렉토리를 정리하기 위한 인계 문서입니다.
새 LLM 세션에서 이 파일만 컨텍스트로 주면 리팩토링을 즉시 시작할 수 있습니다.

## 배경

니체 페르소나 SFT 파이프라인 (한국어 sLLM 캡스톤 프로젝트). 영어 원전(Gutenberg) → Gemma 4로 한국어 재구성 → SFT 데이터셋 생성 → QLoRA 파인튜닝.

현재 v2_pipeline은 동작하지만 파일이 평면적으로 흩어져 있고, 책 메타데이터가 4개 파일에 중복돼 있으며, 파이프라인을 한 번에 돌릴 스크립트가 없습니다.

## 현재 구조 (리팩토링 전)

```
ml/v2_pipeline/
  english_chunker_bge.py      # BGE 청커
  english_chunker_eh.py       # EH 청커
  english_chunker_gm.py       # GM 청커
  english_chunker_gs.py       # JW 청커 (파일명만 gs)
  english_chunker_ti.py       # TI 청커
  reconstructor.py            # 영→한 재구성
  track_filter.py             # 6축 LLM 채점 + 책별 통과 조건
  sft_generator.py            # 청크당 SFT 샘플 3개 생성
  stage_a_clean.py            # enum 정규화 + hygiene
  stage_a_score.py            # Q1~Q3 LLM 채점 (5점)
  stage_a_dedup.py            # MinHash + bge-m3 임베딩 dedup
  stage_a_select.py           # A+B 등급 → train/eval split
  verify_chunks.py            # 청커 산출물 검증
  glossary.md
  prompts/reconstruction.txt
  scripts/test_reconstruct.py
```

## 목표 구조 (리팩토링 후)

```
ml/v2_pipeline/
  works.py                    # 책 메타데이터 단일 출처 (NEW)
  chunkers/                   # 청커 모음
    __init__.py
    base.py                   # 공통 유틸 (선택)
    bge.py
    eh.py
    gm.py
    jw.py                     # english_chunker_gs.py 이름 변경
    ti.py
  reconstruct.py              # reconstructor.py 이름만 변경
  track_filter.py             # 그대로
  sft_generate.py             # sft_generator.py 이름만 변경
  stage_a/
    __init__.py
    clean.py
    score.py
    dedup.py
    select.py
  run_pipeline.py             # 전체 파이프라인 자동화 (NEW)
  pipeline_stats.py           # 통합 통계 리포트 (NEW)
  verify_chunks.py            # 그대로
  glossary.md
  prompts/
    reconstruction.txt
```

## 핵심 변경 사항

### 1. works.py (단일 메타데이터)

현재 4개 파일(`track_filter.py`, `sft_generator.py`, `stage_a_clean.py`, `stage_a_dedup.py`)에 다음 dict들이 중복돼 있음:

- `BOOK_FILES`: 책 약자 → 파일명 (gs.jsonl, bge.jsonl 등 — JW가 gs.jsonl인 이유는 historical, 변경 권장)
- `BOOK_VOICE`: 책 → voice (JW=contemplative, BGE/GM=polemical, TI/EH=hammer)
- `BOOK_PERIOD`: 책 → period (middle/late/final)
- `BOOK_FULL_NAMES`: 책 → "The Joyful Wisdom (즐거운 학문)" 형식 풀네임

이걸 `works.py` 단일 dataclass로 통합:

```python
from dataclasses import dataclass
from typing import Literal

Voice = Literal["contemplative_aphorism", "polemical_sharp", "hammer_intensified"]
Period = Literal["middle", "late", "final"]

@dataclass(frozen=True)
class Work:
    code: str               # "JW", "BGE", ...
    file_stem: str          # "jw" — 청크 파일명 stem (현재 JW만 "gs"인데 통일 권장)
    voice: Voice
    period: Period
    full_name_en: str       # "The Joyful Wisdom"
    full_name_ko: str       # "즐거운 학문"
    chunker_module: str     # "v2_pipeline.chunkers.jw"

WORKS: dict[str, Work] = {
    "JW": Work("JW", "jw", "contemplative_aphorism", "middle",
               "The Joyful Wisdom", "즐거운 학문",
               "v2_pipeline.chunkers.jw"),
    "BGE": Work("BGE", "bge", "polemical_sharp", "late",
                "Beyond Good and Evil", "선악의 저편",
                "v2_pipeline.chunkers.bge"),
    "GM": Work("GM", "gm", "polemical_sharp", "late",
               "Genealogy of Morals", "도덕의 계보",
               "v2_pipeline.chunkers.gm"),
    "TI": Work("TI", "ti", "hammer_intensified", "final",
               "Twilight of the Idols", "우상의 황혼",
               "v2_pipeline.chunkers.ti"),
    "EH": Work("EH", "eh", "hammer_intensified", "final",
               "Ecce Homo", "이 사람을 보라",
               "v2_pipeline.chunkers.eh"),
}

def get_work(code: str) -> Work:
    return WORKS[code]

def all_works() -> list[Work]:
    return list(WORKS.values())
```

**중요**: JW의 청크 파일이 현재 `gs.jsonl`인데 (옛 GS = Gay Science 약자 흔적), 리팩토링 때 `jw.jsonl`로 이름 변경 권장. 단 기존 v2_data/*/gs.jsonl 파일도 같이 rename 필요.

### 2. chunkers/ 디렉토리

- `english_chunker_bge.py` → `chunkers/bge.py`
- `english_chunker_eh.py` → `chunkers/eh.py`
- `english_chunker_gm.py` → `chunkers/gm.py`
- `english_chunker_gs.py` → `chunkers/jw.py`
- `english_chunker_ti.py` → `chunkers/ti.py`

각 chunker 파일 안에 `def main()` 또는 `def run()` 함수 노출하고, 모듈 import로 호출 가능하게. 현재는 `if __name__ == "__main__"`에서 main() 호출.

`chunkers/__init__.py`에서 모든 chunker 모듈 export.

옵션: `chunkers/base.py`에 공통 유틸 (CRLF 처리, 종료 마커 검색 등) 추출. 현재 5개 chunker에 비슷한 패턴 있음. 단 과한 추상화는 피할 것.

### 3. stage_a/ 디렉토리

- `stage_a_clean.py` → `stage_a/clean.py`
- `stage_a_score.py` → `stage_a/score.py`
- `stage_a_dedup.py` → `stage_a/dedup.py`
- `stage_a_select.py` → `stage_a/select.py`

각 모듈에 `def main()` 노출.

### 4. run_pipeline.py (NEW)

전체 파이프라인 자동 실행. 단계별 resume 가능:

```python
"""run_pipeline.py — Nietzsche SFT 파이프라인 전체 실행.

사용법:
    python -m v2_pipeline.run_pipeline                    # 전부
    python -m v2_pipeline.run_pipeline --book JW          # JW만
    python -m v2_pipeline.run_pipeline --from track_filter # 특정 단계부터
    python -m v2_pipeline.run_pipeline --skip dedup       # 특정 단계 건너뛰기
"""
import argparse
from importlib import import_module
from v2_pipeline.works import WORKS, all_works

STAGES = [
    ("chunk",        "v2_pipeline.chunkers.{book_module}"),
    ("reconstruct",  "v2_pipeline.reconstruct"),
    ("track_filter", "v2_pipeline.track_filter"),
    ("sft_generate", "v2_pipeline.sft_generate"),
    ("clean",        "v2_pipeline.stage_a.clean"),
    ("score",        "v2_pipeline.stage_a.score"),
    ("dedup",        "v2_pipeline.stage_a.dedup"),
    ("select",       "v2_pipeline.stage_a.select"),
]

def run_chunk_stage(books):
    for w in books:
        mod = import_module(w.chunker_module)
        print(f"\n[chunk] {w.code}")
        mod.main()

def run_reconstruct_stage(books):
    from v2_pipeline import reconstruct
    for w in books:
        reconstruct.run_for_book(w)  # 함수 추가 필요

# ... 각 단계 함수

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--book", help="단일 책 (chunk/reconstruct에만 적용)")
    parser.add_argument("--from", dest="from_stage", help="시작 단계")
    parser.add_argument("--skip", action="append", default=[], help="건너뛸 단계")
    parser.add_argument("--only", action="append", default=[], help="특정 단계만")
    args = parser.parse_args()

    books = [WORKS[args.book]] if args.book else all_works()

    stages_to_run = STAGES
    if args.from_stage:
        idx = next(i for i, (n, _) in enumerate(stages_to_run) if n == args.from_stage)
        stages_to_run = stages_to_run[idx:]
    if args.only:
        stages_to_run = [(n, m) for n, m in stages_to_run if n in args.only]
    stages_to_run = [(n, m) for n, m in stages_to_run if n not in args.skip]

    for name, _ in stages_to_run:
        runner = globals()[f"run_{name}_stage"]
        runner(books)

if __name__ == "__main__":
    main()
```

**주의**: 각 stage 모듈을 함수 호출 가능하게 리팩토링 필요. 현재는 `asyncio.run(main())` 패턴이라 함수 추출해서 import 가능하게 만들어야 함.

### 5. pipeline_stats.py (NEW)

전 단계 통계를 markdown으로 통합. 발표 자료 직행.

```python
"""pipeline_stats.py — 전 단계 통계를 통합 markdown 리포트로.

각 단계의 *_report.json + 산출 jsonl 파일을 읽어 종합.
출력: v2_data/PIPELINE_REPORT.md
"""
import json
from pathlib import Path
from collections import Counter
from datetime import datetime

DATA = Path("v2_data")
OUT = DATA / "PIPELINE_REPORT.md"

def stats_chunks():
    # v2_data/english_chunks/*.jsonl 책별 카운트
    ...

def stats_reconstructed():
    ...

def stats_track_filter():
    # filtered/*.jsonl + use_case 분포
    ...

def stats_sft_candidates():
    ...

def stats_stage_a():
    # cleaned_report.json, scored_report.json, dedup_report.json, select_report.json
    ...

def stats_final_dataset():
    # train.jsonl + eval.jsonl 분포 매트릭스
    ...

def main():
    sections = [
        ("# Nietzsche SFT Pipeline Report", []),
        (f"\nGenerated: {datetime.now().isoformat()}\n", []),
        ("## Stage 1: Chunking", stats_chunks()),
        ("## Stage 2: Reconstruction", stats_reconstructed()),
        ("## Stage 3: Track Filtering", stats_track_filter()),
        ("## Stage 4: SFT Generation", stats_sft_candidates()),
        ("## Stage 5: Stage A (Clean → Score → Dedup → Select)", stats_stage_a()),
        ("## Final Dataset", stats_final_dataset()),
    ]
    OUT.write_text("\n".join(...))

if __name__ == "__main__":
    main()
```

핵심 표 예시:

```markdown
## Stage 1: Chunking

| Book | Chunks | Avg Length | Min | Max |
|---|---|---|---|---|
| JW  | 383 | 1193 | 42 | 9692 |
| BGE | 296 | 1258 | 44 | 8058 |
| GM  | 77  | 4043 | 603 | 14279 |
| TI  | 151 | 1161 | 48 | 6357 |
| EH  | 66  | 3213 | 134 | 7958 |
| **Total** | **973** | | | |

## Stage 5: Final Dataset

Train: 2413 / Eval: 138

### Voice Distribution (train)
- contemplative_aphorism: 992 (41%)
- polemical_sharp: 872 (36%)
- hammer_intensified: 549 (23%)

### Pattern Distribution (train)
- reflection_reframing: 826
- ...
```

## 작업 순서 (체크리스트)

1. [ ] `works.py` 작성
2. [ ] `chunkers/` 디렉토리 만들고 5개 청커 이동 + import path 수정
3. [ ] `chunkers/__init__.py` 작성
4. [ ] `english_chunker_*.py` 옛 파일 삭제
5. [ ] `stage_a/` 디렉토리 만들고 4개 stage 이동
6. [ ] `stage_a/__init__.py` 작성
7. [ ] 옛 stage_a_*.py 삭제
8. [ ] `reconstructor.py` → `reconstruct.py`, `sft_generator.py` → `sft_generate.py` rename
9. [ ] 모든 모듈의 BOOK_* dict 제거하고 `from v2_pipeline.works import WORKS, get_work` 사용
10. [ ] 각 모듈에 `def main()` 또는 `def run_for_book(w: Work)` 함수 노출
11. [ ] `run_pipeline.py` 작성
12. [ ] `pipeline_stats.py` 작성
13. [ ] (선택) JW 청크 파일 `gs.jsonl` → `jw.jsonl` rename + 모든 참조 수정
14. [ ] 동작 확인: `python -m v2_pipeline.run_pipeline --only stats`
15. [ ] 이 REFACTOR_PLAN.md 파일을 `archive/`로 이동

## 주의 사항

### v2_data 보존
이미 생성된 v2_data/ 안의 파일들은 손대지 말 것. 리팩토링은 코드만. 데이터 재생성은 시간 낭비.

### 파일 이름 호환성
JW 청크 파일이 `gs.jsonl`인 게 historical 흔적. rename 결정하면:
- `mv v2_data/english_chunks/gs.jsonl v2_data/english_chunks/jw.jsonl`
- `mv v2_data/reconstructed/gs.jsonl v2_data/reconstructed/jw.jsonl`
- `mv v2_data/filtered/gs.jsonl v2_data/filtered/jw.jsonl`
- 모든 코드의 `"gs.jsonl"` 참조 수정
- source_ref 형식은 이미 `JW_s125`라 영향 없음

### 새 책 추가 시나리오 (Phase 2)
Daybreak (DB) 추가:
1. `chunkers/db.py` 작성 (책 형식에 맞게 — 불가피한 작업, 30분~2시간)
2. `works.py`의 `WORKS` dict에 1줄 추가
3. `python -m v2_pipeline.run_pipeline --book DB`
4. 끝

이게 리팩토링의 진짜 가치.

### 발표 가치
`pipeline_stats.py`가 만드는 markdown 리포트가 발표 자료 1장으로 직행 가능. 통계 표 + 분포 그림 (matplotlib 추가하면 더 좋음).

## 시간 예상

- works.py + chunkers 정리: 30분
- stage_a/ 정리: 15분
- 함수 추출 (각 모듈 main → 호출 가능 함수): 30분
- run_pipeline.py: 30분
- pipeline_stats.py: 30분
- 동작 확인 + 디버깅: 30분
- **총 약 2시간 30분**

## 컨텍스트: 현재 v2_data 상태 (리팩토링 시점 기준)

- english_chunks/: 5권 청크 973개
- reconstructed/: 한국어 재구성 973개
- filtered/: 트랙 필터 통과 918개 (94.4%)
- sft_candidates/candidates.jsonl: LLM 생성 SFT 후보 2780개
- sft_candidates/cleaned.jsonl: enum/hygiene 통과 2728
- sft_candidates/scored.jsonl: Q1~Q3 채점 완료 2728 (A 1726, B 828, C 162, F 12)
- sft_candidates/deduped.jsonl: 의미 dedup 후 2725
- sft_dataset/train.jsonl: 2413
- sft_dataset/eval.jsonl: 138

리팩토링 작업 시 이 데이터 그대로 활용. 코드 정리만 하면 됨.
