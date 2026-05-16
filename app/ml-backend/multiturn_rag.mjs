// multiturn_rag.mjs — 해설 모드 멀티턴 CLI
// 파이프라인: Router → (Rewriter → RAG → Generator) or short-circuit
//
// 전제:
//   - llama-server (E2B Q4_K_M) at http://localhost:8000 (chat)
//     실행 옵션 필수: --jinja --chat-template-kwargs '{"enable_thinking":false}'
//   - llama-server (BGE-M3 Q4_K_M) at http://localhost:8001 (embeddings)
//   - corpus.db (build_index.mjs로 생성)

import readline from 'node:readline';
import fs from 'node:fs/promises';
import path from 'node:path';
import { SearchIndex } from './search.mjs';
import { SessionLogger } from './logger.mjs';
import { classify } from './router.mjs';
import { rewriteQuery } from './query_rewriter.mjs';
import { COMMENTARY_SYSTEM } from './prompts.mjs';

const CHAT_URL = 'http://localhost:8000/v1/chat/completions';
const EMBED_URL = 'http://localhost:8001/v1/embeddings';
const CHAT_MODEL = 'gemma-4-E2B-it-Q4_K_M.gguf';
const DB_PATH = './corpus.db';
const SAVE_DIR = './sessions';
const TOP_K = 5;

// ---- 초기화 ----
const logger = new SessionLogger();
console.log('[init] opening corpus.db ...');
const index = new SearchIndex(DB_PATH);
console.log(`[init] indexed chunks: ${index.count()}\n`);

// history: system 제외, user는 원본 텍스트(자료 X), assistant는 응답
let history = [];

// ---- 임베딩 ----
async function embed(text) {
  const res = await fetch(EMBED_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ input: text, model: 'bge-m3' }),
  });
  if (!res.ok) throw new Error(`embed HTTP ${res.status}: ${await res.text()}`);
  const json = await res.json();
  return json.data[0].embedding;
}

// ---- 검색 결과 포맷 (LLM 프롬프트용) ----
function formatChunks(hits) {
  return hits
    .map((h, i) => {
      const label =
        h.source_type === 'original'
          ? '원전'
          : h.source_type === 'interpretation'
          ? '풀이'
          : h.source_type;
      return `[${i + 1}] (${label} / ${h.chunk_id})\n${h.text_ko}`;
    })
    .join('\n\n');
}

function buildUserMessage(query, context) {
  return `[참고 자료]
${context}

[학습자 질문]
${query}

학습자의 질문 형식·의도에 맞춰 답하세요. 자료는 필요한 부분만 활용하고, "일상 예시", "비유", "쉽게" 요청 시에는 자료의 핵심 개념을 학습자에게 친숙한 표현으로 풀어 쓰세요. "자료 [N]에 따르면" 같은 학술적 인용 표기는 피하고 자연스러운 문장으로.`;
}

// ---- 추론 스트리밍 ----
async function streamResponse(msgs) {
  const t0 = Date.now();
  const res = await fetch(CHAT_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      model: CHAT_MODEL,
      messages: msgs,
      max_tokens: 1000,
      temperature: 0.7,
      top_p: 0.95,
      top_k: 64,
      stream: true,
      stream_options: { include_usage: true },
    }),
  });
  if (!res.ok) throw new Error(`chat HTTP ${res.status}: ${await res.text()}`);

  const reader = res.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';
  let full = '';
  let usage = null;
  let finishReason = null;

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed.startsWith('data: ')) continue;
      const data = trimmed.slice(6).trim();
      if (data === '[DONE]') continue;
      try {
        const chunk = JSON.parse(data);
        const choice = chunk.choices?.[0];
        if (choice) {
          const delta = choice.delta?.content || '';
          if (delta) {
            logger.llmToken(delta);
            full += delta;
          }
          if (choice.finish_reason) finishReason = choice.finish_reason;
        }
        if (chunk.usage) usage = chunk.usage;
      } catch {}
    }
  }

  const duration_ms = Date.now() - t0;
  return {
    content: full,
    duration_ms,
    completion_tokens: usage?.completion_tokens ?? 0,
    prompt_tokens: usage?.prompt_tokens ?? 0,
    finish_reason: finishReason || 'unknown',
  };
}

// ---- 메인 루프 ----
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
});

function ask(prompt) {
  return new Promise((resolve) => rl.question(prompt, resolve));
}

async function main() {
  console.log('해설 모드 멀티턴 CLI (Router + RAG + Query Rewriting)');
  console.log('명령어: /reset /save /context /router /rewrite /log /stats /verbose /quit\n');

  while (true) {
    let query;
    try {
      query = (await ask('you> ')).trim();
    } catch {
      break;
    }
    if (!query) continue;

    // ---- 명령어 ----
    if (query === '/quit') break;

    if (query === '/reset') {
      history = [];
      console.log('[reset] history cleared\n');
      continue;
    }

    if (query === '/context') {
      const last = logger.getLastRewrite();
      if (!last) {
        console.log('[context] 없음\n');
      } else {
        console.log(`[context] 마지막 검색 쿼리: "${last.rewritten}"`);
        console.log('(상세 청크는 로그 파일에서 확인)\n');
      }
      continue;
    }

    if (query === '/router') {
      const last = logger.getLastRouter();
      if (!last) {
        console.log('[router] 없음\n');
      } else {
        console.log('[router]');
        console.log(`  intent    : ${last.intent}`);
        if (last.message) console.log(`  message   : ${last.message}`);
        console.log(`  reason    : ${last.reason}`);
        console.log(`  duration  : ${last.duration_ms}ms`);
        if (last.raw && last.raw !== last.intent) console.log(`  raw       : ${last.raw}`);
        console.log();
      }
      continue;
    }

    if (query === '/rewrite') {
      const last = logger.getLastRewrite();
      if (!last) {
        console.log('[rewrite] 없음\n');
      } else {
        console.log('[rewrite]');
        console.log(`  original  : ${last.original}`);
        console.log(`  rewritten : ${last.rewritten}`);
        console.log(`  skipped   : ${last.skipped}`);
        console.log(`  reason    : ${last.reason}`);
        console.log(`  duration  : ${last.duration_ms}ms`);
        if (last.raw && last.raw !== last.rewritten) {
          console.log(`  raw       : ${last.raw}`);
        }
        console.log();
      }
      continue;
    }

    if (query === '/log') {
      console.log(`[log] ${logger.getFilePath()}\n`);
      continue;
    }

    if (query === '/stats') {
      logger.printStats();
      continue;
    }

    if (query.startsWith('/verbose')) {
      const arg = query.split(/\s+/)[1];
      if (arg === 'on') logger.setVerbose(true);
      else if (arg === 'off') logger.setVerbose(false);
      else console.log(`[verbose] usage: /verbose on|off (current: ${logger.verbose})\n`);
      continue;
    }

    if (query === '/save') {
      await fs.mkdir(SAVE_DIR, { recursive: true });
      const ts = new Date().toISOString().replace(/[:.]/g, '-');
      const file = path.join(SAVE_DIR, `session_${ts}.json`);
      await fs.writeFile(file, JSON.stringify(history, null, 2), 'utf8');
      console.log(`[save] ${file}\n`);
      continue;
    }

    // ---- 턴 처리 ----
    logger.startTurn();
    logger.userInput(query);
    logger.time('turn');

    // 1. Router (분류)
    const route = await classify(query, history);
    logger.router(route);

    // OUT_OF_DOMAIN / AMBIGUOUS → short-circuit
    if (route.intent === 'OUT_OF_DOMAIN' || route.intent === 'AMBIGUOUS') {
      const replyMessage =
        route.message ||
        (route.intent === 'OUT_OF_DOMAIN'
          ? '이 자료에서는 다룰 수 없는 주제입니다. 차라투스트라의 사상에 대해 궁금한 점이 있으면 물어주세요.'
          : '어떤 것을 말씀하시는 건지 좀 더 구체적으로 알려주시면 답해드리겠습니다.');

      logger.shortCircuit({ intent: route.intent, message: replyMessage });

      history.push({ role: 'user', content: query });
      history.push({ role: 'assistant', content: replyMessage });

      const totalMs = logger.timeEnd('turn');
      logger.turnComplete(totalMs);
      continue;
    }

    // COMMENTARY: 일반 RAG 흐름

    // 2. Query Rewriting
    const rew = await rewriteQuery(query, history);
    logger.rewrite(rew);

    // 3. RAG 검색
    let hits;
    try {
      logger.time('rag');
      const qVec = await embed(rew.rewritten);
      hits = index.search(qVec, TOP_K);
      const ragMs = logger.timeEnd('rag');
      logger.ragSearch({ query: rew.rewritten, topK: TOP_K, duration_ms: ragMs, hits });
    } catch (e) {
      logger.error(`rag failed: ${e.message}`);
      const totalMs = logger.timeEnd('turn');
      logger.turnComplete(totalMs);
      continue;
    }

    // 4. LLM 호출 (history + 자료가 박힌 현재 user 메시지)
    const context = formatChunks(hits);
    const userMsgWithContext = buildUserMessage(query, context);
    const promptMessages = [
      { role: 'system', content: COMMENTARY_SYSTEM },
      ...history,
      { role: 'user', content: userMsgWithContext },
    ];

    logger.llmStart();
    try {
      const out = await streamResponse(promptMessages);
      logger.llmDone(out);

      // history에는 자료 빠진 깨끗한 쌍만 저장
      history.push({ role: 'user', content: query });
      history.push({ role: 'assistant', content: out.content });
    } catch (e) {
      logger.error(`llm failed: ${e.message}`);
    }

    const totalMs = logger.timeEnd('turn');
    logger.turnComplete(totalMs);
  }

  await logger.close();
  index.close();
  rl.close();
  console.log('\nbye.');
}

main();
