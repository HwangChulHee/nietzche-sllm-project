"""
다국어 임베딩 래퍼.

multilingual-e5-large 모델을 기본으로 사용하며, e5 특유의 prefix 처리
('query:' / 'passage:')를 캡슐화한다. 다른 임베딩 모델로 교체 가능하도록
MultilingualEmbedder 클래스로 래핑.

재사용성:
- 책 무관 (joyful_science 전용 로직 없음)
- 한국어/영어/독일어 등 다국어 지원
- 다른 임베딩 모델로 쉽게 교체 가능
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console

if TYPE_CHECKING:
    from torch import Tensor

console = Console()


class MultilingualEmbedder:
    """다국어 임베딩 래퍼.

    e5 모델은 입력 prefix가 필요하다:
    - 검색 query: "query: ..."
    - 검색 대상 (문서): "passage: ..."

    이 클래스는 이 prefix 처리를 자동화한다. 다른 모델 (LaBSE 등)을
    사용할 때는 prefix를 빈 문자열로 두면 된다.
    """

    DEFAULT_MODEL = "intfloat/multilingual-e5-large"

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        query_prefix: str = "query: ",
        passage_prefix: str = "passage: ",
        device: str | None = None,
    ):
        """임베딩 모델 로드.

        Args:
            model_name: HuggingFace 모델 이름
            query_prefix: 검색 query에 붙일 prefix (e5 계열은 "query: ")
            passage_prefix: 검색 대상에 붙일 prefix (e5 계열은 "passage: ")
            device: "cuda" | "cpu" | None (자동)
        """
        # 지연 import: 무거운 의존성이므로 실제 사용 시에만 로드
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name
        self.query_prefix = query_prefix
        self.passage_prefix = passage_prefix

        console.log(f"[cyan]Loading embedding model:[/cyan] {model_name}")
        self.model = SentenceTransformer(model_name, device=device)
        console.log(f"  Device: {self.model.device}")

    def embed_queries(
        self,
        texts: list[str],
        batch_size: int = 32,
        show_progress: bool = False,
    ) -> "Tensor":
        """query 역할 텍스트들을 임베딩.

        Args:
            texts: 임베딩할 텍스트 리스트
            batch_size: 배치 크기
            show_progress: 진행 바 표시 여부

        Returns:
            정규화된 임베딩 텐서 (shape: [N, embedding_dim])
        """
        prefixed = [f"{self.query_prefix}{t}" for t in texts]
        return self.model.encode(
            prefixed,
            batch_size=batch_size,
            convert_to_tensor=True,
            normalize_embeddings=True,
            show_progress_bar=show_progress,
        )

    def embed_passages(
        self,
        texts: list[str],
        batch_size: int = 32,
        show_progress: bool = False,
    ) -> "Tensor":
        """passage 역할 텍스트들을 임베딩.

        Args:
            texts: 임베딩할 텍스트 리스트
            batch_size: 배치 크기
            show_progress: 진행 바 표시 여부

        Returns:
            정규화된 임베딩 텐서 (shape: [N, embedding_dim])
        """
        prefixed = [f"{self.passage_prefix}{t}" for t in texts]
        return self.model.encode(
            prefixed,
            batch_size=batch_size,
            convert_to_tensor=True,
            normalize_embeddings=True,
            show_progress_bar=show_progress,
        )

    @staticmethod
    def cosine_similarity(query_emb: "Tensor", passage_embs: "Tensor") -> "Tensor":
        """정규화된 임베딩 간 코사인 유사도.

        임베딩이 이미 정규화되어 있으므로 단순 내적 = 코사인 유사도.

        Args:
            query_emb: [1, D] 또는 [N, D]
            passage_embs: [M, D]

        Returns:
            유사도 텐서 [N, M] 또는 [1, M]
        """
        from sentence_transformers import util

        return util.cos_sim(query_emb, passage_embs)
