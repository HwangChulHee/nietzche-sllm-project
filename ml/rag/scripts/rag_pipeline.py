"""RAG 파이프라인 PoC: RAG ON/OFF 비교
실행: python ml/rag/scripts/rag_pipeline.py
"""
import json
from pathlib import Path

import requests
from FlagEmbedding import BGEM3FlagModel
from qdrant_client import QdrantClient
from qdrant_client.models import SparseVector, Prefetch, FusionQuery, Fusion

RAG_DIR = Path(__file__).resolve().parent.parent
QDRANT_PATH = RAG_DIR / "qdrant_storage"
COLLECTION = "tsz_corpus"

VLLM_URL = "http://localhost:8000/v1/chat/completions"
MODEL_NAME = "google/gemma-4-E2B-it"
TOP_K = 5

QUERIES = [
    "위버멘쉬가 뭐야?",
    "독수리와 뱀은 뭘 의미해?",
    "신은 죽었다는 게 무슨 뜻이야?",
]

# RAG ON 시스템 프롬프트
SYSTEM_PROMPT_RAG = """당신은 니체의 『차라투스트라는 이렇게 말했다』를 학습자에게 풀어 설명하는 해설자입니다.

주어진 자료(원전 인용과 풀이)를 바탕으로 학습자의 질문에 답하세요.

원칙:
- 자료에 없는 내용은 추측하지 마세요.
- 원전 인용은 그 출처를 밝히고, 풀이는 풀어 설명하세요.
- 교양 독자 대상으로 명확한 현대 한국어로 답하세요.
- 답변은 2~4문단으로 간결하게."""

# RAG OFF 시스템 프롬프트 (참고 자료 없이 자기 지식만)
SYSTEM_PROMPT_NORAG = """당신은 니체의 『차라투스트라는 이렇게 말했다』를 학습자에게 풀어 설명하는 해설자입니다.

학습자의 질문에 답하세요.

원칙:
- 교양 독자 대상으로 명확한 현대 한국어로 답하세요.
- 답변은 2~4문단으로 간결하게."""


def search(model, client, query: str):
    enc = model.encode([query], return_dense=True, return_sparse=True)
    dense_vec = enc["dense_vecs"][0].tolist()
    sw = enc["lexical_weights"][0]
    sparse_vec = SparseVector(
        indices=[int(k) for k in sw.keys()],
        values=[float(v) for v in sw.values()],
    )
    hits = client.query_points(
        collection_name=COLLECTION,
        prefetch=[
            Prefetch(query=dense_vec, using="dense", limit=TOP_K * 2),
            Prefetch(query=sparse_vec, using="sparse", limit=TOP_K * 2),
        ],
        query=FusionQuery(fusion=Fusion.RRF),
        limit=TOP_K,
        with_payload=True,
    ).points
    return hits


def build_context(hits) -> str:
    lines = []
    for h in hits:
        p = h.payload
        tag = "원전" if p["source_type"] == "original" else "풀이"
        section = p.get("section", "")
        section_str = f" ({section})" if section else ""
        lines.append(f"[{tag}{section_str}]\n{p['text_ko']}")
    return "\n\n".join(lines)


def generate_with_rag(query: str, context: str) -> str:
    user_prompt = f"""[참고 자료]
{context}

[학습자 질문]
{query}

위 자료를 바탕으로 학습자에게 풀어 설명해주세요."""

    response = requests.post(
        VLLM_URL,
        json={
            "model": MODEL_NAME,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT_RAG},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": 600,
            "temperature": 0.3,
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def generate_without_rag(query: str) -> str:
    """RAG 없이 LLM 자체 지식으로만 답변"""
    response = requests.post(
        VLLM_URL,
        json={
            "model": MODEL_NAME,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT_NORAG},
                {"role": "user", "content": query},
            ],
            "max_tokens": 600,
            "temperature": 0.3,
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def main():
    print("Loading BGE-M3...")
    model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=True)
    client = QdrantClient(path=str(QDRANT_PATH))
    info = client.get_collection(COLLECTION)
    print(f"Collection: {COLLECTION} ({info.points_count} points)\n")

    for q in QUERIES:
        print("=" * 70)
        print(f"Q: {q}")
        print("=" * 70)

        # 1. RAG OFF (먼저, 비교 기준점)
        print("\n" + "─" * 30 + " [RAG OFF] " + "─" * 30)
        try:
            answer_norag = generate_without_rag(q)
            print(answer_norag)
        except Exception as e:
            print(f"Error: {e}")

        # 2. RAG ON
        print("\n" + "─" * 30 + " [RAG ON] " + "─" * 31)
        hits = search(model, client, q)
        print(f"회수된 청크 {len(hits)}개:")
        for h in hits:
            p = h.payload
            tag = "원전" if p["source_type"] == "original" else "풀이"
            print(f"  [{h.score:.3f}] [{tag}] {p['id']}")
        print()

        context = build_context(hits)
        try:
            answer_rag = generate_with_rag(q, context)
            print(answer_rag)
        except Exception as e:
            print(f"Error: {e}")

        print()


if __name__ == "__main__":
    main()