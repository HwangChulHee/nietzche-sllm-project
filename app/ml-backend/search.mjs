// search.mjs — 검색 인터페이스 (SQLite + sqlite-vec 구현)
// 향후 LanceDB 등으로 교체 시 이 파일만 변경

import Database from 'better-sqlite3';
import * as sqliteVec from 'sqlite-vec';

const EMBED_DIM = 1024;

export class SearchIndex {
  constructor(dbPath) {
    this.db = new Database(dbPath);
    sqliteVec.load(this.db);
    this.db.pragma('journal_mode = WAL');
  }

  initSchema() {
    this.db.exec(`
      CREATE VIRTUAL TABLE IF NOT EXISTS chunks USING vec0(
        chunk_id TEXT PARTITION KEY,
        source_type TEXT,
        text_ko TEXT,
        embedding FLOAT[${EMBED_DIM}]
      )
    `);
  }

  insert(chunk) {
    // chunk: { id, source_type, text_ko, embedding (1024-d Float32Array or number[]) }
    const stmt = this.db.prepare(`
      INSERT INTO chunks(chunk_id, source_type, text_ko, embedding)
      VALUES (?, ?, ?, ?)
    `);
    const blob = Buffer.from(new Float32Array(chunk.embedding).buffer);
    stmt.run(chunk.id, chunk.source_type, chunk.text_ko, blob);
  }

  count() {
    return this.db.prepare('SELECT COUNT(*) AS n FROM chunks').get().n;
  }

  clear() {
    this.db.exec('DELETE FROM chunks');
  }

  /**
   * 검색.
   * @param {number[]} queryVec - 1024차원 쿼리 임베딩
   * @param {number} topK
   * @param {object} opts - { sourceTypes: ['original','interpretation'] }
   * @returns {Array<{ chunk_id, source_type, text_ko, distance }>}
   */
  search(queryVec, topK = 5, opts = {}) {
    const blob = Buffer.from(new Float32Array(queryVec).buffer);

    let where = 'embedding MATCH ?';
    const params = [blob];

    if (opts.sourceTypes && opts.sourceTypes.length > 0) {
      const placeholders = opts.sourceTypes.map(() => '?').join(',');
      where += ` AND source_type IN (${placeholders})`;
      params.push(...opts.sourceTypes);
    }

    params.push(topK);

    const sql = `
      SELECT chunk_id, source_type, text_ko, distance
      FROM chunks
      WHERE ${where}
      ORDER BY distance
      LIMIT ?
    `;
    return this.db.prepare(sql).all(...params);
  }

  close() {
    this.db.close();
  }
}
