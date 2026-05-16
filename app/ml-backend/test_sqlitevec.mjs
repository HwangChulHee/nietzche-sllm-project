import Database from "better-sqlite3";
import * as sqliteVec from "sqlite-vec";

const db = new Database(":memory:");
sqliteVec.load(db);

const { vec_version } = db.prepare("SELECT vec_version() AS vec_version").get();
console.log("sqlite-vec version:", vec_version);

// 메타 컬럼 + 벡터 테이블
db.exec(`
  CREATE VIRTUAL TABLE chunks USING vec0(
    chunk_id TEXT PARTITION KEY,
    source_type TEXT,
    embedding FLOAT[3]
  )
`);

const insert = db.prepare(
  "INSERT INTO chunks(chunk_id, source_type, embedding) VALUES (?, ?, ?)"
);
insert.run("a", "original", Buffer.from(new Float32Array([1, 0, 0]).buffer));
insert.run("b", "original", Buffer.from(new Float32Array([0, 1, 0]).buffer));
insert.run("c", "interpretation", Buffer.from(new Float32Array([0.9, 0.1, 0]).buffer));

// 검색
const query = Buffer.from(new Float32Array([1, 0, 0]).buffer);
const rows = db.prepare(`
  SELECT chunk_id, source_type, distance
  FROM chunks
  WHERE embedding MATCH ?
  ORDER BY distance
  LIMIT 5
`).all(query);

console.log("search results:", rows);
