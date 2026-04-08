"""
Stage 4a 검증: 영어 Gutenberg 파싱 결과 확인.

Usage:
    poetry run python scripts/04a_parse_english.py \\
        --input data/raw/joyful_science_english.txt \\
        --output data/anchors/joyful_science_english_units.jsonl
"""

import argparse
from collections import Counter
from pathlib import Path

from rich.console import Console
from rich.table import Table

from data_pipeline.anchors.gutenberg_parser import parse_gutenberg, save_units_jsonl

console = Console()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Stage 4a: Parse English Gutenberg text",
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="입력: 영어 Gutenberg .txt 파일",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="출력: 영어 청크 JSONL",
    )
    return parser.parse_args()


def print_summary(units: list) -> None:
    """파싱 결과 요약."""
    if not units:
        console.print("[red]No units parsed.[/red]")
        return

    # 섹션별 카운트
    section_counts = Counter(u.section for u in units)

    # 섹션별 테이블
    table = Table(title="English Units by Section", show_header=True)
    table.add_column("Section", style="cyan")
    table.add_column("Count", justify="right")
    table.add_column("Number range", justify="right")
    table.add_column("Avg chars", justify="right")

    for section in ("preface", "prelude", "main_body", "appendix"):
        section_units = [u for u in units if u.section == section]
        if not section_units:
            continue
        nums = [u.section_unit_number for u in section_units]
        avg = sum(u.char_count for u in section_units) / len(section_units)
        table.add_row(
            section,
            str(len(section_units)),
            f"{min(nums)}~{max(nums)}",
            f"{avg:,.0f}",
        )

    console.print()
    console.print(table)
    console.print()
    console.print(f"[bold]Total units:[/bold] {len(units)}")

    # 본편 Book별 카운트
    main_units = [u for u in units if u.section == "main_body"]
    if main_units:
        book_counts = Counter(u.book_number for u in main_units)
        console.print()
        console.print("[bold]Main Body by Book:[/bold]")
        for book_num in sorted(book_counts.keys()):
            book_units = [u for u in main_units if u.book_number == book_num]
            nums = [u.section_unit_number for u in book_units]
            console.print(
                f"  Book {book_num}: {book_counts[book_num]} units "
                f"(numbers {min(nums)}~{max(nums)})"
            )

    # 첫 청크 미리보기
    console.print()
    console.print("[bold]First unit per section:[/bold]")
    for section in ("preface", "prelude", "main_body"):
        section_units = [u for u in units if u.section == section]
        if section_units:
            first = section_units[0]
            preview = first.text[:120].replace("\n", " ")
            console.print(
                f"  [cyan]{section} #{first.section_unit_number}[/cyan]: {preview}..."
            )

    # 본편 1번 (존재의 목적을 가르치는 교사) 확인
    teachers = [
        u for u in main_units if u.section_unit_number == 1
    ]
    if teachers:
        console.print()
        console.print("[bold]Main Body #1 full text:[/bold]")
        text = teachers[0].text[:500].replace("\n", " ")
        console.print(f"  {text}...")


def main() -> None:
    args = parse_args()

    if not args.input.exists():
        console.print(f"[red]Error:[/red] Input not found: {args.input}")
        raise SystemExit(1)

    console.log(f"[cyan]Parsing:[/cyan] {args.input}")
    units = parse_gutenberg(args.input)
    save_units_jsonl(units, args.output)
    print_summary(units)


if __name__ == "__main__":
    main()
