"""
데이터 파이프라인 전체에서 사용하는 Pydantic 스키마 정의.

Stage별 주요 데이터 모델:
- Stage 1 (Extraction): TextBlock, ExtractedPage
- Stage 2 (Section Detection): PageRole, SectionMap (+ ExtractedPage.role)
- Stage 3 이후 (Segmentation ~ Output): Chunk
"""

from typing import Literal

from pydantic import BaseModel, Field


# =====================
# Stage 1: Extraction
# =====================


class TextBlock(BaseModel):
    """텍스트 블록 (pymupdf 또는 Marker에서 추출).

    bbox 좌표를 사용해 좌측 줄번호나 하단 페이지번호 같은
    노이즈 블록을 필터링할 수 있다.
    """

    page_num: int = Field(..., description="0-indexed 페이지 번호")
    block_num: int = Field(..., description="페이지 내 블록 순서")
    bbox: tuple[float, float, float, float] = Field(
        ..., description="블록 경계 좌표 (x0, y0, x1, y1)"
    )
    text: str = Field(..., description="블록 안의 원본 텍스트")
    is_noise: bool = Field(
        default=False,
        description="노이즈 필터링에서 제외 대상으로 마킹되었는지 여부",
    )
    noise_reason: str | None = Field(
        default=None,
        description="노이즈로 판정된 이유 (디버깅용)",
    )


# =====================
# Stage 2: Section Detection
# =====================


PageRole = Literal[
    "preface",          # 서문 본문
    "emerson_cover",    # 에머슨 인용 속표지
    "german_cover",     # 독일어 원전 속표지
    "appendix_cover",   # 부록 시 속표지
    "appendix_body",    # 부록 시 본문
    "main_body",        # 본편 본문
    "unknown",          # 미분류
]


class ExtractedPage(BaseModel):
    """페이지 단위 추출 결과.

    노이즈 필터링 전/후 블록을 모두 보관하며, `clean_text`는
    노이즈가 제거된 본문 텍스트만 합쳐서 저장한다.
    `role`은 Stage 2 (section_detector)에서 채워진다.
    """

    page_num: int = Field(..., description="0-indexed 페이지 번호")
    page_width: float
    page_height: float
    blocks: list[TextBlock] = Field(default_factory=list)
    clean_text: str = Field(
        default="",
        description="노이즈 제거 후 본문 블록만 합친 텍스트",
    )
    role: PageRole | None = Field(
        default=None,
        description="Stage 2에서 부여한 페이지 역할",
    )


class SectionMap(BaseModel):
    """책 전체의 섹션 구조.

    Stage 2에서 생성되며, 각 페이지가 어떤 섹션에 속하는지와
    섹션별 페이지 묶음을 동시에 보관한다.
    """

    book_slug: str = Field(..., description="책 식별자")
    page_roles: dict[int, PageRole] = Field(
        default_factory=dict,
        description="페이지 번호 → 역할 매핑",
    )
    sections: dict[str, list[int]] = Field(
        default_factory=dict,
        description="섹션 이름 → 해당 섹션에 속한 페이지 번호 리스트",
    )


# =====================
# Stage 3 이후: Chunk
# =====================


SectionType = Literal["preface", "appendix_poem", "aphorism"]


class Chunk(BaseModel):
    """파이프라인 전 스테이지에서 공유하는 청크 단위.

    Stage 3(Segmentation)에서 처음 생성되며, 이후 스테이지를 거치면서
    필드가 점진적으로 채워진다:
    - Stage 3: id, book_slug, section_type, unit_number(선택), text_ko_raw,
               source_pages, split_signal, detected_number
    - Stage 4: text_en_anchor, book_number, unit_number(미정 시 보정)
    - Stage 5: text_ko (정제된 텍스트), refined=True
    - Stage 6: validated=True
    """

    # -------- 식별 --------
    id: str = Field(..., description="청크 고유 ID (예: 'joyful_science_aph_1')")
    book_slug: str = Field(..., description="저서 식별자 (예: 'joyful_science')")

    # -------- 구조 정보 --------
    section_type: SectionType = Field(..., description="청크가 속한 섹션 유형")
    book_number: int | None = Field(
        default=None,
        description="본편의 Book 번호 (1~5). 서문/부록은 None.",
    )
    unit_number: int | None = Field(
        default=None,
        description=(
            "섹션 내부의 순서 번호. 서문/부록은 항상 채움. "
            "본편은 명시적 번호가 인식된 경우만 채우고, 아니면 None "
            "(Stage 4에서 영어 Anchor 매칭으로 보정)."
        ),
    )
    unit_title: str | None = Field(
        default=None,
        description="아포리즘 제목 (있는 경우, Stage 5/7에서 추출)",
    )

    # -------- 텍스트 --------
    text_ko_raw: str = Field(
        default="",
        description="정제 전 한국어 원본 (Stage 3 시점)",
    )
    text_ko: str = Field(
        default="",
        description="LLM 정제 후 한국어 (Stage 5 이후)",
    )
    text_en_anchor: str = Field(
        default="",
        description="영어 Gutenberg 원전 (Stage 4 이후)",
    )

    # -------- 메타데이터 --------
    char_count_ko: int = Field(default=0, description="text_ko_raw 글자 수")
    source_pages: list[int] = Field(
        default_factory=list,
        description="이 청크를 구성한 PDF 페이지 번호들 (0-indexed)",
    )

    # -------- 분할 메타데이터 (Stage 4에서 활용) --------
    split_signal: str | None = Field(
        default=None,
        description=(
            "이 청크를 시작시킨 분할 신호의 종류. "
            "'number_block' | 'title_pattern' | 'section_header' | 'first_chunk'"
        ),
    )
    detected_number: int | None = Field(
        default=None,
        description=(
            "명시적으로 인식된 아포리즘 번호 (number_block 신호일 때만). "
            "Stage 4에서 영어 Anchor 매칭의 신뢰도 높은 anchor 포인트로 활용."
        ),
    )

    # -------- 처리 상태 --------
    refined: bool = Field(default=False, description="Stage 5 정제 완료 여부")
    validated: bool = Field(default=False, description="Stage 6 검증 완료 여부")
