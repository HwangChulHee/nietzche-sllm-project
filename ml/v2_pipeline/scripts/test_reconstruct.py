"""GS 청크 1개로 reconstruction 테스트."""
import json
import sys
from pathlib import Path
from openai import OpenAI

CHUNKS = Path("v2_data/english_chunks/gs.jsonl")
PROMPT_TEMPLATE = Path("v2_pipeline/prompts/reconstruction.txt")
GLOSSARY = Path("v2_pipeline/glossary.md")

MODEL = "google/gemma-4-26B-A4B-it"
BASE_URL = "http://localhost:8000/v1"

client = OpenAI(base_url=BASE_URL, api_key="EMPTY")


def load_chunk(aph_num: int) -> dict:
    for line in CHUNKS.open(encoding="utf-8"):
        c = json.loads(line)
        if c["aph_num"] == aph_num:
            return c
    raise ValueError(f"aph_num={aph_num} not found")


def build_prompt(chunk: dict) -> str:
    template = PROMPT_TEMPLATE.read_text(encoding="utf-8")
    glossary = GLOSSARY.read_text(encoding="utf-8")
    return template.format(
        glossary=glossary,
        work=chunk["work"],
        book=chunk["book"],
        aph_num=chunk["aph_num"],
        text_en=chunk["text_en"],
    )


def reconstruct(chunk: dict) -> str:
    prompt = build_prompt(chunk)
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=2048,
    )
    return resp.choices[0].message.content


def main():
    # 다양한 길이로 3개 테스트
    test_nums = [1, 271, 125]  # 긴 거 / 짧은 격언 / 유명한 거(신은 죽었다)
    if len(sys.argv) > 1:
        test_nums = [int(x) for x in sys.argv[1:]]
    
    for num in test_nums:
        chunk = load_chunk(num)
        print(f"\n{'='*70}")
        print(f"GS aph #{num} (Book {chunk['book']}, {chunk['char_count']}자)")
        print('='*70)
        print(f"\n[영어 원문]\n{chunk['text_en'][:300]}{'...' if chunk['char_count'] > 300 else ''}")
        print(f"\n[한국어 재구성]")
        result = reconstruct(chunk)
        print(result)


if __name__ == "__main__":
    main()