import { SearchIndex } from "./search.mjs";

const index = new SearchIndex("./corpus.db");

// 8001에 임베딩 요청
async function embed(text) {
  const res = await fetch("http://localhost:8001/v1/embeddings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ input: text, model: "bge-m3" }),
  });
  const json = await res.json();
  return json.data[0].embedding;
}

const queries = [
  "차라투스트라는 왜 산에서 내려와?",
  "독수리와 뱀은 뭘 의미해?",
  "위버멘쉬가 뭐야?",
];

for (const q of queries) {
  console.log("\n===", q, "===");
  const vec = await embed(q);
  const hits = index.search(vec, 3);
  for (const h of hits) {
    console.log(`  [${h.distance.toFixed(3)}] ${h.chunk_id} (${h.source_type})`);
    console.log(`    ${h.text_ko.slice(0, 80)}...`);
  }
}

index.close();
