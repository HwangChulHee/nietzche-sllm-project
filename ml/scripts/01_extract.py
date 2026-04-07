"""
Stage 1: PDF → 추출된 페이지 JSONL

Usage:
    poetry run python scripts/01_extract.py \
        --pdf data/raw/즐거운학문-일부.pdf \
        --output data/extracted/joyful_science_sample_pages.jsonl

출력 포맷:
    각 라인이 하나의 ExtractedPage (JSON).
    블록별 bbox, is_noise 플래그, clean_text가 모두 포함된다.
"""

import argparse
from pathlib import Path

from rich.console import Console
from rich.table import Table

from data_pipeline.extraction.noise_filter import filter_pages
from data_pipeline.extraction.pdf_extractor import PDFExtractor

console = Console()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage 1: Extract PDF to JSONL")
    parser.add_argument(
        "--pdf",
        type=Path,
        required=True,
        help="입력 PDF 파일 경로",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="출력 JSONL 파일 경로",
    )
    return parser.parse_args()


def print_summary(pages) -> None:
    """추출 결과 요약 테이블 출력."""
    table = Table(title="Extraction Summary")
    table.add_column("Page", justify="right", style="cyan")
    table.add_column("Total Blocks", justify="right")
    table.add_column("Content", justify="right", style="green")
    table.add_column("Noise", justify="right", style="red")
    table.add_column("Clean Text Preview", style="dim")

    for page in pages:
        noise = sum(1 for b in page.blocks if b.is_noise)
        content = len(page.blocks) - noise
        preview = page.clean_text.replace("\n", " ")[:40]
        if len(page.clean_text) > 40:
            preview += "..."
        table.add_row(
            str(page.page_num),
            str(len(page.blocks)),
            str(content),
            str(noise),
            preview,
        )

    console.print(table)


def main() -> None:
    args = parse_args()

    if not args.pdf.exists():
        console.print(f"[red]Error:[/red] PDF not found: {args.pdf}")
        raise SystemExit(1)

    # 출력 디렉토리 준비
    args.output.parent.mkdir(parents=True, exist_ok=True)

    # 추출 + 필터링
    with PDFExtractor(args.pdf) as extractor:
        raw_pages = extractor.extract_all()

    filtered_pages = filter_pages(raw_pages)

    # JSONL 저장
    with args.output.open("w", encoding="utf-8") as f:
        for page in filtered_pages:
            f.write(page.model_dump_json() + "\n")

    console.print(
        f"\n[green]✓ Saved[/green] {len(filtered_pages)} pages to {args.output}"
    )

    # 요약 출력
    print_summary(filtered_pages)

    # 전체 통계
    total_blocks = sum(len(p.blocks) for p in filtered_pages)
    total_noise = sum(
        1 for p in filtered_pages for b in p.blocks if b.is_noise
    )
    total_content = total_blocks - total_noise
    total_clean_chars = sum(len(p.clean_text) for p in filtered_pages)

    console.print()
    console.print(f"[bold]Total pages:[/bold] {len(filtered_pages)}")
    console.print(f"[bold]Total blocks:[/bold] {total_blocks}")
    console.print(f"[bold green]Content blocks:[/bold green] {total_content}")
    console.print(f"[bold red]Noise blocks:[/bold red] {total_noise}")
    console.print(f"[bold]Clean text chars:[/bold] {total_clean_chars:,}")


if __name__ == "__main__":
    main()