"""
Stage 0c: Marker JSON → ExtractedPage 변환 어댑터.

Marker가 출력한 JSON (Document → Page → Block 트리)을
파이프라인 표준 형식인 ExtractedPage 리스트로 변환한다.

Marker의 블록 타입과 우리 파이프라인의 매핑:
- Text         → 본문 블록 (콘텐츠)
- SectionHeader → 본문 블록 (콘텐츠, 섹션 헤더 마킹)
- PageHeader    → 노이즈 (자동 제거)
- PageFooter    → 노이즈 (자동 제거)
- 빈 텍스트     → 노이즈

추가로 좌표 기반 노이즈 필터를 적용해서 줄번호 같은 것도 제거한다.
"""

import re
from pathlib import Path
from typing import Any

from rich.console import Console

from data_pipeline.extraction.noise_filter import filter_page
from data_pipeline.schema import ExtractedPage, TextBlock

console = Console()


# 콘텐츠로 취급할 Marker 블록 타입
CONTENT_BLOCK_TYPES = {
    "Text",
    "SectionHeader",
    "ListItem",
    "TextInlineMath",
}

# 무조건 노이즈로 취급할 Marker 블록 타입
NOISE_BLOCK_TYPES = {
    "PageHeader",
    "PageFooter",
    "Footnote",  # 각주는 별도 처리 필요시 추가
}


def _clean_html(html: str) -> str:
    """Marker 출력의 HTML 태그를 제거하고 텍스트만 추출.

    Marker는 텍스트를 `<p block-type="Text">...</p>` 같은
    HTML로 감싸서 반환한다. 태그를 제거하고 텍스트만 남긴다.
    각주 태그 `<sup>...</sup>` 같은 것도 제거.
    """
    if not html:
        return ""
    # HTML 엔티티 디코딩 (기본적인 것만)
    text = html
    text = text.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
    text = text.replace("&quot;", '"').replace("&#39;", "'")
    # HTML 태그 제거
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


def _extract_page_blocks(
    page_node: dict[str, Any], page_idx: int
) -> tuple[list[TextBlock], float, float]:
    """Marker의 Page 노드에서 TextBlock 리스트를 추출."""
    blocks: list[TextBlock] = []

    # 페이지 크기 (bbox에서 추출)
    page_bbox = page_node.get("bbox", [0, 0, 0, 0])
    page_width = float(page_bbox[2]) if len(page_bbox) >= 4 else 0.0
    page_height = float(page_bbox[3]) if len(page_bbox) >= 4 else 0.0

    children = page_node.get("children") or []

    for block_idx, child in enumerate(children):
        block_type = child.get("block_type", "Unknown")
        raw_text = child.get("html", "") or child.get("text", "")
        text = _clean_html(raw_text)
        bbox = child.get("bbox", [0.0, 0.0, 0.0, 0.0])

        # bbox는 [x0, y0, x1, y1] 형태여야 함
        if len(bbox) != 4:
            bbox = [0.0, 0.0, 0.0, 0.0]
        bbox_tuple = (
            float(bbox[0]),
            float(bbox[1]),
            float(bbox[2]),
            float(bbox[3]),
        )

        # 노이즈 판정
        is_noise = False
        noise_reason: str | None = None

        # 1. 명시적 노이즈 블록 타입
        if block_type in NOISE_BLOCK_TYPES:
            is_noise = True
            noise_reason = f"marker_{block_type.lower()}"

        # 2. 빈 텍스트
        elif not text:
            is_noise = True
            noise_reason = "empty_text"

        # 3. 알 수 없는 블록 타입은 일단 노이즈로
        elif block_type not in CONTENT_BLOCK_TYPES:
            is_noise = True
            noise_reason = f"unknown_type_{block_type}"

        blocks.append(
            TextBlock(
                page_num=page_idx,
                block_num=block_idx,
                bbox=bbox_tuple,
                text=text,
                is_noise=is_noise,
                noise_reason=noise_reason,
            )
        )

    return blocks, page_width, page_height


def marker_json_to_pages(
    marker_data: dict[str, Any],
    apply_coordinate_filter: bool = True,
) -> list[ExtractedPage]:
    """Marker JSON 전체를 ExtractedPage 리스트로 변환.

    Args:
        marker_data: Marker가 출력한 JSON (Document 노드 루트)
        apply_coordinate_filter: True면 좌표 기반 노이즈 필터(줄번호 등)를
            추가로 적용

    Returns:
        ExtractedPage 리스트 (페이지 순서대로)
    """
    if not isinstance(marker_data, dict):
        raise ValueError(f"Expected dict at root, got {type(marker_data)}")

    if marker_data.get("block_type") != "Document":
        console.log(
            f"[yellow]경고: 루트 block_type이 'Document'가 아님: "
            f"{marker_data.get('block_type')}[/yellow]"
        )

    page_nodes = marker_data.get("children") or []
    pages: list[ExtractedPage] = []

    for page_idx, page_node in enumerate(page_nodes):
        if page_node.get("block_type") != "Page":
            console.log(
                f"[yellow]경고: Page {page_idx}의 block_type이 'Page'가 아님: "
                f"{page_node.get('block_type')}[/yellow]"
            )
            continue

        blocks, page_width, page_height = _extract_page_blocks(
            page_node, page_idx
        )

        # clean_text 생성 (노이즈 제외)
        content_texts = [b.text for b in blocks if not b.is_noise and b.text]
        clean_text = "\n".join(content_texts)

        page = ExtractedPage(
            page_num=page_idx,
            page_width=page_width,
            page_height=page_height,
            blocks=blocks,
            clean_text=clean_text,
        )

        # 좌표 기반 추가 필터 (줄번호 등 — Marker가 못 잡은 것들)
        if apply_coordinate_filter:
            page = filter_page(page)

        pages.append(page)

    return pages


def load_marker_json(json_path: str | Path) -> dict[str, Any]:
    """Marker JSON 파일을 로드.

    Args:
        json_path: Marker가 출력한 *.json 파일 경로

    Returns:
        파싱된 Marker JSON 딕셔너리
    """
    import json

    json_path = Path(json_path)
    if not json_path.exists():
        raise FileNotFoundError(f"Marker JSON not found: {json_path}")

    with json_path.open("r", encoding="utf-8") as f:
        return json.load(f)
