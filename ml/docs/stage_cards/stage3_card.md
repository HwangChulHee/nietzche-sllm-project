# Stage 3 카드: 청크 분할 (아포리즘 단위)

## 한 줄 요약
페이지를 아포리즘/절/시 단위 청크로 분할한다.

## 위치
**전체 파이프라인에서**: 5/8 단계 (Stage 0/Marker/1/2 완료 → **Stage 3** → Stage 4~7 → 파인튜닝)
**데이터 단위 변화**: 페이지 (361개) → 청크 (약 450개 예상)

## 입력
- `data/extracted/joyful_science_marker_pages_annotated.jsonl` (Stage 2 출력)
  - 361개 페이지, 각 페이지에 role 포함
- `data/extracted/joyful_science_marker_sections.json` (Stage 2 출력)
  - SectionMap (섹션별 페이지 묶음)

## 출력
- `data/chunks/joyful_science_chunks_raw.jsonl`
  - Chunk 객체 리스트, 각 청크는 unit_number, text_ko_raw, source_pages, split_signal, detected_number 포함

## 만들 파일
- `ml/data_pipeline/schema.py` (수정) — Chunk에 `split_signal`, `detected_number` 필드 추가
- `ml/data_pipeline/segmentation/aphorism_segmenter.py` (신규) — 섹션별 분할 로직
- `ml/scripts/03_segment_chunks.py` (신규) — CLI 실행

---

## 🎯 분할 철학 (가장 중요)

Stage 3 분할은 **불완전할 수밖에 없다**. Marker가 본편 아포리즘 번호를 일관되게 인식 못 하기 때문. 우리의 전략은 **Stage 4 영어 Anchor 매핑에서 보정하기 쉬운 형태로 분할**하는 것.

### 잘못된 분할의 두 종류

**Type A: Under-segmentation (합쳐짐)**
- 두 개 이상의 아포리즘이 하나의 청크로 합쳐짐
- 예: 본편 1번과 2번이 한 청크
- 발생 원인: 분할 신호 놓침 (특히 본편 1번처럼 번호 없는 케이스)
- **Stage 4 보정 난이도**: 🟡 어려움 — "분리 위치"를 찾아야 함

**Type B: Over-segmentation (쪼개짐)**
- 한 아포리즘이 여러 청크로 쪼개짐
- 발생 원인: 분할 신호 오인식
- **Stage 4 보정 난이도**: 🟢 쉬움 — 두 청크가 같은 영어 아포리즘에 매칭되면 병합

### 핵심 원칙: **Type B를 선호하고 Type A를 피한다**

→ Stage 3는 **약간 공격적인 분할**을 한다:
- 신뢰할 수 있는 신호는 모두 사용
- 결과 청크 수가 383개보다 약간 많거나 비슷할 가능성 (이상적: 380~400)
- Stage 4에서 영어 Anchor로 검증 후 병합/분리/번호 부여

---

## 핵심 알고리즘: 섹션별 분할 전략

### 1. 서문 분할 (Page 0~9)

**구조**: 4개 절 (1, 2, 3, 4)

**분할 신호**: 짧은 숫자 블록 `^\d+\.$` (예: "1.", "2.", "3.", "4.")

**Marker 출력 패턴 (실제 데이터)**:
```
Page 0:
  [Text] 5            ← 줄번호 (noise)
  [Text] 1.           ← 절 번호 (분할 신호)
  [Text] 아마도 이 책은...  ← 본문
```

**알고리즘**:
```
current_section = None
current_text = []
current_first_page = None

for page in preface_pages (0~9):
    for block in page.content_blocks:  # noise 제외
        match = re.match(r"^(\d+)\.$", block.text.strip())
        if match:
            # 새 절 시작
            if current_section is not None:
                yield Chunk(
                    section_type="preface",
                    unit_number=current_section,
                    text_ko_raw="\n".join(current_text),
                    source_pages=[...],
                    split_signal="number_block",
                    detected_number=current_section,
                )
            current_section = int(match.group(1))
            current_text = []
            current_first_page = page.page_num
        else:
            current_text.append(block.text)

# 마지막 절
if current_section is not None:
    yield Chunk(...)
```

**예상 결과**: 4개 청크 (서문 1~4절)

---

### 2. 부록 시 분할 (Page 13~37)

**구조**: 63개 시 (1~63)

**분할 신호**: 짧은 숫자 블록 `^\d+\.$`

**알고리즘**: 서문과 동일. section_type만 `"appendix_poem"`으로.

**예상 결과**: 60~63개 청크

---

### 3. 본편 분할 (Page 38~360) [가장 까다로움]

**구조**: 383개 아포리즘 (1~383)

**문제점**: Marker가 아포리즘 번호를 일관되게 인식 못 함
- Page 38: 1번, 번호 없음 ("존재의 목적을 가르치는 교사.—...")
- Page 42: 2번, 번호 있음 ("[Text] 2." + "[Text] 지적 양심.—...")
- Page 44: 3번, 번호 없음 ("고귀와 비속.—...")
- Page 49: 7번, SectionHeader로 잡힘 ("7.")

**분할 신호 (3중 휴리스틱, 우선순위 순)**:

#### 신호 1: 명시적 번호 블록
- 패턴: `^(\d+)\.$` 짧은 Text 블록
- 길이: `len(text.strip()) <= 5`
- 예: `"2."`, `"127."`
- → `split_signal="number_block"`, `detected_number=2`

#### 신호 2: SectionHeader 블록
- block_type이 `SectionHeader`
- 텍스트가 짧음 (제목 또는 번호)
- → `split_signal="section_header"`, `detected_number=parse if number`

#### 신호 3: 제목.— 패턴
- 정규식: `^([^—\n.]{1,40})\.\s*[—–-]\s+`
- 짧은 제목 (40자 이하) + 마침표 + 줄표 + 공백
- 예: `"지적 양심. —"`, `"고귀와 비속.—"`, `"존재의 목적을 가르치는 교사.—"`
- → `split_signal="title_pattern"`, `detected_number=None`

**Type A 방지를 위해 신호 3 (제목 패턴)이 핵심.** 번호가 없는 본편 1번, 3번을 잡아냄.

**Type B 방지를 위해**:
- 신호 1의 길이 조건 (5자 이하)
- 신호 3의 제목 길이 조건 (40자 이하)

**알고리즘**:
```python
current_chunk_text = []
current_first_page = None
current_signal = None
current_number = None

def is_split_signal(block):
    """블록이 분할 신호인지 판단. (signal_type, detected_number) 반환."""
    text = block.text.strip()
    
    # 신호 1: 명시적 번호 블록
    if len(text) <= 5:
        m = re.match(r"^(\d+)\.$", text)
        if m:
            return ("number_block", int(m.group(1)))
    
    # 신호 2: SectionHeader (block_type 정보 필요)
    # → block에서 별도 메타데이터 필요. 아래 참고.
    
    # 신호 3: 제목.— 패턴
    m = re.match(r"^([^—\n.]{1,40})\.\s*[—–-]\s+", text)
    if m:
        return ("title_pattern", None)
    
    return (None, None)

for page in main_body_pages:
    for block in page.content_blocks:
        signal_type, detected_num = is_split_signal(block)
        
        if signal_type:
            # 새 아포리즘 시작
            if current_chunk_text:
                yield Chunk(
                    section_type="aphorism",
                    unit_number=current_number,  # 명시적 번호 있으면 사용, 없으면 None
                    text_ko_raw="\n".join(current_chunk_text),
                    source_pages=[...],
                    split_signal=current_signal,
                    detected_number=current_number,
                )
            
            # 새 청크 초기화
            current_chunk_text = []
            current_signal = signal_type
            current_number = detected_num
            current_first_page = page.page_num
            
            # 번호 블록은 본문 아니므로 스킵
            # 제목 패턴은 본문 일부이므로 포함
            if signal_type != "number_block":
                current_chunk_text.append(block.text)
        else:
            # 현재 청크에 추가
            current_chunk_text.append(block.text)
            if current_first_page is None:
                current_first_page = page.page_num

# 마지막 청크
if current_chunk_text:
    yield Chunk(...)
```

**SectionHeader 처리**:
- Marker JSON에서 SectionHeader 블록은 우리 어댑터에서 일반 Text로 흡수됨
- 어댑터를 수정해서 `block_type` 정보를 TextBlock에 보존해야 함
- **결정**: 일단 신호 1 + 신호 3만 사용. SectionHeader는 Phase 2에서 추가.

**예상 결과**: 약 380~420개 청크 (이상은 383개)
- 신호 잡힘: 90% 이상 (신호 3 덕분)
- 약간의 over-segmentation 허용 → Stage 4에서 병합

---

## Chunk 객체 필드 채우기

| 필드 | Stage 3에서 채움 | 값 |
|---|---|---|
| `id` | ✅ | `joyful_science_preface_1`, `joyful_science_appendix_1`, `joyful_science_aph_1` |
| `book_slug` | ✅ | `"joyful_science"` |
| `section_type` | ✅ | `"preface"` / `"appendix_poem"` / `"aphorism"` |
| `book_number` | ❌ | Stage 4에서 BOOK_RANGES 보고 결정 |
| `unit_number` | 🟡 | 서문/부록은 채움. 본편은 명시적 번호 있을 때만 채움 (없으면 None) |
| `unit_title` | ❌ | Stage 5/7에서 추출 |
| `text_ko_raw` | ✅ | 청크 본문 |
| `text_ko` | ❌ | Stage 5에서 |
| `text_en_anchor` | ❌ | Stage 4에서 |
| `char_count_ko` | ✅ | `len(text_ko_raw)` |
| `source_pages` | ✅ | 청크가 걸친 페이지 번호들 |
| `split_signal` | ✅ | `"number_block"` / `"title_pattern"` / `"section_header"` / `"first_chunk"` |
| `detected_number` | 🟡 | 명시적으로 인식된 번호 (있을 때만) |
| `refined` | - | False (기본값) |
| `validated` | - | False (기본값) |

### Schema 변경 필요

```python
# schema.py의 Chunk 클래스에 추가
class Chunk(BaseModel):
    ...  # 기존 필드들
    
    split_signal: str | None = Field(
        default=None,
        description="이 청크를 시작시킨 분할 신호의 종류",
    )
    detected_number: int | None = Field(
        default=None,
        description="명시적으로 인식된 아포리즘 번호 (number_block 신호일 때만)",
    )
```

---

## 다음 스테이지가 사용하는 것

**Stage 4 (Anchor 매핑)** 가 chunks_raw.jsonl을 입력으로 받음:

### Stage 4가 활용하는 메타데이터
- **`detected_number`**: 신뢰도 높은 anchor 포인트 (직접 매핑 가능)
- **`split_signal`**: 분할의 신뢰도 추정 (number_block > section_header > title_pattern)
- **`source_pages`**: 페이지 위치 정보 (페이지 순서 보존 확인)

### Stage 4의 책임
1. **본편 청크에 `unit_number` 매핑** (영어 Gutenberg 1~383번과 매칭)
2. **잘못 분할된 청크 보정**:
   - 두 한국어 청크가 같은 영어 아포리즘에 매칭 → 병합
   - 한 한국어 청크가 두 영어 아포리즘에 매칭 → 분리 시도 (어려우면 플래깅)
3. **`text_en_anchor` 채움**
4. **`book_number` 채움** (BOOK_RANGES 사용)

---

## 성공 기준

- ✅ 서문: 정확히 4개 청크
- ✅ 부록: 60~63개 청크
- 🟡 본편: 380~420개 청크 (이상은 383개, 약간의 over-segmentation 허용)
- ✅ 모든 청크에 `text_ko_raw`, `source_pages`, `split_signal` 채워짐
- ✅ 명시적 번호 있는 청크의 `detected_number` 채워짐
- ✅ unknown 페이지 (Stage 2의 unknown role)는 청크 생성 안 함

## 검증 방법

```bash
poetry run python scripts/03_segment_chunks.py \
    --pages data/extracted/joyful_science_marker_pages_annotated.jsonl \
    --sections data/extracted/joyful_science_marker_sections.json \
    --output data/chunks/joyful_science_chunks_raw.jsonl
```

검증 항목:
1. **청크 총 개수**: 서문 4 + 부록 ~63 + 본편 380~420 = 약 450
2. **첫 청크 (서문 1절)** 텍스트 확인
3. **본편 첫 청크 (1번 아포리즘)** 텍스트 확인
4. **split_signal 분포**: number_block / title_pattern 비율
5. **detected_number 통계**: 본편 청크 중 몇 %가 명시적 번호 가졌는지
6. **청크 길이 분포**: 너무 짧거나 너무 긴 청크 확인 (이상치 발견)
7. **source_pages 연속성** 확인

---

## 위험 / 주의사항

### 1. 본편 분할 부정확성 (수용 가능)
- Marker가 번호를 일관되게 인식 못 함
- 제목.— 패턴이 본문 중간에 등장할 수도 있음
- → **Stage 4 영어 Anchor로 보정** (split_signal 정보 활용)

### 2. 페이지 경계 처리
- 한 아포리즘이 여러 페이지에 걸치는 경우 자연스럽게 처리 (새 신호 만나기 전까지 누적)

### 3. 짧은 분할 신호의 오인식
- "1." 같은 짧은 블록이 본문 안에 등장할 가능성 (예: 인용문 안)
- → **블록의 길이 조건** (`len(text) <= 5`)으로 1차 필터링
- 위험하면 Stage 4에서 detected_number와 영어 Anchor 매칭으로 검증

### 4. 줄번호와의 혼동
- "5", "10", "15", "20" 같은 줄번호는 noise_filter에서 이미 마킹됨
- content_blocks만 사용하므로 영향 없음

### 5. unit_number 부재 (본편)
- 명시적 번호 없는 청크는 unit_number=None
- Stage 4에서 영어 Anchor 매칭 후 채움
- ID는 임시로 순서대로 부여 (`joyful_science_aph_1`, `joyful_science_aph_2`, ...)

---

## 진행 상태

- [x] 설계 합의
- [x] 분할 철학 확정 (Over > Under)
- [x] schema에 split_signal, detected_number 추가 결정
- [ ] schema.py 수정
- [ ] aphorism_segmenter.py 작성
- [ ] 03_segment_chunks.py 작성
- [ ] 서문 + 부록 검증
- [ ] 본편 검증
- [ ] split_signal 분포 확인
- [ ] 청크 길이 분포 확인
- [ ] 카드 진행 상태 업데이트
