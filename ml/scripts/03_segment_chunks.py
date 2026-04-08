"""
Stage 3 CLI: 페이지 → 청크 분할

Usage:
    poetry run python scripts/03_segment_chunks.py \\
        --pages data/extracted/joyful_science_marker_pages_annotated.jsonl \\
        --sections data/extracted/joyful_science_marker_sections.json \\
        --output data/chunks/joyful_science_chunks_raw.jsonl
"""

import argparse
import json
from collections import Counter
from pathlib import Path

from rich.console import Console
from rich.table import Table

from data_pipeline.schema import Chunk, ExtractedPage, SectionMap
from data_pipeline.segmentation.aphorism_segmenter import segment_pages

console = Console()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Stage 3: Split pages into aphorism-level chunks",
    )
    parser.add_argument(
        "--pages",
        type=Path,
        required=True,
        help="입력: Stage 2가 출력한 annotated pages JSONL",
    )
    parser.add_argument(
        "--sections",
        type=Path,
        required=True,
        help="입력: Stage 2가 출력한 sections JSON",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="출력: chunks JSONL",
    )
    parser.add_argument(
        "--book-slug",
        type=str,
        default="joyful_science",
        help="책 식별자 (기본: joyful_science)",
    )
    return parser.parse_args()


def load_pages(path: Path) -> list[ExtractedPage]:
    pages: list[ExtractedPage] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            pages.append(ExtractedPage.model_validate_json(line))
    return pages


def load_section_map(path: Path) -> SectionMap:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return SectionMap.model_validate(data)


def save_chunks(chunks: list[Chunk], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(chunk.model_dump_json() + "\n")


def print_summary(chunks: list[Chunk]) -> None:
    """청크 분할 결과 요약 출력."""
    if not chunks:
        console.print("[red]No chunks generated.[/red]")
        return

    # 섹션별 카운트
    section_counts = Counter(c.section_type for c in chunks)

    # 본편 split_signal 분포
    aph_chunks = [c for c in chunks if c.section_type == "aphorism"]
    signal_counts = Counter(c.split_signal for c in aph_chunks)

    # 본편 detected_number 통계
    aph_with_number = sum(1 for c in aph_chunks if c.detected_number is not None)

    # 청크 길이 통계
    char_counts = [c.char_count_ko for c in chunks]
    avg_chars = sum(char_counts) / len(char_counts)
    min_chars = min(char_counts)
    max_chars = max(char_counts)

    # 섹션별 카운트 테이블
    section_table = Table(title="Chunks by Section", show_header=True)
    section_table.add_column("Section", style="cyan")
    section_table.add_column("Count", justify="right")
    section_table.add_column("Avg chars", justify="right")
    for section in ("preface", "appendix_poem", "aphorism"):
        section_chunks = [c for c in chunks if c.section_type == section]
        if section_chunks:
            avg = sum(c.char_count_ko for c in section_chunks) / len(section_chunks)
            section_table.add_row(
                section,
                str(len(section_chunks)),
                f"{avg:,.0f}",
            )

    console.print()
    console.print(section_table)

    # 본편 split_signal 분포
    if aph_chunks:
        signal_table = Table(title="Main Body: Split Signal Distribution", show_header=True)
        signal_table.add_column("Signal", style="cyan")
        signal_table.add_column("Count", justify="right")
        signal_table.add_column("%", justify="right")
        for signal, count in signal_counts.most_common():
            pct = count / len(aph_chunks) * 100
            signal_table.add_row(
                str(signal),
                str(count),
                f"{pct:.1f}%",
            )
        console.print()
        console.print(signal_table)

        console.print()
        console.print(
            f"[bold]Aphorisms with explicit number:[/bold] "
            f"{aph_with_number} / {len(aph_chunks)} "
            f"({aph_with_number / len(aph_chunks) * 100:.1f}%)"
        )

    # 길이 분포
    console.print()
    console.print("[bold]Chunk length:[/bold]")
    console.print(f"  min:  {min_chars:,} chars")
    console.print(f"  avg:  {avg_chars:,.0f} chars")
    console.print(f"  max:  {max_chars:,} chars")

    # 너무 짧거나 긴 청크 경고
    very_short = [c for c in chunks if c.char_count_ko < 50]
    very_long = [c for c in chunks if c.char_count_ko > 5000]
    if very_short:
        console.print(
            f"  [yellow]⚠ {len(very_short)} very short chunks (<50 chars)[/yellow]"
        )
    if very_long:
        console.print(
            f"  [yellow]⚠ {len(very_long)} very long chunks (>5000 chars)[/yellow]"
        )

    # 첫 번째 청크 미리보기 (각 섹션)
    console.print()
    console.print("[bold]First chunk per section:[/bold]")
    for section in ("preface", "appendix_poem", "aphorism"):
        section_chunks = [c for c in chunks if c.section_type == section]
        if section_chunks:
            first = section_chunks[0]
            preview = first.text_ko_raw[:100].replace("\n", " ")
            console.print(f"  [cyan]{section}[/cyan] ({first.id}): {preview}...")


def main() -> None:
    args = parse_args()

    if not args.pages.exists():
        console.print(f"[red]Error:[/red] Pages file not found: {args.pages}")
        raise SystemExit(1)
    if not args.sections.exists():
        console.print(f"[red]Error:[/red] Sections file not found: {args.sections}")
        raise SystemExit(1)

    console.log(f"[cyan]Loading pages:[/cyan] {args.pages}")
    pages = load_pages(args.pages)
    console.log(f"  Loaded {len(pages)} pages")

    console.log(f"[cyan]Loading section map:[/cyan] {args.sections}")
    section_map = load_section_map(args.sections)
    console.log(f"  Sections: {list(section_map.sections.keys())}")

    console.print()
    chunks = segment_pages(
        pages=pages,
        section_map=section_map,
        book_slug=args.book_slug,
        verbose=True,
    )

    save_chunks(chunks, args.output)
    console.log(f"[green]✓ Saved[/green] {len(chunks)} chunks to {args.output}")

    print_summary(chunks)


if __name__ == "__main__":
    main()
