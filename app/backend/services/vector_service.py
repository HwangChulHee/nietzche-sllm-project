"""
vector_service.py — Qdrant 기반 RAG 컨텍스트 검색.

동작:
  - Qdrant 컬렉션이 없거나 데이터가 없으면 빈 리스트 반환 (graceful degradation)
  - 컬렉션이 있으면 쿼리를 임베딩하여 코사인 유사도 검색
  - sentence-transformers가 설치되지 않았으면 빈 리스트 반환
"""

import asyncio
import logging
from core.config import settings

logger = logging.getLogger(__name__)

COLLECTION_NAME = "nietzsche_quotes"
VECTOR_DIM = 384  # paraphrase-multilingual-MiniLM-L12-v2 출력 차원

# ───────────────────────────────────────────────────────
# 싱글턴 — 모듈 로드 시 1회만 초기화
# ───────────────────────────────────────────────────────

_model = None   # SentenceTransformer
_qdrant = None  # AsyncQdrantClient


def _get_model():
    """SentenceTransformer 싱글턴 — 첫 호출 시 1회 로드."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(settings.EMBEDDING_MODEL)
    return _model


def _get_qdrant():
    """Qdrant 클라이언트 싱글턴 — 첫 호출 시 1회 생성."""
    global _qdrant
    if _qdrant is None:
        from qdrant_client import AsyncQdrantClient
        _qdrant = AsyncQdrantClient(url=settings.QDRANT_URL)
    return _qdrant


async def search_context(query: str, top_k: int = 3) -> list[str]:
    """
    쿼리와 유사한 니체 어록을 Qdrant에서 검색.
    데이터가 없거나 오류 발생 시 빈 리스트 반환.
    """
    try:
        client = _get_qdrant()

        # 컬렉션 존재 확인
        collections = await client.get_collections()
        collection_names = {c.name for c in collections.collections}

        if COLLECTION_NAME not in collection_names:
            logger.info("Qdrant 컬렉션 '%s' 없음 — 빈 컨텍스트 반환", COLLECTION_NAME)
            return []

        # 임베딩 생성
        query_vector = await _embed(query)
        if query_vector is None:
            return []

        # 유사도 검색
        results = await client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_vector,
            limit=top_k,
            with_payload=True,
        )

        return [
            hit.payload.get("text", "")
            for hit in results
            if hit.payload and hit.payload.get("text")
        ]

    except Exception as e:
        logger.warning("Qdrant 검색 실패 — 빈 컨텍스트 반환: %s", e)
        return []


async def _embed(text: str) -> list[float] | None:
    """텍스트를 벡터로 변환. sentence-transformers 미설치 시 None 반환."""
    try:
        loop = asyncio.get_event_loop()
        model = _get_model()
        vector = await loop.run_in_executor(None, model.encode, text)
        return vector.tolist()
    except ImportError:
        logger.warning("sentence-transformers 미설치 — 벡터 검색 불가")
        return None
    except Exception as e:
        logger.warning("임베딩 실패: %s", e)
        return None
