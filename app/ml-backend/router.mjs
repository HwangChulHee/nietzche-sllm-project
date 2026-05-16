// router.mjs — 학습자 질문 분류
// 출력: { intent: 'COMMENTARY' | 'OUT_OF_DOMAIN' | 'AMBIGUOUS', message, ... }
// 파싱 실패 또는 LLM 실패 시 COMMENTARY로 폴백 (안전)

import { ROUTER_SYSTEM } from './prompts.mjs';

const DEFAULT_OPTS = {
  llmUrl: 'http://localhost:8000/v1/chat/completions',
  model: 'gemma-4-E2B-it-Q4_K_M.gguf',
  recentTurns: 3,
  maxTokens: 200,
  temperature: 0.3,
  topP: 0.95,
  timeoutMs: 10000,   // ← 5000 → 10000
};

const VALID_INTENTS = ['COMMENTARY', 'OUT_OF_DOMAIN', 'AMBIGUOUS'];

function buildRouterPrompt(currentQuery, recentHistory) {
  const lines = ['[히스토리]'];
  if (recentHistory.length === 0) {
    lines.push('(비어있음)');
  } else {
    for (const m of recentHistory) {
      const role = m.role === 'user' ? '학습자' : '해설자';
      lines.push(`${role}: ${m.content}`);
    }
  }
  lines.push('');
  lines.push('[학습자 마지막 질문]');
  lines.push(currentQuery);
  lines.push('');
  lines.push('[분류]');
  return lines.join('\n');
}

function parseRouterOutput(raw) {
  if (!raw) return null;
  const lines = raw.trim().split('\n');
  if (lines.length === 0) return null;

  // 첫 줄에서 intent 추출 (대소문자, prefix 변형 허용)
  const firstLine = lines[0].trim().toUpperCase();
  const intent = VALID_INTENTS.find(
    (i) => firstLine === i || firstLine.startsWith(i)
  );
  if (!intent) return null;

  // 둘째 줄부터 메시지
  const message = lines.slice(1).join('\n').trim();
  return { intent, message };
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
 * 학습자 질문 분류.
 *
 * @param {string} currentQuery - 학습자 원본 입력
 * @param {Array<{role, content}>} history - system 제외, user+assistant 순차
 * @param {object} options
 * @returns {{ intent, message, reason, duration_ms, raw }}
 */
export async function classify(currentQuery, history, options = {}) {
  const opts = { ...DEFAULT_OPTS, ...options };
  const t0 = Date.now();

  const recent = history.slice(-opts.recentTurns * 2);

  const messages = [
    { role: 'system', content: ROUTER_SYSTEM },
    { role: 'user', content: buildRouterPrompt(currentQuery, recent) },
  ];

  try {
    const raw = await callLLM(messages, opts);
    const duration_ms = Date.now() - t0;
    const parsed = parseRouterOutput(raw);

    if (!parsed) {
      // 파싱 실패 → COMMENTARY로 폴백 (RAG 흐름 그대로 진행)
      return {
        intent: 'COMMENTARY',
        message: '',
        reason: 'parse_failed_fallback',
        duration_ms,
        raw,
      };
    }

    return {
      intent: parsed.intent,
      message: parsed.message,
      reason: 'ok',
      duration_ms,
      raw,
    };
  } catch (e) {
    return {
      intent: 'COMMENTARY',
      message: '',
      reason: `error_fallback: ${e.message}`,
      duration_ms: Date.now() - t0,
      raw: null,
    };
  }
}
