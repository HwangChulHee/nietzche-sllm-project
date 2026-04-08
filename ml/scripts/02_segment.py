"""
Stage 2: 추출된 페이지 JSONL → 섹션 분류 결과 JSON

Usage:
    poetry run python scripts/02_segment.py \
        --pages data/extracted/joyful_science_sample_pages.jsonl \
        --output data/extracted/joyful_science_sample_sections.json

출력 포맷:
    SectionMap (book_slug, page_roles, sections)을 JSON으로 직렬화한 파일.
    원본 페이지 데이터에 role이 추가된 결과는 별도 JSONL로 저장.
"""

import argparse
import json
from pathlib import Path

from rich.console import Console

from data_pipeline.schema import ExtractedPage
from data_pipeline.segmentation.section_detector import detect_sections

console = Console()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage 2: Section detection")
    parser.add_argument(
        "--pages",
        type=Path,
        required=True,
        help="Stage 1 출력 JSONL 파일 경로",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="섹션 맵 JSON 출력 경로",
    )
    parser.add_argument(
        "--annotated-pages",
        type=Path,
        default=None,
        help="role이 추가된 페이지 JSONL 출력 경로 (지정 안 하면 자동 생성)",
    )
    return parser.parse_args()


def load_pages(jsonl_path: Path) -> list[ExtractedPage]:
    """Stage 1 출력 JSONL을 ExtractedPage 리스트로 로드."""
    pages: list[ExtractedPage] = []
    with jsonl_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            pages.append(ExtractedPage.model_validate(data))
    return pages


def main() -> None:
    args = parse_args()

    if not args.pages.exists():
        console.print(f"[red]Error:[/red] Pages file not found: {args.pages}")
        raise SystemExit(1)

    # 입력 로드
    console.log(f"Loading pages from {args.pages}")
    pages = load_pages(args.pages)
    console.log(f"[green]Loaded[/green] {len(pages)} pages")

    # 섹션 감지 실행
    console.print("\n[bold]Running section detection...[/bold]\n")
    classified_pages, section_map = detect_sections(pages)

    # SectionMap 저장
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        # SectionMap의 page_roles는 dict[int, ...] 인데
        # JSON은 int key를 지원 안 하므로 model_dump_json 사용
        f.write(section_map.model_dump_json(indent=2))

    console.print(f"\n[green]✓ Saved section map to[/green] {args.output}")

    # role이 추가된 페이지도 JSONL로 저장 (Stage 3 입력용)
    annotated_path = args.annotated_pages or args.pages.with_name(
        args.pages.stem + "_annotated.jsonl"
    )
    with annotated_path.open("w", encoding="utf-8") as f:
        for page in classified_pages:
            f.write(page.model_dump_json() + "\n")

    console.print(f"[green]✓ Saved annotated pages to[/green] {annotated_path}")


if __name__ == "__main__":
    main()
