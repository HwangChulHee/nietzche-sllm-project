"""
Stage 0a: 원본 PDF에서 특정 페이지 범위만 추출.

니체전집 같은 합본 PDF에서 한 저서(예: 즐거운 학문)의 본문이
차지하는 페이지 범위만 잘라내 새 PDF 파일로 저장한다.
"""

from pathlib import Path

import fitz  # pymupdf
from rich.console import Console

console = Console()


def extract_page_range(
    src_path: str | Path,
    dst_path: str | Path,
    start_page: int,
    end_page: int,
    indexing: str = "1-indexed",
) -> int:
    """원본 PDF에서 페이지 범위를 추출해 새 PDF로 저장.

    Args:
        src_path: 원본 PDF 경로
        dst_path: 출력 PDF 경로
        start_page: 시작 페이지 번호 (양 끝 포함)
        end_page: 끝 페이지 번호 (양 끝 포함)
        indexing: "1-indexed" (사람이 보는 페이지 번호) 또는 "0-indexed"

    Returns:
        추출된 페이지 수

    Raises:
        FileNotFoundError: 원본 PDF가 없을 때
        ValueError: 페이지 범위가 잘못됐을 때
    """
    src_path = Path(src_path)
    dst_path = Path(dst_path)

    if not src_path.exists():
        raise FileNotFoundError(f"Source PDF not found: {src_path}")

    if start_page > end_page:
        raise ValueError(
            f"start_page ({start_page}) must be <= end_page ({end_page})"
        )

    # 1-indexed → 0-indexed 변환
    if indexing == "1-indexed":
        from_page = start_page - 1
        to_page = end_page - 1
    elif indexing == "0-indexed":
        from_page = start_page
        to_page = end_page
    else:
        raise ValueError(f"Unknown indexing: {indexing}")

    src = fitz.open(src_path)
    total = src.page_count
    console.log(
        f"[cyan]Source:[/cyan] {src_path.name} ({total} pages)"
    )

    # 범위 검증
    if from_page < 0 or to_page >= total:
        src.close()
        raise ValueError(
            f"Page range ({start_page}, {end_page}) [{indexing}] "
            f"out of bounds for PDF with {total} pages"
        )

    # 출력 디렉토리 준비
    dst_path.parent.mkdir(parents=True, exist_ok=True)

    # 새 PDF 생성 + 페이지 복사
    dst = fitz.open()
    dst.insert_pdf(src, from_page=from_page, to_page=to_page)

    extracted_count = dst.page_count
    dst.save(dst_path)
    dst.close()
    src.close()

    console.log(
        f"[green]Extracted[/green] pages {start_page}~{end_page} "
        f"({extracted_count} pages) → {dst_path}"
    )

    return extracted_count
