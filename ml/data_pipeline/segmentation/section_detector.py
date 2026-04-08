"""
Stage 2: 페이지 역할 감지 (섹션 분류).

마커 기반 상태 기계로 각 페이지를 섹션 역할(PageRole)로 분류한다.

상태 흐름:
    SEEKING_PREFACE     ← 시작
        ↓ "제2판 서문" 마커 발견
    IN_PREFACE          ← 서문 본문 페이지들
        ↓ 에머슨 마커 발견
    SEEKING_APPENDIX    ← 에머슨/독일어 속표지 통과 중
        ↓ "농담, 간계 그리고 복수" 마커 발견
    IN_APPENDIX         ← 부록 시 본문 페이지들
        ↓ "존재의 목적을 가르치는 교사" 마커 발견
    IN_MAIN_BODY        ← 본편 본문 페이지들
"""

from enum import Enum

from rich.console import Console

from data_pipeline.books import joyful_science as jw
from data_pipeline.schema import ExtractedPage, PageRole, SectionMap

console = Console()


class DetectorState(str, Enum):
    """섹션 감지 상태 기계의 상태."""

    SEEKING_PREFACE = "seeking_preface"
    IN_PREFACE = "in_preface"
    SEEKING_APPENDIX = "seeking_appendix"
    IN_APPENDIX = "in_appendix"
    IN_MAIN_BODY = "in_main_body"


def detect_sections(
    pages: list[ExtractedPage],
    book_slug: str = jw.BOOK_SLUG,
    verbose: bool = True,
) -> tuple[list[ExtractedPage], SectionMap]:
    """페이지 리스트를 순회하며 각 페이지에 역할을 부여하고 SectionMap을 반환.

    Args:
        pages: Stage 1에서 추출한 ExtractedPage 리스트 (page_num 순서대로)
        book_slug: 책 식별자 (현재는 joyful_science 만 지원)
        verbose: True면 상태 전환 과정을 콘솔에 출력

    Returns:
        (role이 채워진 ExtractedPage 리스트, SectionMap)
    """
    state = DetectorState.SEEKING_PREFACE
    page_roles: dict[int, PageRole] = {}
    classified_pages: list[ExtractedPage] = []

    for page in pages:
        text = page.clean_text
        new_state, role = _classify_page(state, text, page.page_num, verbose)

        page_roles[page.page_num] = role
        classified_pages.append(page.model_copy(update={"role": role}))
        state = new_state

    # SectionMap의 sections 필드 채우기
    sections: dict[str, list[int]] = {}
    for page_num, role in page_roles.items():
        # 본문 섹션만 sections에 포함 (속표지는 제외)
        if role in ("preface", "appendix_body", "main_body"):
            sections.setdefault(role, []).append(page_num)

    # 페이지 번호 정렬
    for section_name in sections:
        sections[section_name].sort()

    section_map = SectionMap(
        book_slug=book_slug,
        page_roles=page_roles,
        sections=sections,
    )

    if verbose:
        _print_summary(section_map, len(pages))

    return classified_pages, section_map


def _classify_page(
    state: DetectorState,
    text: str,
    page_num: int,
    verbose: bool,
) -> tuple[DetectorState, PageRole]:
    """현재 상태와 페이지 텍스트를 보고 (다음 상태, 역할)을 결정.

    상태 전환 우선순위:
        1. 본편 시작 마커 (어느 상태에서도 본편으로 전환 가능)
        2. 부록 시작 마커
        3. 독일어 속표지 마커
        4. 에머슨 속표지 마커
        5. 서문 시작 마커
    """
    # 1. 본편 시작 마커 — 가장 우선순위 높음
    # 어느 상태에서도 본편 마커가 등장하면 즉시 전환
    if jw.MAIN_BODY_START_MARKER in text and state != DetectorState.IN_MAIN_BODY:
        _log_transition(state, DetectorState.IN_MAIN_BODY, page_num,
                        f"main body marker: '{jw.MAIN_BODY_START_MARKER}'", verbose)
        return DetectorState.IN_MAIN_BODY, "main_body"

    # 2. 부록 시 시작 마커
    if jw.APPENDIX_COVER_MARKER in text:
        _log_transition(state, DetectorState.IN_APPENDIX, page_num,
                        f"appendix cover marker: '{jw.APPENDIX_COVER_MARKER}'", verbose)
        return DetectorState.IN_APPENDIX, "appendix_cover"

    # 3. 독일어 원전 속표지
    if jw.GERMAN_COVER_MARKER in text:
        # 상태 전환은 없음, 역할만 부여
        if verbose:
            console.log(f"  [dim]Page {page_num}:[/dim] german_cover (marker found)")
        # 보통 에머슨 다음에 오므로 상태는 SEEKING_APPENDIX 유지
        next_state = DetectorState.SEEKING_APPENDIX if state == DetectorState.IN_PREFACE else state
        return next_state, "german_cover"

    # 4. 에머슨 속표지
    if jw.EMERSON_COVER_MARKER in text and state == DetectorState.IN_PREFACE:
        _log_transition(state, DetectorState.SEEKING_APPENDIX, page_num,
                        f"emerson cover marker: '{jw.EMERSON_COVER_MARKER}'", verbose)
        return DetectorState.SEEKING_APPENDIX, "emerson_cover"

    # 5. 서문 시작 마커
    if jw.PREFACE_START_MARKER in text and state == DetectorState.SEEKING_PREFACE:
        _log_transition(state, DetectorState.IN_PREFACE, page_num,
                        f"preface marker: '{jw.PREFACE_START_MARKER}'", verbose)
        return DetectorState.IN_PREFACE, "preface"

    # 마커 없음 — 현재 상태에 따라 역할 부여
    return _role_from_state(state), _continuing_role(state)


def _role_from_state(state: DetectorState) -> DetectorState:
    """마커 없을 때는 상태 유지."""
    return state


def _continuing_role(state: DetectorState) -> PageRole:
    """현재 상태에서 마커 없는 페이지의 역할을 결정.

    각 상태에서 '계속 같은 섹션이라고 가정'할 때의 역할.
    """
    mapping: dict[DetectorState, PageRole] = {
        DetectorState.SEEKING_PREFACE: "unknown",
        DetectorState.IN_PREFACE: "preface",
        DetectorState.SEEKING_APPENDIX: "unknown",
        DetectorState.IN_APPENDIX: "appendix_body",
        DetectorState.IN_MAIN_BODY: "main_body",
    }
    return mapping[state]


def _log_transition(
    from_state: DetectorState,
    to_state: DetectorState,
    page_num: int,
    reason: str,
    verbose: bool,
) -> None:
    """상태 전환 로그 출력."""
    if not verbose:
        return
    console.log(
        f"  [yellow]Page {page_num}:[/yellow] "
        f"{from_state.value} → [bold cyan]{to_state.value}[/bold cyan] "
        f"({reason})"
    )


def _print_summary(section_map: SectionMap, total_pages: int) -> None:
    """섹션 감지 결과 요약 출력."""
    from rich.table import Table

    table = Table(title="Section Detection Summary")
    table.add_column("Section", style="cyan")
    table.add_column("Page Count", justify="right")
    table.add_column("Page Range", style="dim")

    # 본문 섹션
    for section_name, page_list in section_map.sections.items():
        if page_list:
            page_range = f"{min(page_list)}~{max(page_list)}"
        else:
            page_range = "-"
        table.add_row(section_name, str(len(page_list)), page_range)

    # 속표지 / unknown
    cover_counts: dict[str, list[int]] = {}
    for page_num, role in section_map.page_roles.items():
        if role not in ("preface", "appendix_body", "main_body"):
            cover_counts.setdefault(role, []).append(page_num)

    for role, page_list in cover_counts.items():
        page_list.sort()
        if len(page_list) == 1:
            page_range = str(page_list[0])
        else:
            page_range = f"{min(page_list)}~{max(page_list)}"
        table.add_row(role, str(len(page_list)), page_range)

    console.print()
    console.print(table)
    console.print(f"\n[bold]Total pages classified:[/bold] {total_pages}")
