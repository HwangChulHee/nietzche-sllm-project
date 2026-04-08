# Track 1 Architecture — 파일 카탈로그

이 문서는 `ml/data_pipeline/`의 모든 파일이 **무엇을 하는지**, **왜 존재하는지**, **다른 파일과 어떻게 연결되는지**를 기록한다.

새 파일을 만들거나 기존 파일을 크게 수정할 때마다 이 문서를 갱신할 것.

---

## 🗺️ 전체 그림

```
원본 PDF → 페이지 추출 → Marker OCR → ExtractedPage → 섹션 → 청크 → 매핑된 청크 → 정제된 청크 → 검증된 청크 → SFT 샘플 → 파인튜닝 모델
            Stage0      외부도구    Stage1         Stage2  Stage3  Stage4         Stage5         Stage6        Stage7    파인튜닝
```

각 스테이지는 **이전 스테이지의 출력 파일을 입력으로 받아 다음 스테이지의 입력 파일을 출력**한다.

---

## 📁 디렉토리 구조

```
ml/data_pipeline/
├── schema.py              ← 모든 모듈이 공유하는 데이터 모델
├── preprocessing/         ← Stage 0
│   ├── page_extractor.py
│   └── marker_adapter.py
├── extraction/            ← Stage 1 (PDF 모드 — legacy)
│   ├── pdf_extractor.py
│   └── noise_filter.py
├── segmentation/          ← Stage 2 + 3
│   ├── section_detector.py
│   └── aphorism_segmenter.py    (Stage 3에서 작성)
├── books/                 ← 저서별 어댑터
│   └── joyful_science.py
├── anchors/               ← Stage 4
│   └── gutenberg_parser.py      (Stage 4에서 작성)
├── alignment/             ← Stage 4
│   └── mapper.py                (Stage 4에서 작성)
├── refinement/            ← Stage 5
│   ├── llm_client.py            (Stage 5에서 작성)
│   ├── prompts.py               (Stage 5에서 작성)
│   └── refiner.py               (Stage 5에서 작성)
├── validation/            ← Stage 6
│   └── validators.py            (Stage 6에서 작성)
└── output/                ← Stage 7
    └── sft_formatter.py         (Stage 7에서 작성)

ml/scripts/
├── 00_preprocess.py       ← Stage 0 실행 (페이지 추출)
├── 01_extract.py          ← Stage 1 실행 (Marker JSON or PDF)
├── 02_segment.py          ← Stage 2 실행
└── (03~07은 추후 작성)
```

---

## 📄 파일별 역할 카탈로그

### 공통

#### `schema.py`
- **역할**: 파이프라인 전체에서 사용하는 Pydantic 데이터 모델
- **핵심 타입**:
  - `TextBlock`: 텍스트 블록 (bbox + text + is_noise)
  - `ExtractedPage`: 페이지 단위 추출 결과
  - `PageRole`: 페이지 역할 타입 (preface, main_body 등 7종)
  - `SectionMap`: 책 전체 섹션 구조
  - `Chunk`: 아포리즘 단위 청크 (Stage 3 이후)
  - `SectionType`: 청크 섹션 타입
- **누가 사용**: 모든 모듈
- **수정 빈도**: 새 스테이지마다 조금씩 (필드 추가)

---

### Stage 0: Preprocessing (원본 PDF → 추출된 PDF)

**목적**: 합본 PDF에서 한 저서의 페이지 범위만 추출.

#### `preprocessing/page_extractor.py`
- **역할**: pymupdf로 PDF의 특정 페이지 범위를 새 PDF로 복사
- **입력**: 원본 PDF 경로, start/end 페이지
- **출력**: 새 PDF 파일
- **핵심 함수**: `extract_page_range()`
- **인덱싱**: 1-indexed (사람이 보는 PDF 뷰어 기준)
- **다음 단계로의 연결**: 외부 도구 Marker가 이 PDF를 입력으로 받음

#### `scripts/00_preprocess.py`
- **역할**: Stage 0 CLI 실행
- **명령**: `python scripts/00_preprocess.py --source <pdf> --book joyful_science`
- **입력**: 원본 PDF
- **출력**: `data/raw/{book_slug}_extracted.pdf`
- **다음 단계**: Marker CLI를 사용자가 직접 호출

---

### Marker (외부 도구, 우리 코드 아님)

**목적**: PDF → JSON (Surya OCR + 레이아웃 분석)

- **명령**:
  ```bash
  marker_single data/raw/{book_slug}_extracted.pdf \
      --output_dir data/marker_output \
      --output_format json
  ```
- **출력**: `data/marker_output/{book_slug}_extracted/{book_slug}_extracted.json`
- **블록 타입**: Document → Page → Text/SectionHeader/PageHeader/PageFooter
- **속도**: 페이지당 ~1.2초 (RTX 4090 기준)

---

### Stage 1: Extraction (Marker JSON or PDF → ExtractedPage)

**목적**: Marker JSON을 우리 파이프라인 표준 형식인 ExtractedPage로 변환.

#### `preprocessing/marker_adapter.py`
- **역할**: Marker JSON → `list[ExtractedPage]` 변환
- **입력**: Marker가 출력한 JSON 파일
- **출력**: `list[ExtractedPage]`
- **핵심 함수**: `marker_json_to_pages()`, `load_marker_json()`
- **블록 타입 매핑**:
  - `Text`, `SectionHeader`, `ListItem` → 콘텐츠
  - `PageHeader`, `PageFooter` → 자동 노이즈
  - 빈 텍스트 → 노이즈
- **다음 단계로의 연결**: 01_extract.py가 호출

#### `extraction/pdf_extractor.py` (legacy)
- **역할**: pymupdf로 PDF 블록 추출 (Marker 사용 전 방식)
- **현재 상태**: legacy. Marker 모드를 기본으로 사용.
- **유지 이유**: PDF 모드 fallback (Marker 안 쓰는 케이스)

#### `extraction/noise_filter.py`
- **역할**: 좌표 기반 노이즈 필터 (줄번호, 페이지번호 제거)
- **입력**: `ExtractedPage`
- **출력**: `is_noise` 마킹된 `ExtractedPage`
- **핵심 로직**:
  - 줄번호: `width < 15px AND x0 < page_width * 0.15`
  - 페이지번호: `y0 > page_height * 0.88 AND width < 100px`
- **사용 위치**: 두 모드 (PDF/Marker) 모두에서 적용

#### `scripts/01_extract.py`
- **역할**: Stage 1 CLI 실행 (두 가지 모드 지원)
- **명령 (Marker 모드, 권장)**:
  ```bash
  python scripts/01_extract.py \
      --marker-json data/marker_output/.../joyful_science_extracted.json \
      --output data/extracted/joyful_science_pages.jsonl
  ```
- **명령 (PDF 모드, legacy)**:
  ```bash
  python scripts/01_extract.py \
      --pdf data/raw/{file}.pdf \
      --output data/extracted/{file}_pages.jsonl
  ```
- **출력**: `data/extracted/{book_slug}_pages.jsonl`
- **다음 단계**: 02_segment.py가 이 JSONL 입력

---

### Stage 2: Segmentation - Section Detection

**목적**: 각 페이지에 섹션 역할(서문/본편/부록/속표지)을 부여.

#### `books/joyful_science.py`
- **역할**: 즐거운 학문 전용 상수와 마커 정의
- **포함**:
  - `BOOK_SLUG`, `BOOK_TITLE_KO` 등 식별 정보
  - `SOURCE_PAGE_RANGE = (19, 379)` — Stage 0용 페이지 범위
  - 4개 섹션 마커: `EMERSON_COVER_MARKER`, `GERMAN_COVER_MARKER`, `APPENDIX_COVER_MARKER`, `MAIN_BODY_START_MARKER`
  - `BOOK_RANGES` — 본편 1~5권 아포리즘 번호 범위
  - `APPENDIX_POEM_COUNT` — 부록 시 개수
- **누가 사용**: 00_preprocess.py, section_detector.py, (이후) aphorism_segmenter.py
- **참고**: `PREFACE_START_MARKER`는 사용 안 함 (추출된 PDF가 이미 본문부터 시작)

#### `segmentation/section_detector.py`
- **역할**: 마커 기반 상태 기계로 페이지별 섹션 역할 분류
- **입력**: `list[ExtractedPage]`
- **출력**: `(role 채워진 list[ExtractedPage], SectionMap)`
- **핵심 함수**: `detect_sections()`
- **상태 흐름**: `IN_PREFACE` (시작) → `SEEKING_APPENDIX` → `IN_APPENDIX` → `IN_MAIN_BODY`
- **다음 단계로의 연결**: 02_segment.py가 결과를 두 파일로 저장

#### `scripts/02_segment.py`
- **역할**: Stage 2 CLI 실행
- **명령**: `python scripts/02_segment.py --pages <jsonl> --output <json>`
- **출력**:
  - `sections.json` (SectionMap)
  - `pages_annotated.jsonl` (role 추가된 페이지들)
- **다음 단계**: 03_segment_chunks.py가 두 파일 모두 입력

---

### Stage 3: Segmentation - Chunk Splitting [작업 중]

**목적**: 각 페이지를 아포리즘 단위 청크로 쪼갠다.

#### `segmentation/aphorism_segmenter.py` (예정)
- **역할**: 섹션별로 다른 분할 전략 적용
- **입력**: pages_annotated.jsonl + sections.json
- **출력**: `list[Chunk]`
- **분할 전략**:
  - 서문: 절 단위 (1, 2, 3, 4)
  - 부록 시: 시 번호별
  - 본편: 아포리즘 번호별

#### `scripts/03_segment_chunks.py` (예정)
- **출력**: `data/chunks/{book_slug}_chunks_raw.jsonl`

---

### Stage 4: Anchor Mapping [미작성]

**목적**: 한국어 청크와 영어 Gutenberg 원전 매핑.

#### `anchors/gutenberg_parser.py` (예정)
- **역할**: 영어 Gutenberg txt에서 383개 아포리즘 인덱스 생성

#### `alignment/mapper.py` (예정)
- **역할**: 한국어 청크 unit_number와 영어 인덱스 매칭

#### `scripts/04_map_anchor.py` (예정)
- **출력**: `data/chunks/{book_slug}_chunks_mapped.jsonl`

---

### Stage 5: LLM Refinement [미작성]

**목적**: LLM(Gemma 4)으로 OCR 노이즈 제거 + 문체 복원.

#### `refinement/llm_client.py` (예정)
- **역할**: vLLM 서버 호출 클라이언트 (OpenAI 호환 API)

#### `refinement/prompts.py` (예정)
- **역할**: 정제 프롬프트 템플릿

#### `refinement/refiner.py` (예정)
- **역할**: 배치 처리 + 체크포인트 + 재시도

#### `scripts/05_refine.py` (예정)
- **출력**: `data/chunks/{book_slug}_chunks_refined.jsonl`

---

### Stage 6: Validation [미작성]

**목적**: 정제 품질 검증 (자동 + LLM + 수동).

#### `validation/validators.py` (예정)
- **역할**: 길이 비율, 키워드 보존, LLM-as-Judge 검증

#### `scripts/06_validate.py` (예정)
- **출력**: `data/chunks/{book_slug}_chunks_validated.jsonl`

---

### Stage 7: SFT Format [미작성]

**목적**: 검증된 청크를 SFT 학습 데이터셋으로 변환.

#### `output/sft_formatter.py` (예정)
- **역할**:
  - Pass 1: 청크 응답에 어울리는 사용자 질문 LLM 생성
  - Pass 2: 응답을 자연스러운 상담 형식으로 다듬기
  - 최종 messages 배열 형식으로 변환

#### `scripts/07_format_sft.py` (예정)
- **출력**: `data/sft/{book_slug}_sft.jsonl`

---

## 🔗 데이터 흐름 (파일 단위)

```
원본 PDF (data/raw/즐거운학문-원본.pdf, 744p)
  ↓ scripts/00_preprocess.py
data/raw/joyful_science_extracted.pdf  (361p)  ✅ 존재
  ↓ marker_single (외부 도구)
data/marker_output/joyful_science_extracted/joyful_science_extracted.json  ✅ 존재
  ↓ scripts/01_extract.py --marker-json
data/extracted/joyful_science_marker_pages.jsonl  ✅ 존재
  ↓ scripts/02_segment.py
data/extracted/joyful_science_marker_sections.json  ✅ 존재
data/extracted/joyful_science_marker_pages_annotated.jsonl  ✅ 존재
  ↓ scripts/03_segment_chunks.py (작업중)
data/chunks/joyful_science_chunks_raw.jsonl
  ↓ scripts/04_map_anchor.py (미작성)
data/chunks/joyful_science_chunks_mapped.jsonl
  ↓ scripts/05_refine.py (미작성)
data/chunks/joyful_science_chunks_refined.jsonl
  ↓ scripts/06_validate.py (미작성)
data/chunks/joyful_science_chunks_validated.jsonl
  ↓ scripts/07_format_sft.py (미작성)
data/sft/joyful_science_sft.jsonl
  ↓ 파인튜닝
파인튜닝된 Gemma 4 모델
```

---

## 📌 설계 원칙 (잊지 말 것)

1. **단계별 독립 실행**: 각 스테이지는 JSONL/JSON 입출력. 망가지면 그 스테이지만 재실행.
2. **저서별 어댑터 분리**: 책별 차이는 `books/`. 공통 로직은 `data_pipeline/`.
3. **schema는 점진적 확장**: 필요한 필드를 스테이지마다 추가.
4. **JSONL 우선**: 디버깅/수동 검토 쉬워야 함.
5. **Marker 외부 도구로 활용**: PDF → JSON 변환은 Marker(Surya 모델). 우리는 변환 결과만 어댑터로 흡수.

---

## 📝 갱신 기록

- **2026-04-07**: 초안 작성, Stage 1 완료
- **2026-04-08 오전**: Stage 2 완료 (일부 PDF 검증). PageRole, SectionMap 추가. books/joyful_science.py 신설.
- **2026-04-08 오후**: Marker 통합. Stage 0/1/2 재구성:
  - Stage 0: ocrmypdf 제거, 페이지 추출 전용으로 단순화
  - Marker (외부 도구) 추가
  - Stage 1: marker_adapter.py 신설, 두 모드(PDF/Marker JSON) 지원
  - Stage 2: PREFACE_START_MARKER 제거, 시작 상태를 IN_PREFACE로 변경
  - 전체 PDF (361p) 검증 완료: preface 10, appendix_body 25, main_body 323

---

## 🎯 새 작업 시작 시 체크리스트

1. 이 문서의 "디렉토리 구조"에서 작업할 파일 위치 확인
2. "데이터 흐름"에서 입력/출력 파일 확인
3. 작업 시작 전 해당 스테이지의 카드(`docs/stage_cards/`) 작성
4. 작업 끝나면 이 문서 해당 섹션 + 갱신 기록 업데이트
