# Stage 2 카드: 섹션 감지

## 한 줄 요약
페이지에 섹션 역할을 부여한다 (서문/본편/부록/속표지 분류).

## 위치
**전체 파이프라인에서**: 2/7 단계 (Stage 1 완료 → **Stage 2** → Stage 3~7 → 파인튜닝)
**데이터 단위 변화**: 페이지 → 페이지 + 역할 라벨

## 입력
- `data/extracted/joyful_science_sample_pages.jsonl` (Stage 1 출력)
  - 44개 페이지, 각 페이지에 blocks와 clean_text 포함

## 출력
- `data/extracted/joyful_science_sample_sections.json`
  - SectionMap 객체 (book_slug, page_roles, sections)
- `data/extracted/joyful_science_sample_pages_annotated.jsonl`
  - 44개 페이지 (각 페이지에 role 필드 추가됨)

## 만들 파일
- `ml/data_pipeline/schema.py` (수정) — PageRole 타입, SectionMap 클래스, ExtractedPage.role 필드 추가
- `ml/data_pipeline/books/joyful_science.py` (신규) — 책별 마커와 상수
- `ml/data_pipeline/segmentation/section_detector.py` (신규) — 상태 기계
- `ml/scripts/02_segment.py` (신규) — CLI 실행

## 핵심 알고리즘: 상태 기계

```
SEEKING_PREFACE
  ↓ "제2판 서문" 마커 발견
IN_PREFACE
  ↓ "시인과 현자" (에머슨) 마커 발견
SEEKING_APPENDIX
  ↓ "농담, 간계 그리고 복수" 마커 발견
IN_APPENDIX
  ↓ "존재의 목적을 가르치는 교사" 마커 발견
IN_MAIN_BODY
```

## 페이지 역할 (PageRole)
| 역할 | 의미 | Stage 3에서 |
|---|---|---|
| `preface` | 서문 본문 | 절 단위 분할 |
| `emerson_cover` | 에머슨 인용 속표지 | 스킵 |
| `german_cover` | 독일어 원전 속표지 | 스킵 |
| `appendix_cover` | 부록 시 속표지 | 스킵 |
| `appendix_body` | 부록 시 본문 | 시 번호별 분할 |
| `main_body` | 본편 본문 | 아포리즘 번호별 분할 |
| `unknown` | 미분류 | 디버깅 필요 |

## 다음 스테이지가 사용하는 것
**Stage 3 (청크 분할)**가 두 출력 파일을 모두 입력으로 받는다:
- `pages_annotated.jsonl`: 각 페이지의 role을 보고 어떤 분할 전략을 쓸지 결정
- `sections.json`: 섹션별 페이지 묶음 정보로 빠르게 조회

## 성공 기준
- ✅ 44페이지가 모두 분류됨 (unknown 0개)
- ✅ 페이지 0~9: preface
- ✅ 페이지 10: emerson_cover
- ✅ 페이지 11: german_cover
- ✅ 페이지 12: appendix_cover
- ✅ 페이지 13~37: appendix_body
- ✅ 페이지 38~43: main_body

## 검증 방법
```bash
poetry run python scripts/02_segment.py \
    --pages data/extracted/joyful_science_sample_pages.jsonl \
    --output data/extracted/joyful_science_sample_sections.json
```
출력 테이블 + 상태 전환 로그 확인

## 위험 / 주의사항
- **마커가 본문에 우연히 등장**: 본편의 어떤 아포리즘에 "제2판 서문"이라는 단어가 등장하면 오작동 가능. 상태 기계로 방지하지만 추가 검증 필요.
- **전체 PDF에서는 다를 수 있음**: 일부 PDF에는 본편이 6페이지뿐이라 검증이 충분하지 않음. 전체 PDF에서 다시 검증해야 함 (Day 2 후반).
- **Page 9 (서명 페이지)**: "제노바 부근의 루타에서 1886년 가을" 페이지. 별도 role로 분리 안 함, preface에 포함.

## 진행 상태
- [x] 설계 합의 완료
- [x] schema.py 수정
- [x] books/joyful_science.py 작성
- [x] section_detector.py 작성
- [x] 02_segment.py 작성
- [x] 일부 PDF에서 검증
- [ ] 전체 PDF에서 검증 (Day 2 후반)
