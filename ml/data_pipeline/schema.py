"""
데이터 파이프라인 전체에서 사용하는 Pydantic 스키마 정의.

Stage별 주요 데이터 모델:
- Stage 1 (Extraction): TextBlock, ExtractedPage
- Stage 3 이후 (Segmentation ~ Output): Chunk
"""

from typing import Literal

from pydantic import BaseModel, Field


# =====================
# Stage 1: Extraction
# =====================


class TextBlock(BaseModel):
    """pymupdf에서 추출한 단일 텍스트 블록.

    pymupdf의 `page.get_text("blocks")` 결과를 감싼 구조.
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


class ExtractedPage(BaseModel):
    """페이지 단위 추출 결과.

    노이즈 필터링 전/후 블록을 모두 보관하며,
    `clean_text`는 노이즈가 제거된 본문 텍스트를 합쳐서 저장한다.
    """

    page_num: int = Field(..., description="0-indexed 페이지 번호")
    page_width: float
    page_height: float
    blocks: list[TextBlock] = Field(default_factory=list)
    clean_text: str = Field(
        default="",
        description="노이즈 제거 후 본문 블록만 합친 텍스트",
    )


# =====================
# Stage 3 이후: Chunk
# =====================


SectionType = Literal["preface", "appendix_poem", "aphorism"]


class Chunk(BaseModel):
    """파이프라인 전 스테이지에서 공유하는 청크 단위.

    Stage 3(Segmentation)에서 처음 생성되며, 이후 스테이지를 거치면서
    필드가 점진적으로 채워진다:
    - Stage 3: id, book_slug, section_type, unit_number, text_ko_raw, source_pages
    - Stage 4: text_en_anchor
    - Stage 5: text_ko (정제된 텍스트), refined=True
    - Stage 6: validated=True
    """

    # -------- 식별 --------
    id: str = Field(..., description="청크 고유 ID (예: 'joyful_science_b1_125')")
    book_slug: str = Field(..., description="저서 식별자 (예: 'joyful_science')")

    # -------- 구조 정보 --------
    section_type: SectionType = Field(..., description="청크가 속한 섹션 유형")
    book_number: int | None = Field(
        default=None,
        description="본편의 Book 번호 (1~5). 서문/부록은 None.",
    )
    unit_number: int = Field(..., description="섹션 내부의 순서 번호")
    unit_title: str | None = Field(
        default=None,
        description="아포리즘 제목 (있는 경우)",
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
    char_count_ko: int = Field(default=0, description="정제된 한국어 글자 수")
    source_pages: list[int] = Field(
        default_factory=list,
        description="이 청크를 구성한 PDF 페이지 번호들 (0-indexed)",
    )

    # -------- 처리 상태 --------
    refined: bool = Field(default=False, description="Stage 5 정제 완료 여부")
    validated: bool = Field(default=False, description="Stage 6 검증 완료 여부")