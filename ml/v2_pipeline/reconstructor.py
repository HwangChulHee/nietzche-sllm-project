"""배치 reconstruction. 영어 청크 → 한국어 재구성.

기능:
- 동시 호출 (asyncio)
- 진행률 표시
- 재시도
- 중단 시 재개 가능 (이미 처리된 aph_num 스킵)
- 라인 단위 즉시 저장 (중단해도 손실 없음)
"""
import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from openai import AsyncOpenAI

# 설정
MODEL = "google/gemma-4-26B-A4B-it"
BASE_URL = "http://localhost:8000/v1"
PROMPT_TEMPLATE_PATH = Path("v2_pipeline/prompts/reconstruction.txt")
GLOSSARY_PATH = Path("v2_pipeline/glossary.md")

# 동시 호출 수 (vllm KV cache가 28x니까 안전하게 16)
CONCURRENCY = 16
MAX_RETRIES = 3
TEMPERATURE = 0.3
MAX_TOKENS = 4096


client = AsyncOpenAI(base_url=BASE_URL, api_key="EMPTY")


def load_chunks(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.open(encoding="utf-8")]


def load_done_aph_nums(output_path: Path) -> set[int]:
    """이미 처리된 청크 ID 로드 (재개용)."""
    if not output_path.exists():
        return set()
    done = set()
    for line in output_path.open(encoding="utf-8"):
        try:
            done.add(json.loads(line)["aph_num"])
        except (json.JSONDecodeError, KeyError):
            continue
    return done


def build_prompt(chunk: dict, template: str, glossary: str) -> str:
    return template.format(
        glossary=glossary,
        work=chunk["work"],
        book=chunk.get("book", "N/A"),
        aph_num=chunk["aph_num"],
        text_en=chunk["text_en"],
    )


async def reconstruct_one(
    chunk: dict,
    template: str,
    glossary: str,
    sem: asyncio.Semaphore,
) -> dict:
    """단일 청크 reconstruction. 재시도 포함."""
    prompt = build_prompt(chunk, template, glossary)
    async with sem:
        for attempt in range(MAX_RETRIES):
            try:
                t0 = time.time()
                resp = await client.chat.completions.create(
                    model=MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=TEMPERATURE,
                    max_tokens=MAX_TOKENS,
                )
                text_ko = resp.choices[0].message.content.strip()
                elapsed = time.time() - t0
                return {
                    **chunk,
                    "text_ko_reconstructed": text_ko,
                    "ko_char_count": len(text_ko),
                    "reconstruction_elapsed_s": round(elapsed, 2),
                    "reconstruction_status": "ok",
                }
            except Exception as e:
                if attempt == MAX_RETRIES - 1:
                    return {
                        **chunk,
                        "text_ko_reconstructed": None,
                        "reconstruction_status": "failed",
                        "reconstruction_error": str(e)[:300],
                    }
                await asyncio.sleep(2 ** attempt)


async def run(input_path: Path, output_path: Path, limit: int | None):
    template = PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8")
    glossary = GLOSSARY_PATH.read_text(encoding="utf-8")
    
    all_chunks = load_chunks(input_path)
    done = load_done_aph_nums(output_path)
    
    todo = [c for c in all_chunks if c["aph_num"] not in done]
    if limit:
        todo = todo[:limit]
    
    print(f"전체 청크: {len(all_chunks)}")
    print(f"이미 처리: {len(done)}")
    print(f"이번 처리: {len(todo)}")
    print(f"동시 호출: {CONCURRENCY}")
    print()
    
    if not todo:
        print("처리할 청크 없음. 종료.")
        return
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sem = asyncio.Semaphore(CONCURRENCY)
    
    completed = 0
    failed = 0
    total = len(todo)
    t_start = time.time()
    
    # append 모드로 즉시 저장 (중단 안전)
    with output_path.open("a", encoding="utf-8") as fout:
        tasks = [
            asyncio.create_task(reconstruct_one(c, template, glossary, sem))
            for c in todo
        ]
        for coro in asyncio.as_completed(tasks):
            result = await coro
            fout.write(json.dumps(result, ensure_ascii=False) + "\n")
            fout.flush()
            
            completed += 1
            if result.get("reconstruction_status") != "ok":
                failed += 1
            
            elapsed = time.time() - t_start
            rate = completed / elapsed if elapsed > 0 else 0
            eta = (total - completed) / rate if rate > 0 else 0
            print(
                f"\r[{completed}/{total}] "
                f"성공 {completed - failed} 실패 {failed} | "
                f"{rate:.1f}/s | ETA {eta:.0f}s",
                end="",
                flush=True,
            )
    
    print()
    print(f"\n완료. 총 {time.time() - t_start:.1f}초")
    print(f"성공: {completed - failed}, 실패: {failed}")
    print(f"출력: {output_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("v2_data/english_chunks/gs.jsonl"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("v2_data/reconstructed/gs.jsonl"),
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="처음 N개만 처리 (테스트용)",
    )
    args = parser.parse_args()
    
    asyncio.run(run(args.input, args.output, args.limit))


if __name__ == "__main__":
    main()