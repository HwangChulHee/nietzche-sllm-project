# Stage 2 카드: 섹션 감지 [완료]

## 한 줄 요약
페이지에 섹션 역할을 부여한다 (서문/본편/부록/속표지 분류).

## 위치
**전체 파이프라인에서**: 4/8 단계 (Stage 0/Marker/Stage 1 완료 → **Stage 2 완료** → Stage 3~7 → 파인튜닝)
**데이터 단위 변화**: 페이지 → 페이지 + 역할 라벨

## 입력
- `data/extracted/joyful_science_marker_pages.jsonl` (Stage 1 출력)
  - 361개 페이지, 각 페이지에 blocks와 clean_text 포함

## 출력
- `data/extracted/joyful_science_marker_sections.json`
  - SectionMap 객체 (book_slug, page_roles, sections)
- `data/extracted/joyful_science_marker_pages_annotated.jsonl`
  - 361개 페이지 (각 페이지에 role 필드 추가됨)

## 만든 파일
- `ml/data_pipeline/schema.py` (수정) — PageRole 타입, SectionMap 클래스, ExtractedPage.role 필드 추가
- `ml/data_pipeline/books/joyful_science.py` (신규) — 책별 마커와 상수
- `ml/data_pipeline/segmentation/section_detector.py` (신규) — 상태 기계
- `ml/scripts/02_segment.py` (신규) — CLI 실행

## 핵심 알고리즘: 상태 기계 (단순화 버전)

```
IN_PREFACE  ← 시작 (첫 페이지부터 서문으로 가정)
   ↓ "시인과 현자" (에머슨) 마커 발견
SEEKING_APPENDIX
   ↓ "농담, 간계 그리고 복수" 마커 발견
IN_APPENDIX
   ↓ "존재의 목적을 가르치는 교사" 마커 발견
IN_MAIN_BODY
```

**참고**: 원래 `SEEKING_PREFACE → "제2판 서문" 마커 → IN_PREFACE` 단계가 있었지만,
Marker로 추출한 PDF의 첫 페이지가 곧 서문 본문 첫 페이지여서 묵시적 시작으로 단순화.

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
**Stage 3 (청크 분할)** 가 두 출력 파일을 모두 입력으로 받음:
- `pages_annotated.jsonl`: 각 페이지의 role 보고 분할 전략 결정
- `sections.json`: 섹션별 페이지 묶음 정보로 빠르게 조회

## 성공 기준
- ✅ 361페이지가 모두 분류됨 (unknown 0개)
- ✅ 페이지 0~9: preface (10페이지)
- ✅ 페이지 10: emerson_cover
- ✅ 페이지 11: german_cover
- ✅ 페이지 12: appendix_cover
- ✅ 페이지 13~37: appendix_body (25페이지)
- ✅ 페이지 38~360: main_body (323페이지)

## 검증 결과 (2026-04-08)

```
         Section Detection Summary          
┏━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Section        ┃ Page Count ┃ Page Range ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ preface        │         10 │ 0~9        │
│ appendix_body  │         25 │ 13~37      │
│ main_body      │        323 │ 38~360     │
│ emerson_cover  │          1 │ 10         │
│ german_cover   │          1 │ 11         │
│ appendix_cover │          1 │ 12         │
└────────────────┴────────────┴────────────┘
```

상태 전환: 4번 (Page 10, 11, 12, 38) — 정확히 의도대로

## 위험 / 주의사항 (해소됨)
- ~~마커가 본문에 우연히 등장~~: 전체 361페이지 검증 결과 해당 케이스 없음
- ~~"제2판 서문" 마커 미작동~~: PREFACE_START_MARKER 제거하여 해결
- ~~일부 PDF 한계 (본편 6페이지)~~: Marker 통합 후 본편 323페이지 모두 인식

## 진행 상태
- [x] 설계 합의 완료
- [x] schema.py 수정
- [x] books/joyful_science.py 작성
- [x] section_detector.py 작성
- [x] 02_segment.py 작성
- [x] 일부 PDF에서 검증
- [x] 전체 PDF에서 검증 (Marker 통합 후 361페이지)
- [x] PREFACE_START_MARKER 제거 (단순화)
