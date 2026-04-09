"""Stage A — Dedup: score-aware, A 중심.

입력: v2_data/sft_candidates/scored.jsonl
출력: v2_data/sft_candidates/deduped.jsonl
     v2_data/sft_candidates/dedup_report.json

규칙:
- A(assistant) 임베딩 cosine ≥ 0.93              → 제거 (모드 붕괴 차단)
- Q(user) cosine ≥ 0.92 AND A cosine ≥ 0.85     → 제거 (완전 중복)
- MinHash로 표면 거의 같은 것 사전 제거 (둘 다 ≥ 0.85)
- 페어 중 점수 낮은 것 제거 (동점이면 뒤 인덱스)
"""
import json
import re
import time
from collections import Counter
from pathlib import Path

import numpy as np
import torch
from datasketch import MinHash, MinHashLSH
from transformers import AutoTokenizer, AutoModel

INPUT = Path("v2_data/sft_candidates/scored.jsonl")
OUTPUT = Path("v2_data/sft_candidates/deduped.jsonl")
REPORT = Path("v2_data/sft_candidates/dedup_report.json")

# MinHash 설정 (사전 거친 dedup)
MINHASH_NGRAM = 5
MINHASH_NUM_PERM = 128
MINHASH_THRESHOLD = 0.85  # user/assistant 둘 다 이 이상이면 표면 거의 같음

# Embedding 설정
EMBED_MODEL = "BAAI/bge-m3"
EMBED_BATCH = 32
EMBED_MAX_LEN = 512

# 의미 dedup 임계값
ASSIST_HARD_THRESHOLD = 0.93   # A 단독 임계값 — 모드 붕괴 차단
QA_BOTH_Q_THRESHOLD = 0.92     # Q+A 동시 검사 시 Q 임계값
QA_BOTH_A_THRESHOLD = 0.85     # Q+A 동시 검사 시 A 임계값


def strip_md(text):
    text = re.sub(r'\*+([^*]+)\*+', r'\1', text)
    text = re.sub(r'_+([^_]+)_+', r'\1', text)
    return text.strip()


def get_user(s):
    for m in s["messages"]:
        if m["role"] == "user":
            return strip_md(m["content"])
    return ""


def get_assistant(s):
    for m in s["messages"]:
        if m["role"] == "assistant":
            return strip_md(m["content"])
    return ""


# ════════════════════════════════════════════════════════════════════
# 점수 비교 (낮은 거 버림)
# ════════════════════════════════════════════════════════════════════

def loser(samples, i, j):
    """페어 (i, j) 중 버릴 인덱스 반환. 점수 낮은 거. 동점이면 뒤(j)."""
    si = samples[i].get("normalized_score", 0)
    sj = samples[j].get("normalized_score", 0)
    if si < sj:
        return i
    if sj < si:
        return j
    return j  # 동점 → 뒤 버림


# ════════════════════════════════════════════════════════════════════
# MinHash (표면 거의 같은 것)
# ════════════════════════════════════════════════════════════════════

def make_minhash(text, n=MINHASH_NGRAM, num_perm=MINHASH_NUM_PERM):
    m = MinHash(num_perm=num_perm)
    text = re.sub(r'\s+', '', text)
    if len(text) < n:
        if text:
            m.update(text.encode('utf-8'))
        return m
    for i in range(len(text) - n + 1):
        m.update(text[i:i+n].encode('utf-8'))
    return m


def minhash_dedup_both(samples):
    """user와 assistant 둘 다 표면 ≥ 0.85 일치 = 거의 같은 샘플 → 제거.
    
    점수 낮은 거 버림.
    """
    print(f"\n[MinHash dedup] threshold={MINHASH_THRESHOLD} (Q AND A)")
    
    # user/assistant MinHash 둘 다 만들기
    user_mh = {}
    assist_mh = {}
    for i, s in enumerate(samples):
        u, a = get_user(s), get_assistant(s)
        if u:
            user_mh[i] = make_minhash(u)
        if a:
            assist_mh[i] = make_minhash(a)
    
    # user 기준 LSH로 candidate 찾기
    lsh = MinHashLSH(threshold=MINHASH_THRESHOLD, num_perm=MINHASH_NUM_PERM)
    for i, mh in user_mh.items():
        lsh.insert(str(i), mh)
    
    to_remove = set()
    for i in sorted(user_mh.keys()):
        if i in to_remove:
            continue
        candidates = [int(x) for x in lsh.query(user_mh[i])]
        for j in candidates:
            if j == i or j in to_remove:
                continue
            # 양쪽 다 ≥ 임계값?
            if i not in assist_mh or j not in assist_mh:
                continue
            a_jaccard = assist_mh[i].jaccard(assist_mh[j])
            if a_jaccard >= MINHASH_THRESHOLD:
                # 둘 다 표면 거의 같음 → 점수 낮은 거 버림
                to_remove.add(loser(samples, i, j))
    
    print(f"  제거: {len(to_remove)}개")
    return to_remove


# ════════════════════════════════════════════════════════════════════
# Embedding (의미)
# ════════════════════════════════════════════════════════════════════

def load_embed_model():
    print(f"\n[Embedding] {EMBED_MODEL} 로딩...")
    tok = AutoTokenizer.from_pretrained(EMBED_MODEL)
    model = AutoModel.from_pretrained(EMBED_MODEL).cuda().eval()
    print("  완료")
    return tok, model


@torch.no_grad()
def embed_texts(tok, model, texts, label=""):
    all_embs = []
    n = len(texts)
    print(f"  {label} {n}개 임베딩 중...", end="", flush=True)
    start = time.time()
    
    for i in range(0, n, EMBED_BATCH):
        batch = texts[i:i+EMBED_BATCH]
        inputs = tok(batch, padding=True, truncation=True,
                     max_length=EMBED_MAX_LEN, return_tensors="pt").to("cuda")
        outputs = model(**inputs)
        embs = outputs.last_hidden_state[:, 0]  # CLS pooling
        embs = torch.nn.functional.normalize(embs, p=2, dim=1)
        all_embs.append(embs.cpu().numpy())
        
        done = min(i + EMBED_BATCH, n)
        elapsed = time.time() - start
        rate = done / elapsed if elapsed > 0 else 0
        eta = (n - done) / rate if rate > 0 else 0
        print(f"\r  {label} {done}/{n} ({rate:.0f}/s, ETA {eta:.0f}s)", end="", flush=True)
    print()
    return np.concatenate(all_embs)


def embed_dedup_aware(samples, tok, model):
    """A 중심 의미 dedup. 점수 낮은 거 버림.
    
    제거 조건:
    1. A cosine ≥ 0.93                       (모드 붕괴)
    2. Q cosine ≥ 0.92 AND A cosine ≥ 0.85   (완전 중복)
    """
    print(f"\n[Embedding dedup]")
    print(f"  Rule 1: A ≥ {ASSIST_HARD_THRESHOLD}")
    print(f"  Rule 2: Q ≥ {QA_BOTH_Q_THRESHOLD} AND A ≥ {QA_BOTH_A_THRESHOLD}")
    
    # 모든 user/assistant 텍스트 모으기
    user_texts = [get_user(s) for s in samples]
    assist_texts = [get_assistant(s) for s in samples]
    
    # 빈 텍스트는 패딩 (0 벡터로)
    user_texts_filled = [t if t else " " for t in user_texts]
    assist_texts_filled = [t if t else " " for t in assist_texts]
    
    user_embs = embed_texts(tok, model, user_texts_filled, label="user")
    assist_embs = embed_texts(tok, model, assist_texts_filled, label="assist")
    
    n = len(samples)
    to_remove = set()
    rule1_count = 0
    rule2_count = 0
    
    print(f"  유사도 비교 중...")
    chunk_size = 256
    for start_i in range(0, n, chunk_size):
        end_i = min(start_i + chunk_size, n)
        a_sims = assist_embs[start_i:end_i] @ assist_embs.T  # (chunk, n)
        u_sims = user_embs[start_i:end_i] @ user_embs.T
        
        for local_i in range(end_i - start_i):
            i = start_i + local_i
            if i in to_remove:
                continue
            for j in range(i + 1, n):
                if j in to_remove:
                    continue
                a_sim = a_sims[local_i, j]
                
                # Rule 1: A 단독 임계값
                if a_sim >= ASSIST_HARD_THRESHOLD:
                    to_remove.add(loser(samples, i, j))
                    rule1_count += 1
                    continue
                
                # Rule 2: Q + A 동시
                if a_sim >= QA_BOTH_A_THRESHOLD:
                    u_sim = u_sims[local_i, j]
                    if u_sim >= QA_BOTH_Q_THRESHOLD:
                        to_remove.add(loser(samples, i, j))
                        rule2_count += 1
    
    print(f"  Rule 1 제거: {rule1_count}")
    print(f"  Rule 2 제거: {rule2_count}")
    print(f"  총 제거: {len(to_remove)}")
    return to_remove, rule1_count, rule2_count


# ════════════════════════════════════════════════════════════════════
# Main
# ════════════════════════════════════════════════════════════════════

def main():
    samples = [json.loads(l) for l in INPUT.open(encoding="utf-8")]
    print(f"입력 샘플: {len(samples)}")
    
    # 점수 통계
    grades = Counter(s.get("grade", "F") for s in samples)
    print(f"입력 등급: {dict(grades)}")
    
    # ────────────────────────────
    # 1. MinHash dedup (Q AND A 둘 다 표면 거의 같은 것)
    # ────────────────────────────
    minhash_remove = minhash_dedup_both(samples)
    after_minhash = [s for i, s in enumerate(samples) if i not in minhash_remove]
    print(f"\nMinHash 후: {len(after_minhash)}")
    
    # ────────────────────────────
    # 2. Embedding dedup (의미, A 중심, score-aware)
    # ────────────────────────────
    tok, model = load_embed_model()
    embed_remove_local, rule1, rule2 = embed_dedup_aware(after_minhash, tok, model)
    final = [s for i, s in enumerate(after_minhash) if i not in embed_remove_local]
    print(f"\nEmbedding 후: {len(final)}")
    
    # ────────────────────────────
    # 출력
    # ────────────────────────────
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8") as f:
        for s in final:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    
    final_grades = Counter(s.get("grade", "F") for s in final)
    final_avg = sum(s.get("normalized_score", 0) for s in final) / max(len(final), 1)
    
    print(f"\n{'='*60}")
    print("  Dedup 결과 (score-aware)")
    print(f"{'='*60}")
    print(f"입력:           {len(samples)}")
    print(f"MinHash 제거:   {len(minhash_remove)} (Q AND A ≥ {MINHASH_THRESHOLD})")
    print(f"Embedding 제거: {len(embed_remove_local)}")
    print(f"  Rule 1 (A ≥ {ASSIST_HARD_THRESHOLD}):                   {rule1}")
    print(f"  Rule 2 (Q ≥ {QA_BOTH_Q_THRESHOLD} AND A ≥ {QA_BOTH_A_THRESHOLD}):   {rule2}")
    print(f"최종:           {len(final)} ({len(final)/len(samples)*100:.1f}%)")
    print()
    print(f"최종 평균 점수: {final_avg:.3f}")
    print(f"최종 등급: {dict(final_grades)}")
    print(f"\n출력: {OUTPUT}")
    
    REPORT.write_text(json.dumps({
        "input": len(samples),
        "minhash_removed": len(minhash_remove),
        "embed_removed_total": len(embed_remove_local),
        "embed_rule1_a_hard": rule1,
        "embed_rule2_q_and_a": rule2,
        "final": len(final),
        "final_avg_score": final_avg,
        "final_grades": dict(final_grades),
        "input_grades": dict(grades),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"리포트: {REPORT}")


if __name__ == "__main__":
    main()