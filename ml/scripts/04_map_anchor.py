"""
Stage 4 CLI: 한국어 청크 → 영어 Anchor 매핑 (anchor-based, v3).

Usage:
    python scripts/04_map_anchor.py \\
        --chunks data/chunks/joyful_science_chunks_raw.jsonl \\
        --english data/anchors/joyful_science_english_units.jsonl \\
        --output data/chunks/joyful_science_chunks_mapped.jsonl
"""

import argparse
import json
from collections import Counter
from pathlib import Path

from rich.console import Console
from rich.table import Table

from data_pipeline.alignment.embedder import MultilingualEmbedder
from data_pipeline.alignment.mapper import MappingConfig, map_chunks_to_english
from data_pipeline.anchors.gutenberg_parser import EnglishUnit
from data_pipeline.books import joyful_science as jw
from data_pipeline.schema import Chunk

console = Console()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Stage 4: Map Korean chunks to English anchors (anchor-based)",
    )
    parser.add_argument("--chunks", type=Path, required=True)
    parser.add_argument("--english", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--low-confidence-threshold", type=float, default=0.75)
    parser.add_argument("--min-embedding-score", type=float, default=0.50)
    parser.add_argument(
        "--embedding-model",
        type=str,
        default="intfloat/multilingual-e5-large",
    )
    return parser.parse_args()


def load_chunks(path: Path) -> list[Chunk]:
    chunks: list[Chunk] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            chunks.append(Chunk.model_validate_json(line))
    return chunks


def load_english_units(path: Path) -> list[EnglishUnit]:
    units: list[EnglishUnit] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            units.append(EnglishUnit.model_validate_json(line))
    return units


def save_chunks(chunks: list[Chunk], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(chunk.model_dump_json() + "\n")


def print_summary(chunks: list[Chunk], missing: dict) -> None:
    total = len(chunks)
    if total == 0:
        console.print("[red]No chunks.[/red]")
        return

    # 섹션별
    section_table = Table(title="Mapping by Section", show_header=True)
    section_table.add_column("Section", style="cyan")
    section_table.add_column("Count", justify="right")
    section_table.add_column("Mapped", justify="right")
    section_table.add_column("Avg conf", justify="right")
    section_table.add_column("Avg chars", justify="right")

    for section in ("preface", "appendix_poem", "aphorism"):
        section_chunks = [c for c in chunks if c.section_type == section]
        if not section_chunks:
            continue
        mapped = [c for c in section_chunks if c.mapping_method != "unmapped"]
        confs = [c.mapping_confidence for c in mapped if c.mapping_confidence]
        avg_conf = sum(confs) / len(confs) if confs else 0.0
        avg_chars = sum(c.char_count_ko for c in section_chunks) / len(section_chunks)
        section_table.add_row(
            section,
            str(len(section_chunks)),
            str(len(mapped)),
            f"{avg_conf:.3f}",
            f"{avg_chars:,.0f}",
        )

    console.print()
    console.print(section_table)

    # 방법 분포
    method_counts = Counter(c.mapping_method for c in chunks)
    method_table = Table(title="Mapping Method", show_header=True)
    method_table.add_column("Method", style="cyan")
    method_table.add_column("Count", justify="right")
    method_table.add_column("%", justify="right")
    for method, count in method_counts.most_common():
        pct = count / total * 100
        method_table.add_row(str(method), str(count), f"{pct:.1f}%")
    console.print()
    console.print(method_table)

    # 신뢰도 분포 (본편)
    aph_chunks = [c for c in chunks if c.section_type == "aphorism"]
    if aph_chunks:
        confs = [c.mapping_confidence or 0.0 for c in aph_chunks]
        buckets = {
            "1.00 (number)": sum(1 for c in confs if c >= 1.0),
            "0.90~1.00": sum(1 for c in confs if 0.90 <= c < 1.0),
            "0.85~0.90": sum(1 for c in confs if 0.85 <= c < 0.90),
            "0.80~0.85": sum(1 for c in confs if 0.80 <= c < 0.85),
            "0.75~0.80": sum(1 for c in confs if 0.75 <= c < 0.80),
            "0.50~0.75": sum(1 for c in confs if 0.50 <= c < 0.75),
            "<0.50": sum(1 for c in confs if c < 0.50),
        }
        console.print()
        console.print("[bold]Main body confidence distribution:[/bold]")
        max_count = max(buckets.values()) if buckets else 1
        for bucket, count in buckets.items():
            bar = "█" * (count * 40 // max(max_count, 1))
            console.print(f"  {bucket:>15s}: {count:4d} {bar}")

    # 플래그
    all_flags = [flag for c in chunks for flag in c.mapping_flags]
    flag_counts = Counter(all_flags)
    if flag_counts:
        console.print()
        console.print("[bold]Mapping flags:[/bold]")
        for flag, count in flag_counts.most_common():
            console.print(f"  {flag}: {count}")

    # 누락
    console.print()
    console.print("[bold]Missing English units:[/bold]")
    for section, nums in missing.items():
        if nums:
            preview = nums[:15]
            more = f" ... ({len(nums)} total)" if len(nums) > 15 else ""
            console.print(f"  {section}: {preview}{more}")
        else:
            console.print(f"  {section}: [green]none[/green]")

    # 샘플
    main_chunks = [c for c in chunks if c.section_type == "aphorism"]
    if main_chunks:
        first = next((c for c in main_chunks if c.unit_number == 1), main_chunks[0])
        console.print()
        console.print("[bold]Sample: Main body #1:[/bold]")
        console.print(f"  ID: {first.id}")
        console.print(f"  unit_number: {first.unit_number}")
        console.print(f"  book_number: {first.book_number}")
        console.print(f"  method: {first.mapping_method}")
        console.print(f"  confidence: {first.mapping_confidence}")
        ko_preview = first.text_ko_raw[:120].replace("\n", " ")
        en_preview = first.text_en_anchor[:120].replace("\n", " ")
        console.print(f"  KO: {ko_preview}")
        console.print(f"  EN: {en_preview}")


def main() -> None:
    args = parse_args()

    if not args.chunks.exists():
        console.print(f"[red]Error:[/red] Chunks not found: {args.chunks}")
        raise SystemExit(1)
    if not args.english.exists():
        console.print(f"[red]Error:[/red] English not found: {args.english}")
        raise SystemExit(1)

    # 로드
    console.log(f"[cyan]Loading Korean chunks:[/cyan] {args.chunks}")
    chunks = load_chunks(args.chunks)
    console.log(f"  Loaded {len(chunks)} chunks")

    console.log(f"[cyan]Loading English units:[/cyan] {args.english}")
    en_units = load_english_units(args.english)
    console.log(f"  Loaded {len(en_units)} English units")

    # 모델 로드
    embedder = MultilingualEmbedder(model_name=args.embedding_model)

    # 설정
    config = MappingConfig(
        low_confidence_threshold=args.low_confidence_threshold,
        min_embedding_score=args.min_embedding_score,
    )

    # 매핑
    console.print()
    console.log("[bold cyan]Starting anchor-based mapping...[/bold cyan]")
    result = map_chunks_to_english(
        ko_chunks=chunks,
        en_units=en_units,
        embedder=embedder,
        config=config,
        book_ranges=jw.BOOK_RANGES,
    )

    # 저장
    save_chunks(result.chunks, args.output)
    console.log(
        f"[green]✓ Saved[/green] {len(result.chunks)} chunks to {args.output}"
    )

    # 요약
    print_summary(result.chunks, result.missing_en_numbers)


if __name__ == "__main__":
    main()
