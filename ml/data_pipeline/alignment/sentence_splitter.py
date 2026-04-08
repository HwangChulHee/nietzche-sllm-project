"""
문장 분할기 추상화.

SentenceSplitter Protocol을 정의하고, 한국어/영어 구현을 제공한다.

재사용성:
- Protocol 기반이라 언어별 구현을 쉽게 추가 가능
- 한국어: KSS (punct 백엔드)
- 영어: pysbd (정확도 높음, 가벼움)
"""

from __future__ import annotations

from typing import Protocol

from rich.console import Console

console = Console()


class SentenceSplitter(Protocol):
    """문장 분할기 인터페이스."""

    def split(self, text: str) -> list[str]:
        """텍스트를 문장 단위로 분할."""
        ...


# =====================
# 한국어
# =====================


class KoreanSentenceSplitter:
    """KSS 기반 한국어 문장 분할기.

    KSS 6.x 백엔드 옵션:
    - "auto": 가능하면 mecab, 아니면 pecab
    - "mecab": C++ mecab 필요
    - "pecab": 순수 파이썬, 느림
    - "punct": 구두점 기반, 빠름 + 외부 의존성 없음
    - "fast": 가장 빠름, 정확도 낮음

    기본값 "punct" — 외부 의존성 없고 충분히 빠르고 정확.
    """

    def __init__(self, backend: str = "punct", num_workers: int = 1):
        try:
            import kss  # noqa: F401
        except ImportError as e:
            raise ImportError("KSS not installed. Run: poetry add kss") from e

        self.backend = backend
        self.num_workers = num_workers
        console.log(
            f"[cyan]KoreanSentenceSplitter initialized[/cyan] "
            f"(backend={backend}, workers={num_workers})"
        )

    def split(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []

        from kss import split_sentences

        try:
            sentences = split_sentences(
                text,
                backend=self.backend,
                num_workers=self.num_workers,
            )
        except Exception as e:
            console.log(f"[yellow]KSS failed, using fallback: {e}[/yellow]")
            return self._fallback_split(text)

        return [s.strip() for s in sentences if s and s.strip()]

    @staticmethod
    def _fallback_split(text: str) -> list[str]:
        """KSS 실패 시 단순 마침표 기반 분할."""
        import re

        parts = re.split(r"(?<=[.!?。])\s+", text)
        return [p.strip() for p in parts if p and p.strip()]


# =====================
# 영어
# =====================


class EnglishSentenceSplitter:
    """pysbd 기반 영어 문장 분할기.

    pysbd (Python Sentence Boundary Disambiguation):
    - 규칙 기반, 가볍고 정확
    - 약어 처리 우수 (Mr., Dr., e.g. 등)
    - 외부 의존성 최소

    Project Gutenberg 영어에 적합.
    """

    def __init__(self, language: str = "en"):
        try:
            import pysbd  # noqa: F401
        except ImportError as e:
            raise ImportError(
                "pysbd not installed. Run: poetry add pysbd"
            ) from e

        self.language = language
        from pysbd import Segmenter

        self.segmenter = Segmenter(language=language, clean=False)
        console.log(
            f"[cyan]EnglishSentenceSplitter initialized[/cyan] "
            f"(pysbd, language={language})"
        )

    def split(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []

        try:
            sentences = self.segmenter.segment(text)
        except Exception as e:
            console.log(f"[yellow]pysbd failed, using fallback: {e}[/yellow]")
            return self._fallback_split(text)

        return [s.strip() for s in sentences if s and s.strip()]

    @staticmethod
    def _fallback_split(text: str) -> list[str]:
        """pysbd 실패 시 단순 정규식 분할."""
        import re

        pattern = r"(?<=[.!?])\s+(?=[A-Z])|(?<=[.!?])\n+"
        parts = re.split(pattern, text)
        return [p.strip() for p in parts if p and p.strip()]
