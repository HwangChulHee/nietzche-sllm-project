"""TSZ corpus 검색 테스트 (원전/풀이 통합) - Dense / Sparse / Hybrid 비교"""
from pathlib import Path

from FlagEmbedding import BGEM3FlagModel
from qdrant_client import QdrantClient
from qdrant_client.models import SparseVector, Prefetch, FusionQuery, Fusion

RAG_DIR = Path(__file__).resolve().parent.parent
QDRANT_PATH = RAG_DIR / "qdrant_storage"
COLLECTION = "tsz_corpus"
TOP_K = 5

QUERIES = [
    "차라투스트라는 왜 산에서 내려와?",
    "독수리와 뱀은 뭘 의미해?",
    "성자는 누구야?",
    "위버멘쉬가 뭐야?",
    "신은 죽었다는 게 무슨 뜻이야?",
]


def fmt_hit(hit) -> str:
    p = hit.payload
    tag = "[원전]" if p["source_type"] == "original" else "[풀이]"
    txt = p["text_ko"][:55].replace("\n", " ")
    return f"  [{hit.score:.3f}] {tag} {p['id']:30} | {txt}..."


def main():
    print("Loading BGE-M3...")
    model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=True)

    client = QdrantClient(path=str(QDRANT_PATH))
    info = client.get_collection(COLLECTION)
    print(f"Collection: {COLLECTION} ({info.points_count} points)\n")

    for q in QUERIES:
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"Query: {q}")

        enc = model.encode([q], return_dense=True, return_sparse=True)
        dense_vec = enc["dense_vecs"][0].tolist()
        sw = enc["lexical_weights"][0]
        sparse_vec = SparseVector(
            indices=[int(k) for k in sw.keys()],
            values=[float(v) for v in sw.values()],
        )

        print("\n[Dense]")
        for h in client.query_points(
            collection_name=COLLECTION, query=dense_vec, using="dense",
            limit=TOP_K, with_payload=True,
        ).points:
            print(fmt_hit(h))

        print("\n[Sparse]")
        for h in client.query_points(
            collection_name=COLLECTION, query=sparse_vec, using="sparse",
            limit=TOP_K, with_payload=True,
        ).points:
            print(fmt_hit(h))

        print("\n[Hybrid (RRF)]")
        for h in client.query_points(
            collection_name=COLLECTION,
            prefetch=[
                Prefetch(query=dense_vec, using="dense", limit=TOP_K * 2),
                Prefetch(query=sparse_vec, using="sparse", limit=TOP_K * 2),
            ],
            query=FusionQuery(fusion=Fusion.RRF),
            limit=TOP_K, with_payload=True,
        ).points:
            print(fmt_hit(h))

        print()


if __name__ == "__main__":
    main()