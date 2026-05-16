// server.mjs — ml-backend HTTP/SSE 래퍼
// /api/v1/explain (POST, SSE): 해설 모드 멀티턴 RAG
//
// 흐름 (multiturn_rag.mjs의 코어 추출, CLI는 그대로 보존):
//   classify → COMMENTARY 면 rewrite → embed → search → LLM stream
//             → OUT_OF_DOMAIN/AMBIGUOUS 면 router.message short-circuit
//
// SSE 이벤트 컨벤션 (frontend lib/api/sse.ts와 1:1):
//   data: {"type":"metadata", kind, ...}   ← router / rewrite / rag
//   data: {"type":"delta", "content":"..."}
//   data: {"type":"done"}
//   data: {"type":"error", "message":"..."}
//
// 전제:
//   - llama-server (E2B Q4_K_M) at http://localhost:8000 (chat)
//   - llama-server (BGE-M3 Q4_K_M) at http://localhost:8001 (embeddings)
//   - corpus.db (build_index.mjs로 생성)

import express from 'express';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { SearchIndex } from './search.mjs';
import { SessionLogger } from './logger.mjs';
import { classify } from './router.mjs';
import { rewriteQuery } from './query_rewriter.mjs';
import { COMMENTARY_SYSTEM } from './prompts.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const CHAT_URL = 'http://localhost:8000/v1/chat/completions';
const EMBED_URL = 'http://localhost:8001/v1/embeddings';
const CHAT_MODEL = 'gemma-4-E2B-it-Q4_K_M.gguf';
const DB_PATH = path.join(__dirname, 'corpus.db');
const TOP_K = 5;
const PORT = 3001;

// ---- 초기화 (multiturn_rag.mjs와 동일) ----
const logger = new SessionLogger();
console.log('[init] opening corpus.db ...');
const index = new SearchIndex(DB_PATH);
console.log(`[init] indexed chunks: ${index.count()}`);

// ---- helpers (multiturn_rag.mjs에서 동일 로직 복사) ----
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

// ---- SSE 송신 헬퍼 ----
function sseSend(res, event) {
  res.write(`data: ${JSON.stringify(event)}\n\n`);
}

// ---- LLM 스트리밍 (multiturn_rag.mjs의 streamResponse + SSE 변환) ----
async function streamResponseSSE(msgs, sseRes) {
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
            sseSend(sseRes, { type: 'delta', content: delta });
          }
          if (choice.finish_reason) finishReason = choice.finish_reason;
        }
        if (chunk.usage) usage = chunk.usage;
      } catch {}
    }
  }

  return {
    content: full,
    duration_ms: Date.now() - t0,
    completion_tokens: usage?.completion_tokens ?? 0,
    prompt_tokens: usage?.prompt_tokens ?? 0,
    finish_reason: finishReason || 'unknown',
  };
}

// ---- Express 앱 ----
const app = express();

// CORS — Next.js dev(:3000) ↔ ml-backend(:3001) 크로스 오리진
app.use((req, res, next) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.sendStatus(204);
  next();
});

app.use(express.json({ limit: '1mb' }));

// 헬스체크
app.get('/health', (req, res) => {
  res.json({ ok: true, indexed_chunks: index.count() });
});

// 해설 모드 SSE
app.post('/api/v1/explain', async (req, res) => {
  const { screen_id, query, history = [] } = req.body || {};
  if (!query || typeof query !== 'string') {
    return res.status(400).json({ error: 'query required' });
  }

  // SSE 헤더
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  res.flushHeaders?.();

  logger.startTurn();
  logger.userInput(query);
  logger.time('turn');

  try {
    // 1. Router 분류
    const route = await classify(query, history);
    logger.router(route);
    sseSend(res, {
      type: 'metadata',
      kind: 'router',
      intent: route.intent,
      message: route.message,
      reason: route.reason,
      duration_ms: route.duration_ms,
      screen_id,
    });

    // OOD / AMBIGUOUS → short-circuit
    if (route.intent === 'OUT_OF_DOMAIN' || route.intent === 'AMBIGUOUS') {
      const replyMessage =
        route.message ||
        (route.intent === 'OUT_OF_DOMAIN'
          ? '이 자료에서는 다룰 수 없는 주제입니다. 차라투스트라의 사상에 대해 궁금한 점이 있으면 물어주세요.'
          : '어떤 것을 말씀하시는 건지 좀 더 구체적으로 알려주시면 답해드리겠습니다.');

      logger.shortCircuit({ intent: route.intent, message: replyMessage });
      sseSend(res, { type: 'delta', content: replyMessage });
      sseSend(res, { type: 'done' });
      const totalMs = logger.timeEnd('turn');
      logger.turnComplete(totalMs);
      return res.end();
    }

    // 2. Query Rewrite
    const rew = await rewriteQuery(query, history);
    logger.rewrite(rew);
    sseSend(res, {
      type: 'metadata',
      kind: 'rewrite',
      original: rew.original,
      rewritten: rew.rewritten,
      skipped: rew.skipped,
    });

    // 3. RAG 검색
    logger.time('rag');
    const qVec = await embed(rew.rewritten);
    const hits = index.search(qVec, TOP_K);
    const ragMs = logger.timeEnd('rag');
    logger.ragSearch({ query: rew.rewritten, topK: TOP_K, duration_ms: ragMs, hits });
    sseSend(res, {
      type: 'metadata',
      kind: 'rag',
      duration_ms: ragMs,
      hits: hits.map(h => ({
        chunk_id: h.chunk_id,
        source_type: h.source_type,
        distance: h.distance,
        text_ko: h.text_ko,
      })),
    });

    // 4. LLM 호출 (system + history + 자료가 박힌 user)
    const context = formatChunks(hits);
    const userMsgWithContext = buildUserMessage(query, context);
    const promptMessages = [
      { role: 'system', content: COMMENTARY_SYSTEM },
      ...history,
      { role: 'user', content: userMsgWithContext },
    ];

    logger.llmStart();
    const out = await streamResponseSSE(promptMessages, res);
    logger.llmDone(out);

    sseSend(res, { type: 'done' });
    const totalMs = logger.timeEnd('turn');
    logger.turnComplete(totalMs);
    res.end();
  } catch (e) {
    logger.error(`explain failed: ${e.message}`);
    try { sseSend(res, { type: 'error', message: e.message }); } catch {}
    res.end();
  }
});

app.listen(PORT, () => {
  console.log(`[server] listening on http://localhost:${PORT}`);
  console.log(`  POST /api/v1/explain (SSE)`);
  console.log(`  GET  /health`);
});