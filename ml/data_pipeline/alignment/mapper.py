"""
Stage 4: 한국어 청크 ↔ 영어 Anchor 매핑.

알고리즘: **Anchor-based mapping** (v3, 재설계)

핵심 통찰:
- Stage 3의 새 분할이 detected_number를 86%까지 잡음
- 번호 있는 청크는 영어 unit에 1:1 직접 매칭 (신뢰도 1.0)
- 번호 없는 청크는 인접 anchor 사이의 좁은 후보 집합에서 임베딩으로 선택
- DP로 gap 내 monotonic alignment를 풀어서 drift 방지

장점 (v2 sentence alignment 대비):
- Hard anchor가 박혀있어 collapse 불가능
- 임베딩 호출이 ~50회 (전체 임베딩 ~7000회 → 100배 감소)
- 책 무관 (책 전용 로직 없음)
- 디버깅 쉬움 (모든 매칭이 명시적 anchor에 묶임)

섹션별:
- preface / appendix_poem: 번호 직접 매칭 (기존과 동일)
- aphorism (본편): anchor + DP gap alignment
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from rich.console import Console

from data_pipeline.alignment.embedder import MultilingualEmbedder
from data_pipeline.anchors.gutenberg_parser import EnglishUnit
from data_pipeline.schema import Chunk

if TYPE_CHECKING:
    pass

console = Console()


# =====================
# 설정
# =====================


@dataclass
class MappingConfig:
    """매핑 알고리즘 설정."""

    # 신뢰도 임계값: 이 이하면 low_confidence 플래그
    low_confidence_threshold: float = 0.75

    # 임베딩 매칭 시 최소 점수 (이 이하면 unmapped)
    min_embedding_score: float = 0.50


# =====================
# 매핑 결과
# =====================


@dataclass
class MappingResult:
    """Stage 4 매핑 전체 결과."""

    chunks: list[Chunk] = field(default_factory=list)
    missing_en_numbers: dict[str, list[int]] = field(default_factory=dict)


# =====================
# 섹션 매핑
# =====================


KO_TO_EN_SECTION = {
    "preface": "preface",
    "appendix_poem": "prelude",
    "aphorism": "main_body",
}


def _filter_en_units_by_section(
    en_units: list[EnglishUnit], en_section: str
) -> list[EnglishUnit]:
    filtered = [u for u in en_units if u.section == en_section]
    filtered.sort(key=lambda u: u.section_unit_number)
    return filtered


def _assign(
    chunk: Chunk,
    unit: EnglishUnit,
    method: str,
    confidence: float,
    book_ranges: dict[int, tuple[int, int]] | None,
    config: MappingConfig,
) -> None:
    """청크에 영어 unit을 할당하고 메타데이터 채움."""
    chunk.text_en_anchor = unit.text
    chunk.unit_number = unit.section_unit_number
    chunk.mapping_method = method
    chunk.mapping_confidence = confidence

    # book_number 결정
    if book_ranges:
        for bn, (start, end) in book_ranges.items():
            if start <= unit.section_unit_number <= end:
                chunk.book_number = bn
                break
    elif unit.book_number is not None:
        chunk.book_number = unit.book_number

    if confidence < config.low_confidence_threshold:
        if "low_confidence" not in chunk.mapping_flags:
            chunk.mapping_flags.append("low_confidence")


def _mark_unmapped(chunk: Chunk, reason: str) -> None:
    """청크를 unmapped로 마킹."""
    chunk.mapping_method = "unmapped"
    chunk.mapping_confidence = 0.0
    if reason not in chunk.mapping_flags:
        chunk.mapping_flags.append(reason)


# =====================
# 섹션 1: 번호 기반 매칭 (preface / appendix_poem)
# =====================


def _map_section_by_number(
    ko_chunks: list[Chunk],
    en_units: list[EnglishUnit],
    book_ranges: dict[int, tuple[int, int]] | None,
    config: MappingConfig,
) -> tuple[list[Chunk], list[int]]:
    """detected_number 기반 직접 매칭. preface / appendix_poem용."""
    en_num_to_unit = {u.section_unit_number: u for u in en_units}
    assigned_nums: set[int] = set()

    for chunk in ko_chunks:
        num = chunk.detected_number or chunk.unit_number
        if num is not None and num in en_num_to_unit:
            unit = en_num_to_unit[num]
            _assign(chunk, unit, "number", 1.0, book_ranges, config)
            assigned_nums.add(num)
        else:
            _mark_unmapped(chunk, "no_number_match")

    missing = sorted(
        u.section_unit_number
        for u in en_units
        if u.section_unit_number not in assigned_nums
    )
    return ko_chunks, missing


# =====================
# 섹션 2: Anchor + DP (main_body)
# =====================


def _anchor_map_main_body(
    ko_chunks: list[Chunk],
    en_units: list[EnglishUnit],
    embedder: MultilingualEmbedder,
    config: MappingConfig,
    book_ranges: dict[int, tuple[int, int]] | None,
) -> tuple[list[Chunk], list[int]]:
    """본편을 anchor 기반으로 매핑.

    Pass 1: detected_number 직접 매칭 (hard anchor)
    Pass 2: 번호 없는 청크들을 인접 anchor 사이 gap에서 DP 정렬
    """
    en_by_number = {u.section_unit_number: u for u in en_units}
    used_en_numbers: set[int] = set()
    max_en = max(en_by_number.keys()) if en_by_number else 0

    # ============================
    # Pass 1: Hard anchor (detected_number 직접 매칭)
    # ============================
    console.log("  [cyan]Pass 1: Direct number matching...[/cyan]")
    direct_count = 0
    duplicate_count = 0

    for chunk in ko_chunks:
        if chunk.detected_number is None:
            continue
        num = chunk.detected_number
        if num not in en_by_number:
            # 번호가 영어 측에 없음 (out of range)
            continue
        if num in used_en_numbers:
            # 중복 (드물지만 가능): 첫 청크가 우선
            duplicate_count += 1
            continue

        _assign(chunk, en_by_number[num], "number", 1.0, book_ranges, config)
        used_en_numbers.add(num)
        direct_count += 1

    console.log(
        f"    Direct matches: {direct_count}"
        + (f", duplicates skipped: {duplicate_count}" if duplicate_count else "")
    )

    # ============================
    # Pass 2: Gap alignment for unnumbered chunks
    # ============================
    console.log("  [cyan]Pass 2: Gap alignment for unnumbered chunks...[/cyan]")
    n = len(ko_chunks)
    i = 0
    gap_count = 0
    embed_match_count = 0
    unmapped_count = 0

    while i < n:
        # 이미 할당된 청크는 skip
        if ko_chunks[i].mapping_method == "number":
            i += 1
            continue

        # 미할당 청크의 연속 구간 찾기
        j = i
        while j < n and ko_chunks[j].mapping_method != "number":
            j += 1
        # ko_chunks[i:j]가 미할당 그룹

        # 직전 anchor (i 직전의 마지막 number-mapped 청크)
        prev_num = 0
        for k in range(i - 1, -1, -1):
            if ko_chunks[k].mapping_method == "number":
                prev_num = ko_chunks[k].unit_number or 0
                break

        # 다음 anchor (j 위치 또는 그 이후의 첫 number-mapped 청크)
        next_num = max_en + 1
        for k in range(j, n):
            if ko_chunks[k].mapping_method == "number":
                next_num = ko_chunks[k].unit_number or (max_en + 1)
                break

        # 후보 영어 unit: (prev_num, next_num) 범위에서 아직 안 쓰인 것
        candidate_nums = [
            num
            for num in range(prev_num + 1, next_num)
            if num in en_by_number and num not in used_en_numbers
        ]
        candidates = [en_by_number[num] for num in candidate_nums]

        gap_chunks = ko_chunks[i:j]
        gap_count += 1

        # DP 정렬
        embed_n, unmap_n = _align_gap_with_dp(
            gap_chunks=gap_chunks,
            candidates=candidates,
            embedder=embedder,
            book_ranges=book_ranges,
            config=config,
            used_en_numbers=used_en_numbers,
        )
        embed_match_count += embed_n
        unmapped_count += unmap_n

        i = j

    console.log(
        f"    Gap regions: {gap_count}, "
        f"embedding-matched: {embed_match_count}, "
        f"unmapped: {unmapped_count}"
    )

    # 누락 영어 unit
    missing = sorted(
        num for num in en_by_number if num not in used_en_numbers
    )
    return ko_chunks, missing


def _align_gap_with_dp(
    gap_chunks: list[Chunk],
    candidates: list[EnglishUnit],
    embedder: MultilingualEmbedder,
    book_ranges: dict[int, tuple[int, int]] | None,
    config: MappingConfig,
    used_en_numbers: set[int],
) -> tuple[int, int]:
    """Gap 내 미할당 청크들을 후보 영어 units에 monotonic DP로 정렬.

    DP 상태:
        dp[i][j] = chunks[i:]와 candidates[j:]를 사용한 최대 총 유사도
    전이:
        - skip_chunk: dp[i+1][j] (청크 i를 unmapped 처리)
        - skip_cand:  dp[i][j+1] (후보 j를 미사용 처리)
        - assign:     sims[i][j] + dp[i+1][j+1]

    Returns:
        (할당된 청크 수, unmapped 청크 수)
    """
    n = len(gap_chunks)
    m = len(candidates)

    if n == 0:
        return 0, 0

    if m == 0:
        # 후보 없음: 모두 unmapped
        for chunk in gap_chunks:
            _mark_unmapped(chunk, "no_candidate")
        return 0, n

    # 임베딩 계산
    ko_texts = [c.text_ko_raw for c in gap_chunks]
    en_texts = [u.text for u in candidates]

    ko_embs = embedder.embed_queries(ko_texts, show_progress=False)
    en_embs = embedder.embed_passages(en_texts, show_progress=False)
    sims = embedder.cosine_similarity(ko_embs, en_embs)
    # shape: (n, m) torch tensor

    # DP table
    dp = [[0.0] * (m + 1) for _ in range(n + 1)]
    choice = [[""] * (m + 1) for _ in range(n + 1)]

    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            # Option A: skip chunk i
            skip_chunk = dp[i + 1][j]
            # Option B: skip candidate j
            skip_cand = dp[i][j + 1]
            # Option C: assign chunk i to candidate j
            sim_val = float(sims[i][j].item())
            assign_val = sim_val + dp[i + 1][j + 1]

            # 최대 선택
            if assign_val >= skip_chunk and assign_val >= skip_cand:
                dp[i][j] = assign_val
                choice[i][j] = "assign"
            elif skip_chunk >= skip_cand:
                dp[i][j] = skip_chunk
                choice[i][j] = "skip_chunk"
            else:
                dp[i][j] = skip_cand
                choice[i][j] = "skip_cand"

    # Backtrace
    assigned_count = 0
    i, j = 0, 0
    while i < n and j < m:
        ch = choice[i][j]
        if ch == "assign":
            chunk = gap_chunks[i]
            unit = candidates[j]
            sim = float(sims[i][j].item())

            if sim < config.min_embedding_score:
                _mark_unmapped(chunk, "low_embedding_score")
            else:
                _assign(
                    chunk,
                    unit,
                    "embedding_anchored",
                    sim,
                    book_ranges,
                    config,
                )
                used_en_numbers.add(unit.section_unit_number)
                assigned_count += 1

            i += 1
            j += 1
        elif ch == "skip_chunk":
            i += 1
        else:  # skip_cand
            j += 1

    # 남은 미할당 청크 처리
    unmapped_count = 0
    while i < n:
        chunk = gap_chunks[i]
        if chunk.mapping_method != "embedding_anchored":
            _mark_unmapped(chunk, "over_segmented")
            unmapped_count += 1
        i += 1

    # n 안의 unmapped 청크 카운트
    for chunk in gap_chunks:
        if chunk.mapping_method == "unmapped":
            unmapped_count += 1

    # 위에서 더한 unmapped는 backtrace 후 남은 i부터 n까지의 것뿐이라 중복 카운트 가능
    # 정확히 하려면 별도 추적 — 여기선 단순화
    actual_unmapped = sum(1 for c in gap_chunks if c.mapping_method == "unmapped")

    return assigned_count, actual_unmapped


# =====================
# 메인 진입점
# =====================


def map_chunks_to_english(
    ko_chunks: list[Chunk],
    en_units: list[EnglishUnit],
    embedder: MultilingualEmbedder,
    config: MappingConfig | None = None,
    book_ranges: dict[int, tuple[int, int]] | None = None,
) -> MappingResult:
    """한국어 청크 전체를 영어 유닛에 매핑.

    - preface / appendix_poem: 번호 직접 매칭
    - aphorism (본편): anchor + DP gap alignment
    """
    if config is None:
        config = MappingConfig()

    result = MappingResult()

    for ko_section, en_section in KO_TO_EN_SECTION.items():
        section_ko = [c for c in ko_chunks if c.section_type == ko_section]
        section_en = _filter_en_units_by_section(en_units, en_section)

        if not section_ko:
            continue
        if not section_en:
            console.log(
                f"[yellow]No English units for {en_section}, "
                f"{len(section_ko)} Korean chunks unmapped[/yellow]"
            )
            for chunk in section_ko:
                _mark_unmapped(chunk, "no_english_section")
                result.chunks.append(chunk)
            continue

        console.log(
            f"\n[bold cyan]Section:[/bold cyan] {ko_section} → {en_section}"
        )
        console.log(
            f"  Korean chunks: {len(section_ko)}, "
            f"English units: {len(section_en)}"
        )

        if ko_section in ("preface", "appendix_poem"):
            mapped, missing = _map_section_by_number(
                section_ko, section_en, book_ranges, config
            )
            result.chunks.extend(mapped)
            result.missing_en_numbers[ko_section] = missing
            mapped_count = sum(
                1 for c in mapped if c.mapping_method == "number"
            )
            console.log(
                f"  [green]Mapped by number:[/green] {mapped_count}"
            )
            console.log(f"  [yellow]Missing:[/yellow] {len(missing)}")

        elif ko_section == "aphorism":
            mapped, missing = _anchor_map_main_body(
                ko_chunks=section_ko,
                en_units=section_en,
                embedder=embedder,
                config=config,
                book_ranges=book_ranges,
            )
            result.chunks.extend(mapped)
            result.missing_en_numbers[ko_section] = missing

            num_count = sum(1 for c in mapped if c.mapping_method == "number")
            emb_count = sum(
                1 for c in mapped if c.mapping_method == "embedding_anchored"
            )
            unmap_count = sum(
                1 for c in mapped if c.mapping_method == "unmapped"
            )
            console.log(
                f"  [green]Number-matched:[/green] {num_count}, "
                f"[green]Embedding-anchored:[/green] {emb_count}, "
                f"[red]Unmapped:[/red] {unmap_count}"
            )
            console.log(f"  [yellow]Missing English units:[/yellow] {len(missing)}")

    return result
