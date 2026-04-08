"""
Stage 0: 전처리 (페이지 추출)

원본 합본 PDF에서 한 저서의 페이지 범위만 추출해 별도 PDF 파일로 저장.
OCR + 구조화는 외부 도구(Marker)가 담당하므로 이 스크립트는 페이지
추출만 수행한다.

Usage:
    poetry run python scripts/00_preprocess.py \\
        --source data/raw/즐거운학문-원본.pdf \\
        --book joyful_science

또는 페이지 범위를 직접 지정:
    poetry run python scripts/00_preprocess.py \\
        --source data/raw/원본.pdf \\
        --output data/raw/extracted.pdf \\
        --start 19 --end 379

다음 단계 (Marker로 OCR + 구조화):
    marker_single data/raw/joyful_science_extracted.pdf \\
        --output_dir data/marker_output \\
        --output_format json
"""

import argparse
import importlib
from pathlib import Path

from rich.console import Console

from data_pipeline.preprocessing.page_extractor import extract_page_range

console = Console()


# 책별 어댑터 매핑
# Phase 1엔 즐거운 학문만. Phase 2에서 다른 저서 추가 시 여기 등록.
BOOK_ADAPTERS = {
    "joyful_science": "data_pipeline.books.joyful_science",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Stage 0: Page extraction from source PDF",
    )
    parser.add_argument(
        "--source",
        type=Path,
        required=True,
        help="원본 PDF 파일 경로 (합본/스캔본)",
    )
    parser.add_argument(
        "--book",
        type=str,
        default=None,
        choices=list(BOOK_ADAPTERS.keys()),
        help="책 어댑터 이름 (예: joyful_science). 지정하면 페이지 범위와 출력 경로 자동 결정",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="출력 PDF 경로 (--book 안 쓸 때만 필요)",
    )
    parser.add_argument(
        "--start",
        type=int,
        default=None,
        help="시작 페이지 번호 1-indexed (--book 안 쓸 때만 필요)",
    )
    parser.add_argument(
        "--end",
        type=int,
        default=None,
        help="끝 페이지 번호 1-indexed (--book 안 쓸 때만 필요)",
    )
    return parser.parse_args()


def resolve_book_settings(book_slug: str) -> tuple[int, int, str]:
    """책 어댑터에서 페이지 범위와 BOOK_SLUG를 가져온다."""
    module_path = BOOK_ADAPTERS[book_slug]
    book = importlib.import_module(module_path)
    start, end = book.SOURCE_PAGE_RANGE
    return start, end, book.BOOK_SLUG


def main() -> None:
    args = parse_args()

    if not args.source.exists():
        console.print(f"[red]Error:[/red] Source PDF not found: {args.source}")
        raise SystemExit(1)

    # 페이지 범위와 출력 경로 결정
    if args.book:
        start_page, end_page, book_slug = resolve_book_settings(args.book)
        output_path = Path(f"data/raw/{book_slug}_extracted.pdf")
        console.log(
            f"[cyan]Book adapter:[/cyan] {book_slug} "
            f"(pages {start_page}~{end_page})"
        )
    else:
        if args.start is None or args.end is None or args.output is None:
            console.print(
                "[red]Error:[/red] --book 을 안 쓸 때는 --start, --end, --output 모두 필요"
            )
            raise SystemExit(1)
        start_page = args.start
        end_page = args.end
        output_path = args.output

    console.print()
    console.print("[bold]Stage 0: Page extraction[/bold]")
    console.print(f"  Source: {args.source}")
    console.print(f"  Output: {output_path}")
    console.print()

    extract_page_range(
        src_path=args.source,
        dst_path=output_path,
        start_page=start_page,
        end_page=end_page,
        indexing="1-indexed",
    )

    console.print()
    console.print("[bold green]✓ Stage 0 complete[/bold green]")
    console.print()
    console.print("[dim]Next step (Marker로 OCR + 구조화):[/dim]")
    console.print(
        f"  [cyan]marker_single {output_path} \\[/cyan]"
    )
    console.print(
        f"  [cyan]    --output_dir data/marker_output \\[/cyan]"
    )
    console.print(
        f"  [cyan]    --output_format json[/cyan]"
    )


if __name__ == "__main__":
    main()
