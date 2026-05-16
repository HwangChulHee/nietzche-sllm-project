// prompts.mjs — system prompt 로더
// prompts/ 디렉토리의 마크다운 파일을 읽어서 상수로 export.
// 앱 시작 시 1회만 읽음 (변경하려면 앱 재시작).

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PROMPTS_DIR = path.join(__dirname, 'prompts');

function load(filename) {
  const filePath = path.join(PROMPTS_DIR, filename);
  try {
    return fs.readFileSync(filePath, 'utf8').trim();
  } catch (e) {
    throw new Error(`Failed to load prompt: ${filePath}\n${e.message}`);
  }
}

export const COMMENTARY_SYSTEM = load('commentary_system.md');
export const QUERY_REWRITER_SYSTEM = load('query_rewriter.md');
export const ROUTER_SYSTEM = load('router.md');
