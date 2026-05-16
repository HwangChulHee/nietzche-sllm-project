// query_rewriter.mjs — 멀티턴 RAG용 쿼리 재작성
// 정책: 첫 턴 skip, 그 외엔 항상 LLM 재작성, 실패 시 원본 fallback
// system prompt는 prompts/query_rewriter.md 에서 로드

import { QUERY_REWRITER_SYSTEM } from './prompts.mjs';

const DEFAULT_OPTS = {
  llmUrl: 'http://localhost:8000/v1/chat/completions',
  model: 'gemma-4-E2B-it-Q4_K_M.gguf',
  recentTurns: 3,        // 히스토리에서 user+assistant 페어 N개 사용
  maxTokens: 80,
  temperature: 0.3,
  topP: 0.95,
  timeoutMs: 5000,
};

function buildRewritePrompt(currentQuery, recentHistory) {
  const lines = ['[히스토리]'];
  for (const m of recentHistory) {
    const role = m.role === 'user' ? '학습자' : '해설자';
    lines.push(`${role}: ${m.content}`);
  }
  lines.push('');
  lines.push('[학습자 마지막 질문]');
  lines.push(currentQuery);
  lines.push('');
  lines.push('[재작성]');
  return lines.join('\n');
}

function cleanRewrite(raw) {
  if (!raw) return '';
  let s = raw.trim();
  // "재작성:", "Rewritten:" 같은 prefix 제거
  s = s.replace(/^(재작성[된된]*\s*[:：]\s*|rewritten\s*[:：]\s*)/i, '');
  // 첫 줄만 (혹시 여러 줄 나오면)
  s = s.split('\n')[0].trim();
  // 양쪽 따옴표 제거
  s = s.replace(/^["「『'']/, '').replace(/["」』'']$/, '');
  return s.trim();
}

async function callLLM(messages, opts) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), opts.timeoutMs);

  try {
    const res = await fetch(opts.llmUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: opts.model,
        messages,
        max_tokens: opts.maxTokens,
        temperature: opts.temperature,
        top_p: opts.topP,
        stream: false,
      }),
      signal: controller.signal,
    });
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}: ${await res.text()}`);
    }
    const json = await res.json();
    return json.choices?.[0]?.message?.content || '';
  } finally {
    clearTimeout(timer);
  }
}

/**
 * 쿼리 재작성.
 *
 * @param {string} currentQuery - 학습자 원본 입력
 * @param {Array<{role, content}>} history - system 제외, user+assistant 순차
 * @param {object} options
 * @returns {{ rewritten, original, skipped, reason, duration_ms, raw }}
 */
export async function rewriteQuery(currentQuery, history, options = {}) {
  const opts = { ...DEFAULT_OPTS, ...options };
  const t0 = Date.now();

  // Skip: 첫 턴 (history 비어있음)
  if (!history || history.length === 0) {
    return {
      rewritten: currentQuery,
      original: currentQuery,
      skipped: true,
      reason: 'first_turn',
      duration_ms: 0,
      raw: null,
    };
  }

  // 최근 N턴만 (user+assistant 페어이므로 *2)
  const recent = history.slice(-opts.recentTurns * 2);

  const messages = [
    { role: 'system', content: QUERY_REWRITER_SYSTEM },
    { role: 'user', content: buildRewritePrompt(currentQuery, recent) },
  ];

  try {
    const raw = await callLLM(messages, opts);
    const rewritten = cleanRewrite(raw);
    const duration_ms = Date.now() - t0;

    // 결과가 비어있으면 fallback
    if (!rewritten) {
      return {
        rewritten: currentQuery,
        original: currentQuery,
        skipped: false,
        reason: 'empty_result_fallback',
        duration_ms,
        raw,
      };
    }

    return {
      rewritten,
      original: currentQuery,
      skipped: false,
      reason: 'ok',
      duration_ms,
      raw,
    };
  } catch (e) {
    return {
      rewritten: currentQuery,
      original: currentQuery,
      skipped: false,
      reason: `error_fallback: ${e.message}`,
      duration_ms: Date.now() - t0,
      raw: null,
    };
  }
}
