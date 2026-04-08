"""
Stage 3: 페이지를 아포리즘 단위 청크로 분할.

섹션마다 다른 분할 전략:
- 서문 (preface): 짧은 숫자 블록 ("1.", "2.", ...)으로 절 분리
- 부록 시 (appendix_body): 짧은 숫자 블록으로 시 분리
- 본편 (main_body): 3중 신호 (block_type 기반)
    1. SectionHeader 블록 (Marker가 명시적으로 헤더로 분류) → 'section_header'
    2. Text 블록 "N." 패턴 → 'number_block'
    3. title.— 패턴 (fallback) → 'title_pattern'

핵심 변경 (v2):
- block_type 정보를 본편 분할에 활용
- Marker가 잘 분류한 경계(SectionHeader)를 1순위 신호로 사용
- regex 의존 최소화, 단조 증가 검증으로 false positive 방지

분할 철학: Type B (over-seg) > Type A (under-seg).
"""

import re
from typing import Iterator

from rich.console import Console

from data_pipeline.books import joyful_science as jw
from data_pipeline.schema import Chunk, ExtractedPage, SectionMap

console = Console()


# =====================
# 분할 신호 정규식
# =====================

# 명시적 번호 블록: "1.", "2.", ..., "383."
NUMBER_BLOCK_PATTERN = re.compile(r"^(\d+)\.$")

# SectionHeader 번호 패턴: "7.", "14" (마침표 있어도 없어도)
SECTION_HEADER_NUMBER_PATTERN = re.compile(r"^(\d+)\.?$")

# 본편 제목.— 패턴 (fallback)
TITLE_DASH_PATTERN = re.compile(r"^([^—\n.]{1,20})\.\s*[—–]\s+")


def _parse_number_block(text: str) -> int | None:
    """블록 텍스트가 명시적 번호 'N.' 인지 검사."""
    text = text.strip()
    if len(text) > 5:
        return None
    m = NUMBER_BLOCK_PATTERN.match(text)
    if m:
        return int(m.group(1))
    return None


def _parse_section_header_number(text: str) -> int | None:
    """SectionHeader 텍스트에서 숫자 추출 (마침표 있어도 없어도).

    예: "7." → 7, "14" → 14, "폭력배의 금언." → None
    """
    text = text.strip()
    if len(text) > 5:
        return None
    m = SECTION_HEADER_NUMBER_PATTERN.match(text)
    if m:
        return int(m.group(1))
    return None


def _matches_title_pattern(text: str) -> bool:
    """블록 텍스트가 본편 '제목.—' 패턴으로 시작하는지 검사."""
    if len(text) < 5:
        return False
    return bool(TITLE_DASH_PATTERN.match(text))


def _get_max_book_number(book_module) -> int:
    """책 모듈에서 본편 최대 번호 추출 (monotonic check용)."""
    if hasattr(book_module, "BOOK_RANGES"):
        ranges = book_module.BOOK_RANGES
        if ranges:
            return max(end for _, (_, end) in ranges.items())
    return 1000


# =====================
# 공통 헬퍼
# =====================


def _content_blocks(page: ExtractedPage) -> list:
    """노이즈 아닌 블록만 반환."""
    return [b for b in page.blocks if not b.is_noise and b.text.strip()]


def _make_chunk_id(book_slug: str, section_type: str, index: int) -> str:
    """청크 ID 생성."""
    if section_type == "preface":
        return f"{book_slug}_preface_{index}"
    if section_type == "appendix_poem":
        return f"{book_slug}_appendix_{index}"
    if section_type == "aphorism":
        return f"{book_slug}_aph_{index}"
    return f"{book_slug}_unknown_{index}"


# =====================
# 서문 분할 (변경 없음)
# =====================


def segment_preface(
    pages: list[ExtractedPage], book_slug: str
) -> list[Chunk]:
    """서문 페이지들을 절 단위 청크로 분할.

    분할 신호: 짧은 숫자 블록 ("1.", "2.", "3.", "4.")
    """
    chunks: list[Chunk] = []
    current_number: int | None = None
    current_text: list[str] = []
    current_pages: list[int] = []

    def emit() -> None:
        if current_number is None or not current_text:
            return
        text = "\n".join(current_text)
        chunks.append(
            Chunk(
                id=_make_chunk_id(book_slug, "preface", current_number),
                book_slug=book_slug,
                section_type="preface",
                unit_number=current_number,
                text_ko_raw=text,
                char_count_ko=len(text),
                source_pages=sorted(set(current_pages)),
                split_signal="number_block",
                detected_number=current_number,
            )
        )

    for page in pages:
        for block in _content_blocks(page):
            number = _parse_number_block(block.text)
            if number is not None:
                emit()
                current_number = number
                current_text = []
                current_pages = [page.page_num]
            else:
                if current_number is not None:
                    current_text.append(block.text)
                    if page.page_num not in current_pages:
                        current_pages.append(page.page_num)

    emit()
    return chunks


# =====================
# 부록 시 분할 (변경 없음)
# =====================


def segment_appendix(
    pages: list[ExtractedPage], book_slug: str
) -> list[Chunk]:
    """부록 시 페이지들을 시 단위 청크로 분할."""
    chunks: list[Chunk] = []
    current_number: int | None = None
    current_text: list[str] = []
    current_pages: list[int] = []

    def emit() -> None:
        if current_number is None or not current_text:
            return
        text = "\n".join(current_text)
        chunks.append(
            Chunk(
                id=_make_chunk_id(book_slug, "appendix_poem", current_number),
                book_slug=book_slug,
                section_type="appendix_poem",
                unit_number=current_number,
                text_ko_raw=text,
                char_count_ko=len(text),
                source_pages=sorted(set(current_pages)),
                split_signal="number_block",
                detected_number=current_number,
            )
        )

    for page in pages:
        for block in _content_blocks(page):
            number = _parse_number_block(block.text)
            if number is not None:
                emit()
                current_number = number
                current_text = []
                current_pages = [page.page_num]
            else:
                if current_number is not None:
                    current_text.append(block.text)
                    if page.page_num not in current_pages:
                        current_pages.append(page.page_num)

    emit()
    return chunks


# =====================
# 본편 분할 (대폭 재작성: block_type 활용)
# =====================


def segment_main_body(
    pages: list[ExtractedPage], book_slug: str
) -> list[Chunk]:
    """본편 페이지들을 아포리즘 단위 청크로 분할.

    분할 신호 (우선순위 순):
    1. SectionHeader 블록 (Marker가 명시적으로 헤더로 분류)
       → split_signal='section_header'
       예: SectionHeader "7." → 아포리즘 #7 시작
       예: SectionHeader "14" → 아포리즘 #14 시작 (마침표 없어도 신뢰)
    2. Text 블록 "N." 패턴 → split_signal='number_block'
       예: Text "2." → 아포리즘 #2 시작
    3. title.— 패턴 (fallback for missing numbers)
       → split_signal='title_pattern'
       단, 막 boundary가 시작된 직후(current_text 비어있음)면 무시
       (안 그러면 number 정보를 덮어씀)

    Monotonic check:
    - 책 범위(1~max) 밖이면 거부
    - 직전 번호보다 작거나, 너무 큰 점프(>50)면 거부
    """
    chunks: list[Chunk] = []
    current_text: list[str] = []
    current_pages: list[int] = []
    current_signal: str | None = None
    current_number: int | None = None
    chunk_index = 0

    # Monotonic check 상태
    last_accepted_number: int = 0
    max_book_number = _get_max_book_number(jw)

    def emit() -> None:
        nonlocal chunk_index
        if not current_text:
            return
        chunk_index += 1
        text = "\n".join(current_text)
        chunks.append(
            Chunk(
                id=_make_chunk_id(book_slug, "aphorism", chunk_index),
                book_slug=book_slug,
                section_type="aphorism",
                unit_number=current_number,
                text_ko_raw=text,
                char_count_ko=len(text),
                source_pages=sorted(set(current_pages)),
                split_signal=current_signal,
                detected_number=current_number,
            )
        )

    def is_valid_number(n: int) -> bool:
        """감지된 번호가 책 범위 내이고 단조 증가하는지."""
        if n < 1 or n > max_book_number:
            return False
        if n < last_accepted_number:
            return False  # 역행 거부
        if n > last_accepted_number + 50:
            return False  # 너무 큰 점프 거부
        return True

    def start_new_chunk(
        signal: str,
        number: int | None,
        page_num: int,
        initial_text: str | None = None,
    ) -> None:
        nonlocal current_text, current_pages, current_signal, current_number
        nonlocal last_accepted_number
        emit()
        current_text = [initial_text] if initial_text else []
        current_pages = [page_num]
        current_signal = signal
        current_number = number
        if number is not None:
            last_accepted_number = number

    def append_to_current(text: str, page_num: int) -> None:
        nonlocal current_text, current_pages, current_signal
        if not current_text and current_signal is None:
            current_signal = "first_chunk"
        current_text.append(text)
        if page_num not in current_pages:
            current_pages.append(page_num)

    for page in pages:
        for block in _content_blocks(page):
            text = block.text
            bt = block.block_type

            # === 신호 1: SectionHeader ===
            if bt == "SectionHeader":
                n = _parse_section_header_number(text)
                if n is not None and is_valid_number(n):
                    # 새 아포리즘 (헤더 텍스트 자체는 본문에 포함하지 않음)
                    start_new_chunk("section_header", n, page.page_num)
                    continue
                # SectionHeader지만 숫자 아니거나 invalid → 본문 일부로 취급
                append_to_current(text, page.page_num)
                continue

            # === 신호 2: Text 블록 "N." ===
            if bt == "Text":
                n = _parse_number_block(text)
                if n is not None and is_valid_number(n):
                    # 새 아포리즘 (번호 텍스트는 본문에 포함하지 않음)
                    start_new_chunk("number_block", n, page.page_num)
                    continue

                # === 신호 3: title.— 패턴 (fallback) ===
                # 단, 막 boundary가 시작된 직후라면 무시
                # (number_block 직후 첫 본문이 title 패턴일 수 있음)
                if _matches_title_pattern(text) and current_text:
                    start_new_chunk(
                        "title_pattern",
                        None,
                        page.page_num,
                        initial_text=text,
                    )
                    continue

            # === 경계 아님 → 현재 청크에 추가 ===
            append_to_current(text, page.page_num)

    emit()
    return chunks


# =====================
# 메인 진입점 (변경 없음)
# =====================


def segment_pages(
    pages: list[ExtractedPage],
    section_map: SectionMap,
    book_slug: str = jw.BOOK_SLUG,
    verbose: bool = True,
) -> list[Chunk]:
    """전체 페이지를 섹션별로 분할해 청크 리스트로 반환."""
    page_by_num: dict[int, ExtractedPage] = {p.page_num: p for p in pages}

    preface_page_nums = section_map.sections.get("preface", [])
    appendix_page_nums = section_map.sections.get("appendix_body", [])
    main_page_nums = section_map.sections.get("main_body", [])

    preface_pages = [page_by_num[n] for n in sorted(preface_page_nums) if n in page_by_num]
    appendix_pages = [page_by_num[n] for n in sorted(appendix_page_nums) if n in page_by_num]
    main_pages = [page_by_num[n] for n in sorted(main_page_nums) if n in page_by_num]

    if verbose:
        console.log(
            f"[cyan]Segmenting:[/cyan] preface={len(preface_pages)} pages, "
            f"appendix={len(appendix_pages)} pages, main={len(main_pages)} pages"
        )

    all_chunks: list[Chunk] = []

    if preface_pages:
        preface_chunks = segment_preface(preface_pages, book_slug)
        all_chunks.extend(preface_chunks)
        if verbose:
            console.log(f"  [green]✓[/green] preface: {len(preface_chunks)} chunks")

    if appendix_pages:
        appendix_chunks = segment_appendix(appendix_pages, book_slug)
        all_chunks.extend(appendix_chunks)
        if verbose:
            console.log(f"  [green]✓[/green] appendix: {len(appendix_chunks)} chunks")

    if main_pages:
        main_chunks = segment_main_body(main_pages, book_slug)
        all_chunks.extend(main_chunks)
        if verbose:
            console.log(f"  [green]✓[/green] main_body: {len(main_chunks)} chunks")

    if verbose:
        console.log(f"[bold green]Total chunks: {len(all_chunks)}[/bold green]")

    return all_chunks
