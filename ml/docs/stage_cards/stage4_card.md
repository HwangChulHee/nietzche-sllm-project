# Stage 4 카드: Anchor 매핑 (한↔영)

## 한 줄 요약
한국어 청크와 영어 Gutenberg 원전을 매핑해서 `text_en_anchor`를 채운다.

## 위치
**전체 파이프라인에서**: 6/8 단계 (Stage 0/1/2/3 완료 → **Stage 4** → Stage 5~7 → 파인튜닝)
**데이터 단위 변화**: 한국어 청크 (381개) → 한국어 + 영어 매핑된 청크 (381개, 동일)

## 입력
- `data/chunks/joyful_science_chunks_raw.jsonl` (Stage 3 출력, 381개 청크)
- `data/raw/joyful_science_english.txt` (Project Gutenberg, Thomas Common 등 번역)

## 출력
- `data/chunks/joyful_science_chunks_mapped.jsonl`
  - 각 청크에 `text_en_anchor`, `book_number`, `unit_number` (보정), 매핑 메타데이터 추가

## 만들 파일

### Stage 4 Part 1 (오늘)
- `ml/data_pipeline/anchors/__init__.py`
- `ml/data_pipeline/anchors/gutenberg_parser.py` — 영어 원전 파싱
- 임베딩 모델 다운로드 + 셋업 검증

### Stage 4 Part 2 (내일)
- `ml/data_pipeline/alignment/__init__.py`
- `ml/data_pipeline/alignment/embedder.py` — 임베딩 래퍼
- `ml/data_pipeline/alignment/mapper.py` — 매핑 알고리즘
- `ml/data_pipeline/schema.py` 수정 — 매핑 메타데이터 필드 추가
- `ml/scripts/04_map_anchor.py` — CLI

---

## 영어 원전 구조 (이미 분석 완료)

```
Section                                     | 청크 수 | 번호
--------------------------------------------|---------|-------
PREFACE TO THE SECOND EDITION               |    4    | 1~4
JEST, RUSE AND REVENGE: A PRELUDE IN RHYME  |   63    | 1~63
BOOK FIRST                                  |   56    | 1~56
BOOK SECOND                                 |   51    | 57~107
BOOK THIRD                                  |  168    | 108~275
BOOK FOURTH: SANCTUS JANUARIUS              |   67    | 276~342
BOOK FIFTH: WE FEARLESS ONES                |   40    | 343~382
APPENDIX: SONGS OF PRINCE FREE-AS-A-BIRD    |   ?     | 별도 (Phase 2로 미룸)
--------------------------------------------|---------|-------
본편 합계                                    |  382    | 1~382
```

**중요**:
- 본편은 **383이 아니라 382개**
- 한국어 PDF의 "appendix_body"는 사실 **PRELUDE (Jest, Ruse and Revenge)**
- 진짜 APPENDIX (Songs of Prince Free-as-a-Bird)는 한국어 PDF에 없을 가능성. Phase 2로 미룸.

### 섹션 매핑 (한국어 ↔ 영어)

| 한국어 (Stage 2 role) | 영어 (Gutenberg) |
|---|---|
| `preface` | PREFACE TO THE SECOND EDITION (1~4) |
| `appendix_body` | JEST, RUSE AND REVENGE PRELUDE (1~63) |
| `main_body` | BOOK FIRST ~ FIFTH (1~382) |

이름이 헷갈림. 한국어에서 "appendix"라 부른 게 영어에선 "prelude"임. 코드에서는 우리 한국어 명명을 유지.

---

## 매핑 알고리즘

### 전략: 임베딩 + 번호 + 위치 보정

#### 단계 1: 영어 원전 파싱
```
parse_gutenberg(english_txt) → list[EnglishUnit]
  - section: "preface" / "prelude" / "main_body"
  - unit_number: 1~4 (preface), 1~63 (prelude), 1~382 (main)
  - book_number: 1~5 (main_body만)
  - text: 영어 본문
```

#### 단계 2: 섹션별 매핑

**서문 (preface):** 
- 한국어 서문 청크 ↔ 영어 PREFACE 매칭
- 둘 다 번호 명확 (1~4) → **번호로 직접 매칭**
- 한국어가 3개, 영어가 4개면 → 임베딩으로 어느 것이 누락인지 판정

**부록 (appendix_body → 영어 prelude):**
- 한국어 청크 (59개) ↔ 영어 PRELUDE (63개) 매칭
- 둘 다 번호 명확 → **번호로 직접 매칭**
- 누락된 4개는 임베딩 + 위치로 추정

**본편 (main_body):**
- 한국어 청크 (319개) ↔ 영어 BOOK 1~5 (382개) 매칭
- 가장 까다로움
- 알고리즘:
  ```
  1. detected_number 있는 한국어 청크 → 영어 번호로 직접 매칭
     (총 152개, 47.6%, 신뢰도 1.0)
  
  2. detected_number 없는 한국어 청크 → 임베딩 매칭
     a) multilingual-e5-large로 한국어 + 영어 청크 임베딩
     b) 한국어 청크별로 영어 후보 풀에서 코사인 유사도 Top-3
     c) 가장 가까운 것 선택, 유사도 점수 기록
     d) 위치 기반 보정: 앞뒤 매칭 결과의 중간 범위 내인지 검증
  
  3. 후처리:
     - 한 영어가 두 한국어에 매칭 → Type B 합치기 후보
     - 영어 번호 누락 (한국어가 가리키지 않음) → Type A 분리 후보
     - 신뢰도 < 0.5 → 플래깅
  ```

#### 단계 3: 청크 메타데이터 채움
- `text_en_anchor` ← 매칭된 영어 텍스트
- `book_number` ← BOOK_RANGES 사용 (서문/부록은 None)
- `unit_number` ← 보정된 진짜 번호
- 매핑 메타데이터 (신뢰도, 매핑 방법)

---

## Schema 변경

`Chunk` 클래스에 매핑 메타데이터 필드 추가:

```python
class Chunk(BaseModel):
    ...  # 기존 필드들
    
    # Stage 4 매핑 메타데이터
    mapping_method: str | None = Field(
        default=None,
        description="매핑 방법: 'number' / 'embedding' / 'position' / 'manual'"
    )
    mapping_confidence: float | None = Field(
        default=None,
        description="매핑 신뢰도 0~1 (number=1.0, embedding=cosine sim)"
    )
    mapping_flags: list[str] = Field(
        default_factory=list,
        description="매핑 이슈 플래그: 'low_confidence', 'merge_candidate', 'split_candidate'"
    )
```

---

## 임베딩 모델

**선택**: `intfloat/multilingual-e5-large`

이유:
- 100개 언어, 한국어 학습 데이터 충분
- BEIR 벤치마크 다국어 1위급
- HuggingFace 무료
- 562MB
- RTX 4090에서 빠르게 동작

**주의: 입력 prefix 필요**:
- 검색 query: `"query: 한국어 텍스트"`
- 검색 대상: `"passage: English text"`

### 설치
```bash
poetry add sentence-transformers
```

### 사용 예시
```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("intfloat/multilingual-e5-large")

ko_text = "사랑은 모든 것을 허락한다"
en_text = "Love permits everything"

ko_emb = model.encode([f"query: {ko_text}"])
en_emb = model.encode([f"passage: {en_text}"])

# 코사인 유사도
from sentence_transformers import util
sim = util.cos_sim(ko_emb, en_emb)
```

---

## 다음 스테이지가 사용하는 것

**Stage 5 (LLM 정제)** 가 chunks_mapped.jsonl을 입력으로 받음:

- `text_en_anchor`: LLM에게 영어 원전을 보여주며 한국어 정제 요청
- `mapping_confidence`: 신뢰도 낮은 청크는 정제 시 추가 검증
- `mapping_flags`: merge/split 후보는 정제 전에 처리

---

## 성공 기준

- ✅ 영어 원전 449개 청크 정확하게 파싱 (preface 4 + prelude 63 + main 382)
- ✅ 본편 한국어 청크 매핑률 95%+ (319 중 ~300+)
- ✅ 명시적 번호 있는 청크 100% 매칭
- ✅ 임베딩 매칭 신뢰도 평균 > 0.7
- ✅ Type A (under) 후보 발견 시 플래깅
- ✅ Type B (over) 후보 발견 시 병합 정보 저장
- ✅ 모든 청크에 `mapping_method`, `mapping_confidence` 채워짐

## 검증 방법

```bash
poetry run python scripts/04_map_anchor.py \
    --chunks data/chunks/joyful_science_chunks_raw.jsonl \
    --english data/raw/joyful_science_english.txt \
    --output data/chunks/joyful_science_chunks_mapped.jsonl
```

검증 항목:
1. 매핑 방법 분포 (number / embedding / position)
2. 신뢰도 분포 (히스토그램)
3. 본편 청크별 매칭된 영어 번호 분포
4. 누락된 영어 번호 (Type A 후보)
5. 중복 매칭 (Type B 후보)
6. 신뢰도 낮은 매칭 샘플 검토

---

## 위험 / 주의사항

### 1. 짧은 청크의 임베딩 약함
- 한 줄짜리 잠언은 의미 신호가 약함
- 대응: 위치 정보 + 임베딩 결합

### 2. OCR 노이즈
- "기장" (가장의 OCR 오류) 같은 단어가 임베딩 품질 저하
- 대응: 핵심 명사가 살아있으면 OK. Stage 5에서 정제됨.

### 3. 번역 차이
- 한국어 = 독일어 원전 직역
- 영어 = Thomas Common 1910 (영문 의역)
- 직접 비교는 차이 큼, 임베딩이 의역도 잡아냄

### 4. 영어 PRELUDE 63개 vs 한국어 부록 59개
- 4개 차이. 한국어가 일부 시를 통합했거나 누락
- 임베딩 + 위치로 매칭

### 5. APPENDIX (Songs of Prince Free-as-a-Bird) 미처리
- 영어 원전 마지막에 있음
- 한국어 PDF에 없을 가능성 (Stage 2에서 unknown 0개였음)
- Phase 2로 미룸

## 진행 상태

### Part 1 (오늘)
- [x] 카드 작성
- [ ] anchors/gutenberg_parser.py 작성
- [ ] 영어 원전 파싱 검증 (449개 청크)
- [ ] sentence-transformers 설치
- [ ] multilingual-e5-large 다운로드
- [ ] 임베딩 셋업 검증 (간단 매칭 테스트)
- [ ] commit

### Part 2 (내일)
- [ ] schema.py 수정 (매핑 메타데이터 필드)
- [ ] alignment/embedder.py 작성
- [ ] alignment/mapper.py 작성
- [ ] 04_map_anchor.py 작성
- [ ] 매핑 실행 + 검증
- [ ] commit
