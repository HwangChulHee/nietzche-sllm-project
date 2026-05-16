// build_index.mjs
// data/*.jsonl 청크들을 BGE-M3로 임베딩해서 SQLite 인덱스(corpus.db) 생성
// 전제: llama-server BGE-M3가 http://localhost:8001 에서 실행 중 (--embeddings)

import fs from 'node:fs/promises';
import path from 'node:path';
import { createInterface } from 'node:readline';
import { createReadStream } from 'node:fs';
import { SearchIndex } from './search.mjs';

const EMBED_URL = 'http://localhost:8001/v1/embeddings';
const DATA_DIR = './data';
const DB_PATH = './corpus.db';

async function readJsonl(filePath) {
  const rows = [];
  const rl = createInterface({
    input: createReadStream(filePath, { encoding: 'utf8' }),
    crlfDelay: Infinity,
  });
  for await (const line of rl) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    rows.push(JSON.parse(trimmed));
  }
  return rows;
}

async function embed(text) {
  const res = await fetch(EMBED_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ input: text, model: 'bge-m3' }),
  });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}: ${await res.text()}`);
  }
  const json = await res.json();
  return json.data[0].embedding;
}

async function main() {
  // 기존 DB 삭제하고 새로
  try {
    await fs.unlink(DB_PATH);
    console.log(`[build] removed existing ${DB_PATH}`);
  } catch {}

  const index = new SearchIndex(DB_PATH);
  index.initSchema();

  // jsonl 파일 탐색
  const files = (await fs.readdir(DATA_DIR))
    .filter((f) => f.endsWith('.jsonl'))
    .sort();

  console.log(`[build] found ${files.length} jsonl files`);

  const chunks = [];
  for (const file of files) {
    const filePath = path.join(DATA_DIR, file);
    const rows = await readJsonl(filePath);
    console.log(`  ${file}: ${rows.length} chunks`);
    chunks.push(...rows);
  }
  console.log(`[build] total ${chunks.length} chunks\n`);

  // 임베딩 + insert
  for (let i = 0; i < chunks.length; i++) {
    const c = chunks[i];
    const text = c.text_ko || c.text_en || '';
    if (!text) {
      console.warn(`  [skip] ${c.id} (no text)`);
      continue;
    }

    process.stdout.write(`[${i + 1}/${chunks.length}] ${c.id} ... `);
    const t0 = Date.now();
    try {
      const vec = await embed(text);
      index.insert({
        id: c.id,
        source_type: c.source_type,
        text_ko: text,
        embedding: vec,
      });
      console.log(`${Date.now() - t0}ms`);
    } catch (e) {
      console.log(`FAIL: ${e.message}`);
    }
  }

  console.log(`\n[build] indexed ${index.count()} chunks into ${DB_PATH}`);
  index.close();
}

main();
