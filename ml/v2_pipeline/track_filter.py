"""3-Track 필터링 (minimal).

LLM 채점은 텍스트만 보고 5축으로 함 (책 정보 주입 없음).
책별 정책은 checker 단계에서만 적용.
"""
import asyncio
import json
import re
import time
from pathlib import Path
from openai import AsyncOpenAI

VLLM_BASE_URL = "http://localhost:8000/v1"
MODEL = "google/gemma-4-26B-A4B-it"
CONCURRENCY = 16
MAX_RETRIES = 3
TEMPERATURE = 0.2

INPUT_DIR = Path("v2_data/reconstructed")
OUTPUT_DIR = Path("v2_data/filtered")


# ════════════════════════════════════════════════════════════════════
# LLM 채점 프롬프트 (텍스트만, 책 정보 없음)
# ════════════════════════════════════════════════════════════════════

SCORING_PROMPT = """당신은 철학 텍스트 청크를 SFT 데이터 생성용으로 평가하는 전문가다.
오직 아래 청크 텍스트만 보고 판단하라. 사전 지식으로 점수를 보정하지 마라.

[청크]
{text}

이 청크를 5개 축으로 1~5점 평가하라.

**Tracks**

- track_existential: 현대인 고민에 응답할 수 있는 통찰을 담고 있는가?
  5 = 명확한 실존적 통찰, 직접 적용 가능
  4 = 강한 함의, 약간의 재해석 필요
  3 = 일부 적용 가능, 우회로 필요
  2 = 적용 가능성 약함
  1 = 적용 불가

- track_philosophical: 개념·입장·논증이 명확한가?
  5 = 핵심 개념의 명시적 전개, 정의·논증 포함
  4 = 개념이 응답의 중심 논리로 작동
  3 = 개념이 부분적으로 작동
  2 = 개념 언급 수준
  1 = 개념 부재

- track_biographical: 화자 자신의 삶·선택·자기평가를 보여주는가?
  5 = 명확한 자전 서술 또는 자기 사상 회고
  4 = 자전적 요소가 청크의 중심
  3 = 자전적 요소가 부수적으로 등장
  2 = 간헐적 1인칭 언급
  1 = 자전 요소 없음

**Common axes**

- self_contained: 청크 단독으로 의미가 통하는가? 외부 맥락 없이 이해 가능한가?
  5 = 완결된 사유 단위
  4 = 거의 자립적, 약간의 외부 맥락
  3 = 일부 맥락 필요
  2 = 외부 맥락 없이 이해 어려움 (예: "더 나아가 ~", "앞에서 본 바와 같이 ~"로 시작하거나, 앞 단락을 받는 지시어가 핵심)
  1 = 단순 연결구·단편

- density: 통찰의 강도가 압축적인가?
  5 = 격언급 압축, 한 문장으로 요약 가능
  4 = 명확한 주장 + 강한 부연
  3 = 명확한 주장 + 부연
  2 = 산만하거나 여러 주장 혼재
  1 = 단순 묘사·일화·연결구

**오직 다음 JSON 형식으로만 응답하라. 다른 설명·서술 금지.**
{{"track_existential": <int>, "track_philosophical": <int>, "track_biographical": <int>, "self_contained": <int>, "density": <int>}}
"""


# ════════════════════════════════════════════════════════════════════
# 책별 통과 조건 (정책은 여기서만)
# ════════════════════════════════════════════════════════════════════

def check_jw(s, chunk):
    A, B = s["track_existential"], s["track_philosophical"]
    sc, den = s["self_contained"], s["density"]
    if (A >= 3 or B >= 3) and sc >= 3 and den >= 2:
        return True, None
    return False, f"JW fail (A={A},B={B},sc={sc},den={den})"


def check_bge(s, chunk):
    B, sc, den = s["track_philosophical"], s["self_contained"], s["density"]
    if B >= 3 and sc >= 3 and den >= 2:
        return True, None
    return False, f"BGE fail (B={B},sc={sc},den={den})"


def check_gm(s, chunk):
    B, sc, den = s["track_philosophical"], s["self_contained"], s["density"]
    if B >= 4 and sc >= 4 and den >= 3:
        return True, None
    return False, f"GM fail (B={B},sc={sc},den={den})"


def check_eh(s, chunk):
    B, C, sc = s["track_philosophical"], s["track_biographical"], s["self_contained"]
    if (C >= 3 or B >= 3) and sc >= 3:
        return True, None
    return False, f"EH fail (B={B},C={C},sc={sc})"


def check_ti(s, chunk):
    A, B = s["track_existential"], s["track_philosophical"]
    sc, den = s["self_contained"], s["density"]
    ch = chunk.get("chapter", 0)

    if ch == 1:    # Maxims and Missiles
        ok = (A >= 3 or B >= 3) and den >= 3
    elif ch == 2:  # The Problem of Socrates
        ok = (A >= 3 or B >= 3) and sc >= 3
    elif ch in (3, 4, 5, 6, 7):  # Reason / True World / Morality / Errors / Improvers
        ok = B >= 3 and sc >= 3
    elif ch == 8:  # Things the Germans Lack
        ok = (A >= 3 or B >= 3) and sc >= 3
    elif ch == 9:  # Skirmishes
        ok = (A >= 3 or B >= 3) and sc >= 3
    elif ch == 10: # What I Owe to the Ancients
        ok = B >= 4 and sc >= 4
    elif ch == 11: # The Hammer Speaketh
        ok = den >= 4
    else:
        ok = False

    if ok:
        return True, None
    return False, f"TI Ch{ch} fail (A={A},B={B},sc={sc},den={den})"


CHECKERS = {
    "JW": check_jw,
    "BGE": check_bge,
    "GM": check_gm,
    "TI": check_ti,
    "EH": check_eh,
}


def determine_use_case(s):
    A = s["track_existential"] >= 3
    B = s["track_philosophical"] >= 3
    C = s["track_biographical"] >= 3

    if A and B and C: return "all"
    if A and B: return "existential+philosophical"
    if B and C: return "philosophical+biographical"
    if A and C: return "existential+biographical"
    if A: return "existential"
    if B: return "philosophical"
    if C: return "biographical"
    return None


# ════════════════════════════════════════════════════════════════════
# LLM 호출
# ════════════════════════════════════════════════════════════════════

JSON_RE = re.compile(r'\{[^{}]*\}', re.DOTALL)
REQUIRED_KEYS = {
    "track_existential", "track_philosophical", "track_biographical",
    "self_contained", "density",
}


async def score_chunk(client, semaphore, chunk):
    text = chunk.get("text_ko_reconstructed") or chunk.get("text_ko") or ""
    if not text.strip():
        return None

    prompt = SCORING_PROMPT.format(text=text)

    async with semaphore:
        for attempt in range(MAX_RETRIES):
            try:
                resp = await client.chat.completions.create(
                    model=MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=TEMPERATURE,
                    max_tokens=150,
                )
                content = resp.choices[0].message.content.strip()
                m = JSON_RE.search(content)
                if not m:
                    raise ValueError(f"JSON 없음: {content[:100]}")

                scores = json.loads(m.group())
                if not REQUIRED_KEYS.issubset(scores):
                    raise ValueError(f"필드 부족: {list(scores.keys())}")

                for k in REQUIRED_KEYS:
                    v = scores[k]
                    if not isinstance(v, int) or not (1 <= v <= 5):
                        raise ValueError(f"{k}={v} 범위 밖")

                return {k: scores[k] for k in REQUIRED_KEYS}
            except Exception:
                if attempt == MAX_RETRIES - 1:
                    return None
                await asyncio.sleep(0.5 * (attempt + 1))


def chunk_key(c):
    return (c.get("essay"), c.get("chapter"), c.get("sub_chapter"),
            c.get("aph_num"), c.get("part"))


# ════════════════════════════════════════════════════════════════════
# 책 단위 처리
# ════════════════════════════════════════════════════════════════════

async def process_book(book_name, input_path, output_path, limit=None):
    print(f"\n{'='*60}\n  {book_name}: {input_path.name}\n{'='*60}")

    if not input_path.exists():
        print(f"❌ 입력 없음: {input_path}")
        return

    chunks = [json.loads(l) for l in input_path.open(encoding="utf-8")]
    print(f"전체 청크: {len(chunks)}")

    already = set()
    if output_path.exists():
        for line in output_path.open(encoding="utf-8"):
            c = json.loads(line)
            already.add(chunk_key(c))
    print(f"이미 처리: {len(already)}")

    todo = [c for c in chunks if chunk_key(c) not in already]
    if limit:
        todo = todo[:limit]
    print(f"이번 처리: {len(todo)}")

    if not todo:
        print("처리할 청크 없음.")
        return

    client = AsyncOpenAI(base_url=VLLM_BASE_URL, api_key="dummy")
    semaphore = asyncio.Semaphore(CONCURRENCY)
    checker = CHECKERS[book_name]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    out_f = output_path.open("a", encoding="utf-8")

    success = failed = passed_count = 0
    start = time.time()

    async def run_one(chunk):
        nonlocal success, failed, passed_count
        scores = await score_chunk(client, semaphore, chunk)

        result = dict(chunk)
        if scores is None:
            result["scores"] = None
            result["passed"] = False
            result["use_case"] = None
            result["reject_reason"] = "scoring_failed"
            failed += 1
        else:
            result["scores"] = scores
            passed, reason = checker(scores, chunk)
            result["passed"] = passed
            result["reject_reason"] = reason
            result["use_case"] = determine_use_case(scores) if passed else None
            success += 1
            if passed:
                passed_count += 1

        out_f.write(json.dumps(result, ensure_ascii=False) + "\n")
        out_f.flush()

        done = success + failed
        elapsed = time.time() - start
        rate = done / elapsed if elapsed > 0 else 0
        eta = (len(todo) - done) / rate if rate > 0 else 0
        print(f"\r[{done}/{len(todo)}] 성공 {success} 실패 {failed} "
              f"통과 {passed_count} | {rate:.1f}/s | ETA {eta:.0f}s",
              end="", flush=True)

    await asyncio.gather(*[run_one(c) for c in todo])
    out_f.close()

    print(f"\n완료. {time.time()-start:.1f}초 | "
          f"성공 {success} 실패 {failed} 통과 {passed_count}")
    print(f"통과율: {passed_count/max(success,1)*100:.1f}%")
    print(f"출력: {output_path}")


# ════════════════════════════════════════════════════════════════════
# Entry
# ════════════════════════════════════════════════════════════════════

async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--book", help="JW/BGE/GM/TI/EH (생략 시 전부)")
    parser.add_argument("--limit", type=int, help="테스트용 N개만")
    args = parser.parse_args()

    book_files = {
        "JW":  "gs.jsonl",
        "BGE": "bge.jsonl",
        "GM":  "gm.jsonl",
        "TI":  "ti.jsonl",
        "EH":  "eh.jsonl",
    }

    books = [args.book] if args.book else list(book_files.keys())

    for book in books:
        await process_book(
            book,
            INPUT_DIR / book_files[book],
            OUTPUT_DIR / book_files[book],
            limit=args.limit,
        )


if __name__ == "__main__":
    asyncio.run(main())