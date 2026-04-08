"""
Stage 4a: Project Gutenberg 영어 원전 파서.

The Joyful Wisdom (Project Gutenberg eBook #52881) 의 텍스트 파일을
파싱해서 섹션별 청크 리스트로 변환한다.

영어 원전 구조:
    PREFACE TO THE SECOND EDITION       (4 절: 1~4)
    JEST, RUSE AND REVENGE: A PRELUDE   (63 시: 1~63)
    BOOK FIRST                          (1~56)
    BOOK SECOND                         (57~107)
    BOOK THIRD                          (108~275)
    BOOK FOURTH: SANCTUS JANUARIUS      (276~342)
    BOOK FIFTH: WE FEARLESS ONES        (343~382)
    APPENDIX: SONGS OF PRINCE FREE-AS-A-BIRD  (Phase 2로 미룸)

번호 패턴: 큰 들여쓰기로 가운데 정렬된 "1.", "2.", ..., 예를 들어:
    "                                   1.\r\n"

주의: 영어 원전은 본편 전체에서 글로벌 번호 (1~382)를 사용한다.
즉 Book Second는 57부터, Book Third는 108부터 시작한다.
서문/부록은 자체 번호 (1~4, 1~63)를 사용한다.
"""

import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field
from rich.console import Console

console = Console()


# =====================
# 데이터 모델
# =====================


EnglishSection = Literal["preface", "prelude", "main_body", "appendix"]


class EnglishUnit(BaseModel):
    """영어 원전의 한 청크 (서문 절, 부록 시, 본편 아포리즘)."""

    section: EnglishSection = Field(..., description="섹션 타입")
    section_unit_number: int = Field(
        ...,
        description=(
            "글로벌 번호. preface 1~4, prelude 1~63, "
            "main_body 1~382 (Book 1~5 통합)"
        ),
    )
    book_number: int | None = Field(
        default=None, description="본편의 Book 번호 1~5 (main_body만)"
    )
    text: str = Field(..., description="영어 본문")
    char_count: int = Field(default=0, description="글자 수")


# =====================
# 섹션 헤더 패턴
# =====================

SECTION_HEADERS = [
    ("PREFACE TO THE SECOND", "preface", None),
    ("JEST, RUSE AND REVENGE", "prelude", None),
    ("BOOK FIRST", "main_body", 1),
    ("BOOK SECOND", "main_body", 2),
    ("BOOK THIRD", "main_body", 3),
    ("BOOK FOURTH", "main_body", 4),
    ("BOOK FIFTH", "main_body", 5),
    ("APPENDIX", "appendix", None),
]

# 청크 번호 패턴: 큰 들여쓰기로 가운데 정렬된 "1.", "2.", "382."
NUMBER_LINE_PATTERN = re.compile(r"^\s{20,}(\d+)\.\s*$")

# Gutenberg 시작/종료 마커
GUTENBERG_START = "*** START OF THE PROJECT GUTENBERG"
GUTENBERG_END = "*** END OF THE PROJECT GUTENBERG"


# =====================
# 파서
# =====================


def _strip_gutenberg_boilerplate(lines: list[str]) -> list[str]:
    """Gutenberg 헤더/푸터 제거."""
    start_idx = 0
    end_idx = len(lines)

    for i, line in enumerate(lines):
        if GUTENBERG_START in line:
            start_idx = i + 1
        elif GUTENBERG_END in line:
            end_idx = i
            break

    return lines[start_idx:end_idx]


def _find_section_starts(lines: list[str]) -> list[tuple[int, str, int | None]]:
    """각 섹션의 시작 라인 번호를 찾는다.

    Returns:
        list of (line_index, section_type, book_number)
    """
    starts: list[tuple[int, str, int | None]] = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        for header_text, section_type, book_num in SECTION_HEADERS:
            if not stripped.startswith(header_text):
                continue
            indent = len(line) - len(line.lstrip())
            if indent < 15:
                continue
            if len(stripped) > 60:
                continue
            starts.append((i, section_type, book_num))
            break
    return starts


def _extract_section_chunks(
    lines: list[str],
    start_idx: int,
    end_idx: int,
    section_type: str,
    book_number: int | None,
) -> list[EnglishUnit]:
    """특정 섹션 라인 범위에서 번호가 매겨진 청크들을 추출.

    영어 원전은 본편에서 글로벌 번호 (1~382)를 사용하므로
    별도 offset 계산 불필요. 그대로 사용.

    Args:
        lines: 전체 라인 리스트
        start_idx: 섹션 시작 라인
        end_idx: 섹션 끝 라인 (다음 섹션 시작)
        section_type: "preface" / "prelude" / "main_body" / "appendix"
        book_number: 본편 책 번호 (main_body만)

    Returns:
        EnglishUnit 리스트
    """
    units: list[EnglishUnit] = []

    # 섹션 안에서 번호 라인 찾기
    number_positions: list[tuple[int, int]] = []  # (line_idx, number)
    for i in range(start_idx, end_idx):
        line = lines[i]
        m = NUMBER_LINE_PATTERN.match(line)
        if m:
            number_positions.append((i, int(m.group(1))))

    if not number_positions:
        return units

    # 번호 사이의 텍스트가 그 번호의 본문
    for j, (num_line_idx, number) in enumerate(number_positions):
        body_start = num_line_idx + 1
        if j + 1 < len(number_positions):
            body_end = number_positions[j + 1][0]
        else:
            body_end = end_idx

        body_lines = lines[body_start:body_end]
        text = _clean_body_text(body_lines)

        if not text.strip():
            continue

        units.append(
            EnglishUnit(
                section=section_type,  # type: ignore
                section_unit_number=number,
                book_number=book_number,
                text=text,
                char_count=len(text),
            )
        )

    return units


def _clean_body_text(lines: list[str]) -> str:
    """본문 라인들을 합쳐서 깔끔한 텍스트로."""
    text_lines: list[str] = []
    for line in lines:
        line = line.rstrip("\r\n")
        if not line.strip():
            if text_lines and text_lines[-1] != "":
                text_lines.append("")
            continue
        text_lines.append(line.strip())

    # 단락 단위로 합치기
    paragraphs: list[str] = []
    current: list[str] = []
    for line in text_lines:
        if line == "":
            if current:
                paragraphs.append(" ".join(current))
                current = []
        else:
            current.append(line)
    if current:
        paragraphs.append(" ".join(current))

    return "\n\n".join(paragraphs)


def parse_gutenberg(text_path: str | Path) -> list[EnglishUnit]:
    """Project Gutenberg 영어 원전 텍스트를 파싱.

    Args:
        text_path: 영어 원전 .txt 파일 경로

    Returns:
        EnglishUnit 리스트 (preface 4 + prelude 63 + main 382 = 449)
    """
    text_path = Path(text_path)
    if not text_path.exists():
        raise FileNotFoundError(f"English text not found: {text_path}")

    raw = text_path.read_text(encoding="utf-8")
    lines = raw.splitlines()

    # Gutenberg 헤더/푸터 제거
    lines = _strip_gutenberg_boilerplate(lines)

    # 섹션 시작 위치 찾기
    section_starts = _find_section_starts(lines)
    if not section_starts:
        raise ValueError("섹션 헤더를 찾을 수 없음")

    console.log(f"[cyan]Found {len(section_starts)} section headers[/cyan]")
    for line_idx, section_type, book_num in section_starts:
        book_str = f" book={book_num}" if book_num else ""
        console.log(f"  line {line_idx}: {section_type}{book_str}")

    all_units: list[EnglishUnit] = []

    for i, (start_line, section_type, book_num) in enumerate(section_starts):
        end_line = (
            section_starts[i + 1][0] if i + 1 < len(section_starts) else len(lines)
        )

        # APPENDIX는 Phase 2로 미룸
        if section_type == "appendix":
            console.log(
                f"[yellow]Skipping {section_type} (Phase 2)[/yellow] "
                f"lines {start_line}~{end_line}"
            )
            continue

        units = _extract_section_chunks(
            lines=lines,
            start_idx=start_line,
            end_idx=end_line,
            section_type=section_type,
            book_number=book_num,
        )
        all_units.extend(units)
        console.log(
            f"  [green]✓[/green] {section_type}"
            f"{f' book={book_num}' if book_num else ''}: "
            f"{len(units)} units"
        )

    return all_units


def save_units_jsonl(units: list[EnglishUnit], output_path: str | Path) -> None:
    """파싱 결과를 JSONL로 저장."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for unit in units:
            f.write(unit.model_dump_json() + "\n")
    console.log(f"[green]✓ Saved[/green] {len(units)} units to {output_path}")
