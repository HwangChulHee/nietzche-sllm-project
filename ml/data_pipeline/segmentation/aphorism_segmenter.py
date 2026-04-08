"""
Stage 3: 페이지를 아포리즘 단위 청크로 분할.

섹션마다 다른 분할 전략을 사용한다:
- 서문 (preface): 짧은 숫자 블록 ("1.", "2.", ...)으로 절 분리
- 부록 시 (appendix_body): 짧은 숫자 블록으로 시 분리
- 본편 (main_body): 3중 휴리스틱
    1. 명시적 번호 블록 ("2." 등)
    2. SectionHeader (Phase 2에서 추가, 현재는 미사용)
    3. 제목.— 패턴 ("지적 양심.—...", "고귀와 비속.—...")

분할 철학: Type B (over-segmentation)을 Type A (under-segmentation)보다 선호.
- Over: 두 청크가 같은 영어 아포리즘에 매칭되면 Stage 4에서 병합 (쉬움)
- Under: 한 청크가 두 영어 아포리즘에 매칭되면 분리 위치 찾기 어려움
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

# 신호 1: 명시적 번호 블록 ("1.", "2.", ..., "383.")
#   - 짧은 블록 (5자 이하)
#   - 순수 "숫자."
NUMBER_BLOCK_PATTERN = re.compile(r"^(\d+)\.$")

# 신호 3: 본편 제목.— 패턴
#   - 짧은 제목 (20자 이하) + 마침표 + 줄표(— 또는 –) + 공백
#   - 예: "지적 양심. —", "고귀와 비속.—", "존재의 목적을 가르치는 교사.—"
#   - "[^—\n.]" 으로 줄표/줄바꿈/마침표가 제목 안에 안 들어오게 함
TITLE_DASH_PATTERN = re.compile(r"^([^—\n.]{1,20})\.\s*[—–]\s+")


def _parse_number_block(text: str) -> int | None:
    """블록 텍스트가 명시적 번호인지 검사. 맞으면 번호 반환, 아니면 None."""
    text = text.strip()
    if len(text) > 5:
        return None
    m = NUMBER_BLOCK_PATTERN.match(text)
    if m:
        return int(m.group(1))
    return None


def _matches_title_pattern(text: str) -> bool:
    """블록 텍스트가 본편 '제목.—' 패턴으로 시작하는지 검사."""
    if len(text) < 5:
        return False
    return bool(TITLE_DASH_PATTERN.match(text))


# =====================
# 공통 헬퍼
# =====================


def _content_blocks(page: ExtractedPage) -> list:
    """노이즈 아닌 블록만 반환 (텍스트가 비어있지 않은 것)."""
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
# 서문 분할
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
                # 새 절 시작
                emit()
                current_number = number
                current_text = []
                current_pages = [page.page_num]
            else:
                if current_number is not None:
                    current_text.append(block.text)
                    if page.page_num not in current_pages:
                        current_pages.append(page.page_num)

    # 마지막 절
    emit()

    return chunks


# =====================
# 부록 시 분할
# =====================


def segment_appendix(
    pages: list[ExtractedPage], book_slug: str
) -> list[Chunk]:
    """부록 시 페이지들을 시 단위 청크로 분할.

    분할 신호: 짧은 숫자 블록 ("1.", "2.", ..., "63.")
    서문과 동일한 알고리즘이지만 section_type만 다름.
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
# 본편 분할 (가장 까다로움)
# =====================


def segment_main_body(
    pages: list[ExtractedPage], book_slug: str
) -> list[Chunk]:
    """본편 페이지들을 아포리즘 단위 청크로 분할.

    분할 신호 (우선순위 순):
    1. 명시적 번호 블록 ("2." 등) → split_signal="number_block"
    2. 제목.— 패턴 ("지적 양심.—" 등) → split_signal="title_pattern"

    Marker가 본편 1번, 3번처럼 번호 없는 케이스를 잡지 못하므로
    신호 2 (제목 패턴)이 핵심. 약간의 over-segmentation을 허용해서
    Stage 4 영어 Anchor 매핑에서 보정.
    """
    chunks: list[Chunk] = []

    # 현재 청크 누적용 상태
    current_text: list[str] = []
    current_pages: list[int] = []
    current_signal: str | None = None
    current_number: int | None = None
    chunk_index = 0  # 본편 청크 순서 (ID 생성용)

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
                unit_number=current_number,  # 명시적 번호 있으면 채움, 없으면 None
                text_ko_raw=text,
                char_count_ko=len(text),
                source_pages=sorted(set(current_pages)),
                split_signal=current_signal,
                detected_number=current_number,
            )
        )

    for page in pages:
        for block in _content_blocks(page):
            text = block.text

            # 신호 1: 명시적 번호 블록
            number = _parse_number_block(text)
            if number is not None:
                # 새 아포리즘 시작
                emit()
                current_text = []
                current_pages = [page.page_num]
                current_signal = "number_block"
                current_number = number
                # 번호 블록 자체는 본문에 포함하지 않음
                continue

            # 신호 3: 제목.— 패턴
            if _matches_title_pattern(text):
                # 새 아포리즘 시작
                emit()
                current_text = [text]  # 제목 블록도 본문에 포함
                current_pages = [page.page_num]
                current_signal = "title_pattern"
                current_number = None
                continue

            # 분할 신호 아님 → 현재 청크에 추가
            if not current_text and current_signal is None:
                # 첫 청크 시작 (신호 없이)
                current_signal = "first_chunk"
            current_text.append(text)
            if page.page_num not in current_pages:
                current_pages.append(page.page_num)

    # 마지막 청크
    emit()

    return chunks


# =====================
# 메인 진입점
# =====================


def segment_pages(
    pages: list[ExtractedPage],
    section_map: SectionMap,
    book_slug: str = jw.BOOK_SLUG,
    verbose: bool = True,
) -> list[Chunk]:
    """전체 페이지를 섹션별로 분할해 청크 리스트로 반환.

    Args:
        pages: Stage 2 출력 (annotated, role 채워진 페이지들)
        section_map: Stage 2 출력 (섹션별 페이지 번호)
        book_slug: 책 식별자
        verbose: True면 진행 로그 출력

    Returns:
        Chunk 리스트 (서문 → 부록 → 본편 순)
    """
    # 페이지를 page_num으로 인덱싱
    page_by_num: dict[int, ExtractedPage] = {p.page_num: p for p in pages}

    # 섹션별 페이지 번호 (Stage 2가 채운 sections 사용)
    preface_page_nums = section_map.sections.get("preface", [])
    appendix_page_nums = section_map.sections.get("appendix_body", [])
    main_page_nums = section_map.sections.get("main_body", [])

    # 페이지 객체 리스트로 변환
    preface_pages = [page_by_num[n] for n in sorted(preface_page_nums) if n in page_by_num]
    appendix_pages = [page_by_num[n] for n in sorted(appendix_page_nums) if n in page_by_num]
    main_pages = [page_by_num[n] for n in sorted(main_page_nums) if n in page_by_num]

    if verbose:
        console.log(
            f"[cyan]Segmenting:[/cyan] preface={len(preface_pages)} pages, "
            f"appendix={len(appendix_pages)} pages, main={len(main_pages)} pages"
        )

    all_chunks: list[Chunk] = []

    # 1. 서문
    if preface_pages:
        preface_chunks = segment_preface(preface_pages, book_slug)
        all_chunks.extend(preface_chunks)
        if verbose:
            console.log(f"  [green]✓[/green] preface: {len(preface_chunks)} chunks")

    # 2. 부록 시
    if appendix_pages:
        appendix_chunks = segment_appendix(appendix_pages, book_slug)
        all_chunks.extend(appendix_chunks)
        if verbose:
            console.log(f"  [green]✓[/green] appendix: {len(appendix_chunks)} chunks")

    # 3. 본편
    if main_pages:
        main_chunks = segment_main_body(main_pages, book_slug)
        all_chunks.extend(main_chunks)
        if verbose:
            console.log(f"  [green]✓[/green] main_body: {len(main_chunks)} chunks")

    if verbose:
        console.log(f"[bold green]Total chunks: {len(all_chunks)}[/bold green]")

    return all_chunks
