"""
pymupdf 기반 PDF 텍스트 추출기.

페이지 단위로 블록(block)을 추출하고 bbox 좌표를 함께 보관한다.
노이즈 필터링은 별도 모듈(noise_filter.py)에서 수행한다.
"""

from pathlib import Path

import fitz  # pymupdf
from rich.console import Console

from data_pipeline.schema import ExtractedPage, TextBlock

console = Console()


class PDFExtractor:
    """pymupdf를 사용한 PDF 블록 추출기.

    Usage:
        extractor = PDFExtractor("path/to/book.pdf")
        pages = extractor.extract_all()
        # 또는
        page = extractor.extract_page(0)
    """

    def __init__(self, pdf_path: str | Path):
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {self.pdf_path}")

        self.doc = fitz.open(self.pdf_path)
        console.log(
            f"[green]PDF loaded:[/green] {self.pdf_path.name} "
            f"({self.doc.page_count} pages)"
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        """명시적으로 PDF 파일을 닫는다."""
        if self.doc is not None:
            self.doc.close()
            self.doc = None

    def extract_page(self, page_num: int) -> ExtractedPage:
        """단일 페이지에서 블록을 추출한다.

        Args:
            page_num: 0-indexed 페이지 번호

        Returns:
            블록 리스트와 페이지 메타데이터를 담은 ExtractedPage
        """
        if page_num < 0 or page_num >= self.doc.page_count:
            raise IndexError(
                f"page_num {page_num} out of range [0, {self.doc.page_count})"
            )

        page = self.doc[page_num]

        # pymupdf의 get_text("blocks") 반환 형식:
        # list of (x0, y0, x1, y1, "text", block_no, block_type)
        # block_type: 0 = text, 1 = image
        raw_blocks = page.get_text("blocks")

        blocks: list[TextBlock] = []
        for raw in raw_blocks:
            x0, y0, x1, y1, text, block_no, block_type = raw

            # 이미지 블록은 건너뛴다
            if block_type != 0:
                continue

            # 빈 텍스트 블록 제거
            text = text.strip()
            if not text:
                continue

            blocks.append(
                TextBlock(
                    page_num=page_num,
                    block_num=block_no,
                    bbox=(x0, y0, x1, y1),
                    text=text,
                )
            )

        return ExtractedPage(
            page_num=page_num,
            page_width=page.rect.width,
            page_height=page.rect.height,
            blocks=blocks,
        )

    def extract_all(self) -> list[ExtractedPage]:
        """모든 페이지에서 블록을 추출한다."""
        pages: list[ExtractedPage] = []
        for i in range(self.doc.page_count):
            pages.append(self.extract_page(i))
        console.log(f"[green]Extracted[/green] {len(pages)} pages")
        return pages