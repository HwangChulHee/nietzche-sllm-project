# Track 1 Architecture — 파일 카탈로그

이 문서는 `ml/data_pipeline/`의 모든 파일이 **무엇을 하는지**, **왜 존재하는지**, **다른 파일과 어떻게 연결되는지**를 기록한다.

새 파일을 만들거나 기존 파일을 크게 수정할 때마다 이 문서를 갱신할 것.

---

## 🗺️ 전체 그림

```
PDF → 페이지 → 섹션 → 청크 → 매핑된 청크 → 정제된 청크 → 검증된 청크 → SFT 샘플 → 파인튜닝 모델
       Stage1   Stage2   Stage3   Stage4         Stage5         Stage6        Stage7    파인튜닝
```

각 스테이지는 **이전 스테이지의 출력 파일을 입력으로 받아 다음 스테이지의 입력 파일을 출력**한다.

---

## 📁 디렉토리 구조

```
ml/data_pipeline/
├── schema.py              ← 모든 모듈이 공유하는 데이터 모델
├── extraction/            ← Stage 1
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
├── 01_extract.py          ← Stage 1 실행
├── 02_segment.py          ← Stage 2 실행
└── (03~07은 추후 작성)
```

---

## 📄 파일별 역할 카탈로그

### 공통

#### `schema.py`
- **역할**: 파이프라인 전체에서 사용하는 Pydantic 데이터 모델
- **핵심 타입**:
  - `TextBlock`: PDF에서 추출한 단일 텍스트 블록 (bbox + text + is_noise)
  - `ExtractedPage`: 페이지 단위 추출 결과 (blocks 리스트 + clean_text + role)
  - `PageRole`: 페이지 역할 타입 (preface, main_body, appendix_body 등 7종)
  - `SectionMap`: 책 전체의 섹션 구조 (page_roles + sections)
  - `Chunk`: 아포리즘 단위 청크 (Stage 3 이후 사용)
  - `SectionType`: 청크 섹션 타입 (preface, appendix_poem, aphorism)
- **누가 사용**: 모든 모듈
- **수정 빈도**: 새 스테이지마다 조금씩 (필드 추가)

---

### Stage 1: Extraction (PDF → 페이지)

**목적**: PDF 파일에서 텍스트 블록을 추출하고 노이즈(줄번호, 페이지번호)를 제거한다.

#### `extraction/pdf_extractor.py`
- **역할**: pymupdf로 PDF의 텍스트 블록을 좌표와 함께 추출
- **입력**: PDF 파일 경로
- **출력**: `list[ExtractedPage]`
- **핵심 클래스**: `PDFExtractor`
- **다음 단계로의 연결**: noise_filter가 이 결과를 받아 노이즈 마킹

#### `extraction/noise_filter.py`
- **역할**: 좌표 기반으로 줄번호/페이지번호 블록을 식별해 `is_noise=True`로 마킹
- **입력**: `ExtractedPage` (PDFExtractor 출력)
- **출력**: `is_noise`가 마킹되고 `clean_text`가 생성된 `ExtractedPage`
- **핵심 함수**: `filter_page()`, `filter_pages()`
- **핵심 로직**:
  - 줄번호: `width < 15px AND x0 < page_width * 0.15`
  - 페이지번호: `y0 > page_height * 0.88 AND width < 100px`
- **다음 단계로의 연결**: 01_extract.py가 이 결과를 JSONL로 저장

#### `scripts/01_extract.py`
- **역할**: Stage 1 CLI 실행 스크립트
- **명령**: `python scripts/01_extract.py --pdf <path> --output <path>`
- **입력**: PDF 파일
- **출력**: `data/extracted/{book_slug}_pages.jsonl` (각 라인 = ExtractedPage JSON)
- **다음 단계로의 연결**: 02_segment.py가 이 JSONL을 입력으로 받음

---

### Stage 2: Segmentation - Section Detection (페이지 → 섹션)

**목적**: 각 페이지에 섹션 역할(서문/본편/부록/속표지)을 부여한다.

#### `books/joyful_science.py`
- **역할**: 즐거운 학문 전용 상수와 마커 정의
- **포함 내용**:
  - `BOOK_SLUG`, `BOOK_TITLE_KO` 등 식별 정보
  - `PREFACE_START_MARKER`, `EMERSON_COVER_MARKER` 등 섹션 감지 마커 5종
  - `BOOK_RANGES`: 본편 1~5권의 아포리즘 번호 범위
  - `APPENDIX_POEM_COUNT`: 부록 시 개수 (63)
- **누가 사용**: section_detector.py, (이후) aphorism_segmenter.py
- **Phase 2 계획**: 다른 저서가 추가되면 같은 패턴으로 `beyond_good_evil.py` 등 작성

#### `segmentation/section_detector.py`
- **역할**: 마커 기반 상태 기계로 페이지별 섹션 역할 분류
- **입력**: `list[ExtractedPage]` (Stage 1 출력)
- **출력**: `(role이 채워진 list[ExtractedPage], SectionMap)`
- **핵심 함수**: `detect_sections()`
- **핵심 로직**: SEEKING_PREFACE → IN_PREFACE → SEEKING_APPENDIX → IN_APPENDIX → IN_MAIN_BODY 상태 전환
- **다음 단계로의 연결**: 02_segment.py가 결과를 두 파일로 저장

#### `scripts/02_segment.py`
- **역할**: Stage 2 CLI 실행 스크립트
- **명령**: `python scripts/02_segment.py --pages <jsonl> --output <json>`
- **입력**: Stage 1의 pages.jsonl
- **출력**:
  - `sections.json` (SectionMap)
  - `pages_annotated.jsonl` (role이 추가된 페이지들)
- **다음 단계로의 연결**: 03_segment_chunks.py(추후)가 두 파일을 모두 입력으로 받음

---

### Stage 3: Segmentation - Chunk Splitting (섹션 → 청크) [미작성]

**목적**: 각 페이지를 아포리즘 단위 청크로 쪼갠다.

#### `segmentation/aphorism_segmenter.py` (예정)
- **역할**: 섹션별로 다른 분할 전략 적용
- **입력**: pages_annotated.jsonl + sections.json
- **출력**: `list[Chunk]`
- **분할 전략**:
  - 서문: "1.", "2.", "3.", "4." 절 단위
  - 부록 시: 시 번호별 (번호가 별도 블록으로 분리됨)
  - 본편: 아포리즘 번호별 (번호가 본문 첫 줄과 같이 있음)

#### `scripts/03_segment_chunks.py` (예정)
- **출력**: `data/chunks/{book_slug}_chunks_raw.jsonl`

---

### Stage 4: Anchor Mapping [미작성]

**목적**: 한국어 청크를 영어 Gutenberg 원전과 매핑한다.

#### `anchors/gutenberg_parser.py` (예정)
- **역할**: 영어 Gutenberg txt 파일에서 383개 아포리즘 인덱스 생성

#### `alignment/mapper.py` (예정)
- **역할**: 한국어 청크의 unit_number를 영어 인덱스와 매칭, `text_en_anchor` 채움

#### `scripts/04_map_anchor.py` (예정)
- **출력**: `data/chunks/{book_slug}_chunks_mapped.jsonl`

---

### Stage 5: LLM Refinement [미작성]

**목적**: LLM(Gemma 4)으로 OCR 노이즈 제거 + 문체 복원.

#### `refinement/llm_client.py` (예정)
- **역할**: vLLM/Ollama 서버 호출 클라이언트 (OpenAI 호환 API)

#### `refinement/prompts.py` (예정)
- **역할**: 정제 프롬프트 템플릿 (영어 원전 + 한국어 raw → 정제된 한국어)

#### `refinement/refiner.py` (예정)
- **역할**: 배치 처리 + 체크포인트 저장 + 재시도

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
PDF (data/raw/즐거운학문-일부.pdf)
  ↓ scripts/01_extract.py
data/extracted/joyful_science_sample_pages.jsonl  ✅ 존재
  ↓ scripts/02_segment.py
data/extracted/joyful_science_sample_sections.json  ⏳ 진행중
data/extracted/joyful_science_sample_pages_annotated.jsonl  ⏳ 진행중
  ↓ scripts/03_segment_chunks.py (미작성)
data/chunks/joyful_science_sample_chunks_raw.jsonl
  ↓ scripts/04_map_anchor.py (미작성)
data/chunks/joyful_science_sample_chunks_mapped.jsonl
  ↓ scripts/05_refine.py (미작성)
data/chunks/joyful_science_sample_chunks_refined.jsonl
  ↓ scripts/06_validate.py (미작성)
data/chunks/joyful_science_sample_chunks_validated.jsonl
  ↓ scripts/07_format_sft.py (미작성)
data/sft/joyful_science_sample_sft.jsonl
  ↓ 파인튜닝
파인튜닝된 Gemma 4 모델
```

---

## 📌 설계 원칙 (잊지 말 것)

1. **단계별 독립 실행**: 각 스테이지는 JSONL/JSON으로 입출력. 한 스테이지가 망가져도 그 스테이지만 재실행 가능.
2. **저서별 어댑터 분리**: 책별 차이는 `books/` 폴더에. 공통 로직은 `data_pipeline/`의 다른 모듈에.
3. **schema는 점진적 확장**: 한 번에 모든 필드를 만들지 않고, 스테이지마다 필요한 필드 추가.
4. **JSONL 우선**: 디버깅/수동 검토가 쉬워야 함. 바이너리 포맷 금지.
5. **LLM 사용 최소화 (단, 필요한 곳은 사용)**: Stage 5, 6, 7은 LLM 사용. Stage 1~4는 LLM 없이.

---

## 📝 갱신 기록

- **2026-04-07**: 초안 작성, Stage 1 완료, Stage 2 진행 중
- **2026-04-08**: Stage 2 완료. PageRole, SectionMap, ExtractedPage.role 추가. books/joyful_science.py 신설.

---

## 🎯 새 작업 시작 시 체크리스트

1. 이 문서의 "디렉토리 구조" 섹션에서 현재 작업할 파일 위치 확인
2. "데이터 흐름" 섹션에서 입력/출력 파일 확인
3. 작업 시작 전 해당 스테이지의 카드(`docs/stage_cards/`)를 작성
4. 작업 끝나면 이 문서의 해당 섹션 업데이트
