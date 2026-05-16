// logger.mjs — 세션 로깅 (콘솔 + JSONL 파일)
// 의존성 0, ANSI 색깔, 파일 비동기 append

import fs from 'node:fs/promises';
import { mkdirSync } from 'node:fs';
import path from 'node:path';

const LOG_DIR = './logs';

// ANSI 색깔
const C = {
  reset: '\x1b[0m',
  dim: '\x1b[2m',
  gray: '\x1b[90m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  cyan: '\x1b[36m',
  magenta: '\x1b[35m',
};

mkdirSync(LOG_DIR, { recursive: true });

export class SessionLogger {
  constructor() {
    const ts = new Date().toISOString().replace(/[:.]/g, '-');
    this.sessionId = ts;
    this.filePath = path.join(LOG_DIR, `session_${ts}.jsonl`);
    this.turn = 0;
    this.timers = new Map(); // label -> start ms
    this.stats = {
      turnsCompleted: 0,
      routerCalls: 0,
      routerByIntent: { COMMENTARY: 0, OUT_OF_DOMAIN: 0, AMBIGUOUS: 0 },
      routerDurations: [],
      rewriteCallsCompleted: 0,
      rewriteSkipped: 0,
      rewriteDurations: [],
      ragDurations: [],
      llmDurations: [],
      llmTokens: [],
      llmTokPerSec: [],
      errors: 0,
    };
    this.lastRewrite = null;
    this.lastRouter = null;
    this.verbose = true;

    this._write({ event: 'session_start', turn: 0, data: { sessionId: this.sessionId } });
    console.log(`${C.gray}[log] session ${this.sessionId} → ${this.filePath}${C.reset}\n`);
  }

  setVerbose(v) {
    this.verbose = v;
    console.log(`${C.gray}[log] verbose = ${v}${C.reset}\n`);
  }

  startTurn() {
    this.turn += 1;
    this.timers.clear();
    this._write({ event: 'turn_start', turn: this.turn, data: {} });
  }

  time(label) {
    this.timers.set(label, Date.now());
  }

  timeEnd(label) {
    const start = this.timers.get(label);
    if (!start) return 0;
    const ms = Date.now() - start;
    this.timers.delete(label);
    return ms;
  }

  userInput(text) {
    this._write({ event: 'user_input', turn: this.turn, data: { text } });
  }

  router({ intent, message, reason, duration_ms, raw }) {
    this.lastRouter = { intent, message, reason, duration_ms, raw };
    this.stats.routerCalls += 1;
    this.stats.routerDurations.push(duration_ms);
    if (this.stats.routerByIntent[intent] !== undefined) {
      this.stats.routerByIntent[intent] += 1;
    }

    const color =
      intent === 'COMMENTARY' ? C.green : intent === 'OUT_OF_DOMAIN' ? C.red : C.yellow;
    console.log(
      `${C.magenta}[router]${C.reset} ${color}${intent}${C.reset} ${C.gray}(${duration_ms}ms)${C.reset}`
    );
    if (message) {
      const preview = message.length > 100 ? message.slice(0, 100) + '...' : message;
      console.log(`  ${C.dim}${preview}${C.reset}`);
    }
    console.log();

    this._write({
      event: 'router',
      turn: this.turn,
      data: { intent, message, reason, duration_ms, raw },
    });
  }

  rewrite({ original, rewritten, skipped, reason, duration_ms, raw }) {
    this.lastRewrite = { original, rewritten, skipped, reason, duration_ms, raw };
    if (skipped) {
      this.stats.rewriteSkipped += 1;
      console.log(`${C.cyan}[rewrite]${C.reset} ${C.dim}skipped (${reason})${C.reset}\n`);
    } else {
      this.stats.rewriteCallsCompleted += 1;
      this.stats.rewriteDurations.push(duration_ms);
      console.log(
        `${C.cyan}[rewrite]${C.reset} "${original}" → "${rewritten}" ${C.gray}(${duration_ms}ms)${C.reset}\n`
      );
    }
    this._write({
      event: 'rewrite',
      turn: this.turn,
      data: { original, rewritten, skipped, reason, duration_ms, raw },
    });
  }

  ragSearch({ query, topK, duration_ms, hits }) {
    this.stats.ragDurations.push(duration_ms);
    console.log(`${C.yellow}[rag]${C.reset} ${hits.length} chunks ${C.gray}(${duration_ms}ms)${C.reset}`);
    hits.forEach((h, i) => {
      const dist = h.distance.toFixed(3);
      const label =
        h.source_type === 'original' ? '원전' : h.source_type === 'interpretation' ? '풀이' : h.source_type;
      const preview = (h.text_ko || '').slice(0, 60).replace(/\n/g, ' ');
      console.log(
        `  ${C.gray}${i + 1}.${C.reset} [${C.gray}${dist}${C.reset}] ${h.chunk_id} ${C.dim}(${label})${C.reset} ${preview}...`
      );
    });
    console.log();
    this._write({
      event: 'rag_search',
      turn: this.turn,
      data: {
        query,
        topK,
        duration_ms,
        hits: hits.map((h) => ({
          id: h.chunk_id,
          source_type: h.source_type,
          distance: h.distance,
          text_ko: h.text_ko,
        })),
      },
    });
  }

  llmStart() {
    console.log(`${C.green}[llm]${C.reset} generating... ${C.gray}(turn ${this.turn})${C.reset}`);
    this._write({ event: 'llm_start', turn: this.turn, data: {} });
  }

  llmToken(delta) {
    if (this.verbose) {
      process.stdout.write(delta);
    }
  }

  llmDone({ duration_ms, completion_tokens, prompt_tokens, finish_reason, content }) {
    const tokPerSec = completion_tokens > 0 ? (completion_tokens / (duration_ms / 1000)).toFixed(1) : '0';
    this.stats.llmDurations.push(duration_ms);
    this.stats.llmTokens.push(completion_tokens);
    this.stats.llmTokPerSec.push(parseFloat(tokPerSec));

    if (this.verbose) {
      process.stdout.write('\n');
    }
    console.log(
      `${C.green}[llm]${C.reset} done ${C.gray}(${(duration_ms / 1000).toFixed(1)}s, ${completion_tokens} tokens, ${tokPerSec} tok/s, finish=${finish_reason})${C.reset}\n`
    );
    this._write({
      event: 'llm_done',
      turn: this.turn,
      data: { duration_ms, completion_tokens, prompt_tokens, finish_reason, content },
    });
  }

  shortCircuit({ intent, message }) {
    // OUT_OF_DOMAIN / AMBIGUOUS 시 generator 호출 없이 router 메시지를 응답으로
    console.log(`${C.green}[short-circuit]${C.reset} ${intent} 응답 출력`);
    console.log(message);
    console.log();
    this._write({
      event: 'short_circuit',
      turn: this.turn,
      data: { intent, message },
    });
  }

  turnComplete(totalMs) {
    this.stats.turnsCompleted += 1;
    this._write({ event: 'turn_complete', turn: this.turn, data: { total_duration_ms: totalMs } });
  }

  warn(message, extra = {}) {
    console.log(`${C.yellow}[warn]${C.reset} ${message}`);
    this._write({ event: 'warn', turn: this.turn, data: { message, ...extra } });
  }

  error(message, extra = {}) {
    this.stats.errors += 1;
    console.log(`${C.red}[error]${C.reset} ${message}`);
    this._write({ event: 'error', turn: this.turn, data: { message, ...extra } });
  }

  printStats() {
    const avg = (arr) => (arr.length === 0 ? 0 : arr.reduce((a, b) => a + b, 0) / arr.length);

    console.log(`${C.magenta}=== Session Stats ===${C.reset}`);
    console.log(`  turns completed       : ${this.stats.turnsCompleted}`);
    console.log(
      `  router (C/OOD/AMB)    : ${this.stats.routerByIntent.COMMENTARY} / ${this.stats.routerByIntent.OUT_OF_DOMAIN} / ${this.stats.routerByIntent.AMBIGUOUS}`
    );
    if (this.stats.routerDurations.length > 0) {
      console.log(`  avg router time       : ${avg(this.stats.routerDurations).toFixed(0)}ms`);
    }
    console.log(
      `  rewrite (called/skip) : ${this.stats.rewriteCallsCompleted} / ${this.stats.rewriteSkipped}`
    );
    if (this.stats.rewriteDurations.length > 0) {
      console.log(`  avg rewrite time      : ${avg(this.stats.rewriteDurations).toFixed(0)}ms`);
    }
    if (this.stats.ragDurations.length > 0) {
      console.log(`  avg rag time          : ${avg(this.stats.ragDurations).toFixed(0)}ms`);
    }
    if (this.stats.llmDurations.length > 0) {
      console.log(`  avg llm time          : ${(avg(this.stats.llmDurations) / 1000).toFixed(1)}s`);
      console.log(`  avg tok/s             : ${avg(this.stats.llmTokPerSec).toFixed(1)}`);
      console.log(`  avg tokens / response : ${avg(this.stats.llmTokens).toFixed(0)}`);
    }
    console.log(`  errors                : ${this.stats.errors}`);
    console.log(`  log file              : ${this.filePath}`);
    console.log();
  }

  getLastRewrite() {
    return this.lastRewrite;
  }

  getLastRouter() {
    return this.lastRouter;
  }

  getFilePath() {
    return this.filePath;
  }

  async _write(record) {
    const line = JSON.stringify({ ts: new Date().toISOString(), ...record }) + '\n';
    try {
      await fs.appendFile(this.filePath, line, 'utf8');
    } catch (e) {
      console.error(`[logger] write failed: ${e.message}`);
    }
  }

  async close() {
    this._write({ event: 'session_end', turn: this.turn, data: this.stats });
  }
}
