"""TSZ 청크(원전+풀이) → BGE-M3 임베딩 → Qdrant 인덱싱"""
import json
from collections import Counter
from pathlib import Path

from FlagEmbedding import BGEM3FlagModel
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    SparseIndexParams,
    SparseVector,
    SparseVectorParams,
    VectorParams,
)

RAG_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = RAG_DIR / "data"
DATA_FILES = [
    DATA_DIR / "orig_tsz_p1_prologue.jsonl",
    DATA_DIR / "interp_tsz_p1_prologue.jsonl",
]
QDRANT_PATH = RAG_DIR / "qdrant_storage"
COLLECTION = "tsz_corpus"


def main():
    chunks = []
    for f in DATA_FILES:
        loaded = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
        chunks.extend(loaded)
        print(f"Loaded {len(loaded)} chunks from {f.name}")
    counts = Counter(c["source_type"] for c in chunks)
    print(f"Total: {len(chunks)} chunks {dict(counts)}")

    print("\nLoading BGE-M3...")
    model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=True)
    texts = [c["text_ko"] for c in chunks]
    print(f"Encoding {len(texts)} chunks...")
    out = model.encode(texts, return_dense=True, return_sparse=True, batch_size=8)
    dense_vecs = out["dense_vecs"]
    sparse_weights = out["lexical_weights"]
    print(f"  dense shape: {dense_vecs.shape}")

    client = QdrantClient(path=str(QDRANT_PATH))
    if client.collection_exists(COLLECTION):
        client.delete_collection(COLLECTION)
        print(f"\nDeleted existing collection: {COLLECTION}")
    client.create_collection(
        collection_name=COLLECTION,
        vectors_config={"dense": VectorParams(size=1024, distance=Distance.COSINE)},
        sparse_vectors_config={"sparse": SparseVectorParams(index=SparseIndexParams())},
    )
    print(f"Created collection: {COLLECTION}")

    points = []
    for i, (chunk, dvec, swts) in enumerate(zip(chunks, dense_vecs, sparse_weights)):
        points.append(PointStruct(
            id=i,
            vector={
                "dense": dvec.tolist(),
                "sparse": SparseVector(
                    indices=[int(k) for k in swts.keys()],
                    values=[float(v) for v in swts.values()],
                ),
            },
            payload=chunk,
        ))
    client.upsert(collection_name=COLLECTION, points=points)
    print(f"Upserted {len(points)} points")

    info = client.get_collection(COLLECTION)
    print(f"\nCollection: {COLLECTION}")
    print(f"  points_count: {info.points_count}")
    print(f"  status: {info.status}")


if __name__ == "__main__":
    main()