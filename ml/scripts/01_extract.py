"""
Stage 1: PDF/Marker JSON → ExtractedPage JSONL

두 가지 입력 모드 지원:
1. PDF 모드 (기존): pymupdf 기반 블록 추출
   poetry run python scripts/01_extract.py \
       --pdf data/raw/something.pdf \
       --output data/extracted/something_pages.jsonl

2. Marker 모드 (신규): Marker JSON에서 변환
   poetry run python scripts/01_extract.py \
       --marker-json data/marker_output/something/something.json \
       --output data/extracted/something_pages.jsonl
"""

import argparse
from pathlib import Path

from rich.console import Console
from rich.table import Table

from data_pipeline.extraction.noise_filter import filter_pages
from data_pipeline.extraction.pdf_extractor import PDFExtractor
from data_pipeline.preprocessing.marker_adapter import (
    load_marker_json,
    marker_json_to_pages,
)
from data_pipeline.schema import ExtractedPage

console = Console()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Stage 1: Extract pages from PDF or Marker JSON",
    )
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument(
        "--pdf",
        type=Path,
        help="입력 PDF 파일 (pymupdf 기반 추출)",
    )
    src.add_argument(
        "--marker-json",
        type=Path,
        help="Marker가 출력한 JSON 파일 (Marker 어댑터 사용)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="출력 JSONL 파일 경로",
    )
    parser.add_argument(
        "--no-coordinate-filter",
        action="store_true",
        help="좌표 기반 노이즈 필터 비활성화 (Marker 모드에서만 의미 있음)",
    )
    return parser.parse_args()


def extract_from_pdf(pdf_path: Path) -> list[ExtractedPage]:
    """PDF에서 페이지 추출 (기존 로직)."""
    console.log(f"[cyan]Extracting from PDF:[/cyan] {pdf_path}")
    extractor = PDFExtractor()
    pages = extractor.extract(pdf_path)
    console.log(f"[green]Extracted[/green] {len(pages)} pages")

    console.log("Applying noise filter...")
    pages = filter_pages(pages)
    return pages


def extract_from_marker(
    json_path: Path, apply_coordinate_filter: bool = True
) -> list[ExtractedPage]:
    """Marker JSON에서 페이지 추출."""
    console.log(f"[cyan]Loading Marker JSON:[/cyan] {json_path}")
    marker_data = load_marker_json(json_path)

    console.log("Converting to ExtractedPage...")
    pages = marker_json_to_pages(
        marker_data, apply_coordinate_filter=apply_coordinate_filter
    )
    console.log(f"[green]Converted[/green] {len(pages)} pages")
    return pages


def save_pages_jsonl(pages: list[ExtractedPage], output_path: Path) -> None:
    """ExtractedPage 리스트를 JSONL로 저장."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for page in pages:
            f.write(page.model_dump_json() + "\n")
    console.log(f"[green]✓ Saved[/green] {len(pages)} pages to {output_path}")


def print_summary(pages: list[ExtractedPage]) -> None:
    """추출 결과 요약 테이블 출력."""
    total_blocks = sum(len(p.blocks) for p in pages)
    noise_blocks = sum(
        sum(1 for b in p.blocks if b.is_noise) for p in pages
    )
    content_blocks = total_blocks - noise_blocks
    total_chars = sum(len(p.clean_text) for p in pages)

    table = Table(title="Extraction Summary", show_header=True)
    table.add_column("Page", justify="right")
    table.add_column("Total Blocks", justify="right")
    table.add_column("Content", justify="right")
    table.add_column("Noise", justify="right")
    table.add_column("Clean Text Preview", overflow="fold")

    # 처음 50개 페이지만 테이블에 (너무 많으면 가독성 저하)
    display_pages = pages if len(pages) <= 50 else pages[:50]

    for page in display_pages:
        total = len(page.blocks)
        noise = sum(1 for b in page.blocks if b.is_noise)
        content = total - noise
        preview = page.clean_text[:80].replace("\n", " ")
        if len(page.clean_text) > 80:
            preview += "..."
        table.add_row(
            str(page.page_num),
            str(total),
            str(content),
            str(noise),
            preview,
        )

    console.print()
    console.print(table)
    if len(pages) > 50:
        console.print(f"[dim](Showing first 50 of {len(pages)} pages)[/dim]")
    console.print()
    console.print(f"[bold]Total pages:[/bold] {len(pages)}")
    console.print(f"[bold]Total blocks:[/bold] {total_blocks}")
    if total_blocks > 0:
        console.print(
            f"[bold]Content blocks:[/bold] {content_blocks} "
            f"({content_blocks / total_blocks * 100:.1f}%)"
        )
        console.print(
            f"[bold]Noise blocks:[/bold] {noise_blocks} "
            f"({noise_blocks / total_blocks * 100:.1f}%)"
        )
    console.print(f"[bold]Clean text chars:[/bold] {total_chars:,}")


def main() -> None:
    args = parse_args()

    if args.pdf:
        if not args.pdf.exists():
            console.print(f"[red]Error:[/red] PDF not found: {args.pdf}")
            raise SystemExit(1)
        pages = extract_from_pdf(args.pdf)
    else:
        if not args.marker_json.exists():
            console.print(
                f"[red]Error:[/red] Marker JSON not found: {args.marker_json}"
            )
            raise SystemExit(1)
        pages = extract_from_marker(
            args.marker_json,
            apply_coordinate_filter=not args.no_coordinate_filter,
        )

    save_pages_jsonl(pages, args.output)
    print_summary(pages)


if __name__ == "__main__":
    main()
