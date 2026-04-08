"""
데이터 파이프라인 전체에서 사용하는 Pydantic 스키마 정의.

Stage별 주요 데이터 모델:
- Stage 1 (Extraction): TextBlock, ExtractedPage
- Stage 2 (Section Detection): PageRole, SectionMap
- Stage 3 (Segmentation): Chunk (예비 분할)
- Stage 4 (Anchor Mapping): Chunk (블록 단위 정렬)
"""

from typing import Literal

from pydantic import BaseModel, Field


# =====================
# Stage 1: Extraction
# =====================


class TextBlock(BaseModel):
    """텍스트 블록 (Marker 또는 pymupdf에서 추출)."""

    page_num: int = Field(..., description="0-indexed 페이지 번호")
    block_num: int = Field(..., description="페이지 내 블록 순서")
    bbox: tuple[float, float, float, float] = Field(
        ..., description="블록 경계 좌표 (x0, y0, x1, y1)"
    )
    text: str = Field(..., description="블록 안의 원본 텍스트")
    block_type: str | None = Field(
        default=None,
        description=(
            "Marker가 분류한 블록 타입. "
            "'Text' | 'SectionHeader' | 'PageHeader' | 'PageFooter' | "
            "'ListItem' | 'TextInlineMath' | etc. "
            "pymupdf 추출 시에는 None."
        ),
    )
    is_noise: bool = Field(
        default=False,
        description="노이즈 필터링에서 제외 대상으로 마킹되었는지",
    )
    noise_reason: str | None = Field(
        default=None,
        description="노이즈로 판정된 이유 (디버깅용)",
    )


# =====================
# Stage 2: Section Detection
# =====================


PageRole = Literal[
    "preface",
    "emerson_cover",
    "german_cover",
    "appendix_cover",
    "appendix_body",
    "main_body",
    "unknown",
]


class ExtractedPage(BaseModel):
    """페이지 단위 추출 결과."""

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
    """책 전체의 섹션 구조."""

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

    Stage별 필드 채움:
    - Stage 3 (Segmentation): 예비 분할
        id, book_slug, section_type, unit_number(선택), text_ko_raw,
        source_pages, split_signal, detected_number
    - Stage 4 (Anchor Mapping): 블록 단위 정렬로 청크 재구성
        text_en_anchor, book_number, unit_number(보정),
        mapping_method, mapping_confidence, mapping_flags
    - Stage 5 (LLM Refinement): text_ko, refined=True
    - Stage 6 (Validation): validated=True
    """

    # -------- 식별 --------
    id: str = Field(..., description="청크 고유 ID")
    book_slug: str = Field(..., description="저서 식별자")

    # -------- 구조 --------
    section_type: SectionType = Field(..., description="청크가 속한 섹션 유형")
    book_number: int | None = Field(
        default=None,
        description="본편의 Book 번호 (1~5). 서문/부록은 None.",
    )
    unit_number: int | None = Field(
        default=None,
        description="섹션 내부의 순서 번호",
    )
    unit_title: str | None = Field(
        default=None,
        description="아포리즘 제목 (있는 경우)",
    )

    # -------- 텍스트 --------
    text_ko_raw: str = Field(
        default="",
        description="정제 전 한국어 원본",
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

    # -------- Stage 3: 분할 메타데이터 --------
    split_signal: str | None = Field(
        default=None,
        description=(
            "분할 신호. 'section_header' | 'number_block' | "
            "'title_pattern' | 'first_chunk' | 'sentence_aligned'"
        ),
    )
    detected_number: int | None = Field(
        default=None,
        description="Stage 3에서 명시적으로 인식된 아포리즘 번호",
    )

    # -------- Stage 4: 매핑 메타데이터 --------
    mapping_method: str | None = Field(
        default=None,
        description=(
            "매핑 방법. 'number'(번호 직접) | "
            "'sentence_aligned'(문장 단위 정렬) | 'unmapped'"
        ),
    )
    mapping_confidence: float | None = Field(
        default=None,
        description="매핑 신뢰도 0.0~1.0",
    )
    mapping_flags: list[str] = Field(
        default_factory=list,
        description=(
            "매핑 이슈 플래그. 'low_confidence' | 'absorbed_short' | "
            "'no_english_section'"
        ),
    )

    # -------- 처리 상태 --------
    refined: bool = Field(default=False, description="Stage 5 정제 완료 여부")
    validated: bool = Field(default=False, description="Stage 6 검증 완료 여부")
