"""
추출된 TextBlock들을 노이즈와 본문으로 분류하는 필터.

노이즈 유형:
1. 좌측 줄번호 (5, 10, 15, 20 등): 매우 좁은 폭 + 페이지 왼쪽 가장자리
2. 하단 페이지 번호 ("즐거운 학문 23", "24 니체전집 12"): 페이지 하단 + 좁은 폭

본 필터는 블록 단위로 is_noise 플래그를 설정할 뿐, 실제로 제거하지는 않는다.
이를 통해 디버깅이나 수동 검토가 필요할 때 원본을 보존할 수 있다.
"""

from rich.console import Console

from data_pipeline.schema import ExtractedPage, TextBlock

console = Console()


# =====================
# 튜닝 가능한 상수
# =====================

# 줄번호: 폭 임계값 (이보다 좁은 블록은 줄번호 후보)
LINE_NUMBER_MAX_WIDTH = 15.0

# 줄번호: 페이지 왼쪽 영역 비율 (이보다 왼쪽에 있어야 줄번호)
LINE_NUMBER_LEFT_RATIO = 0.15

# 페이지 번호: 페이지 하단 영역 비율 (이보다 아래에 있어야 페이지 번호)
PAGE_NUMBER_BOTTOM_RATIO = 0.88

# 페이지 번호: 최대 폭 (본문이 오판되지 않도록 안전장치)
PAGE_NUMBER_MAX_WIDTH = 100.0


# =====================
# 필터 함수
# =====================


def _is_line_number(block: TextBlock, page_width: float) -> bool:
    """좌측 세로 줄번호 블록인지 판정."""
    x0, _, x1, _ = block.bbox
    block_width = x1 - x0

    if block_width >= LINE_NUMBER_MAX_WIDTH:
        return False

    if x0 >= page_width * LINE_NUMBER_LEFT_RATIO:
        return False

    return True


def _is_page_number(block: TextBlock, page_height: float) -> bool:
    """하단 페이지 번호 블록인지 판정."""
    x0, y0, x1, _ = block.bbox
    block_width = x1 - x0

    if y0 <= page_height * PAGE_NUMBER_BOTTOM_RATIO:
        return False

    if block_width >= PAGE_NUMBER_MAX_WIDTH:
        return False

    return True


def classify_block(block: TextBlock, page_width: float, page_height: float) -> TextBlock:
    """단일 블록을 분류해 is_noise와 noise_reason을 설정한 새 블록을 반환."""
    if _is_line_number(block, page_width):
        return block.model_copy(
            update={"is_noise": True, "noise_reason": "line_number"}
        )

    if _is_page_number(block, page_height):
        return block.model_copy(
            update={"is_noise": True, "noise_reason": "page_number"}
        )

    return block


def filter_page(page: ExtractedPage) -> ExtractedPage:
    """페이지 내 모든 블록에 노이즈 플래그를 붙이고, clean_text를 생성한다."""
    classified_blocks = [
        classify_block(block, page.page_width, page.page_height)
        for block in page.blocks
    ]

    # 본문 블록만 이어붙여서 clean_text 생성
    clean_text = "\n".join(
        block.text for block in classified_blocks if not block.is_noise
    )

    return page.model_copy(
        update={
            "blocks": classified_blocks,
            "clean_text": clean_text,
        }
    )


def filter_pages(pages: list[ExtractedPage]) -> list[ExtractedPage]:
    """여러 페이지를 일괄 필터링한다."""
    filtered = [filter_page(page) for page in pages]

    # 간단한 통계
    total_blocks = sum(len(p.blocks) for p in filtered)
    noise_blocks = sum(
        1 for p in filtered for b in p.blocks if b.is_noise
    )
    console.log(
        f"[cyan]Filter applied:[/cyan] {noise_blocks}/{total_blocks} blocks "
        f"marked as noise ({noise_blocks / total_blocks * 100:.1f}%)"
    )

    return filtered