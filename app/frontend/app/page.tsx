"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { streamRespondAuto } from "@/lib/api/persona";
import { getSave } from "@/lib/api/save";
import { useAppDispatch } from "@/lib/hooks/useAppDispatch";
import { enterTitle } from "@/lib/store/episodeSlice";

export default function TitlePage() {
  const dispatch = useAppDispatch();
  const [hasSlot, setHasSlot] = useState<boolean | null>(null);
  const [sseLog, setSseLog] = useState<string>("");

  useEffect(() => {
    dispatch(enterTitle());

    getSave()
      .then((slot) => setHasSlot(slot !== null))
      .catch(() => setHasSlot(null));
  }, [dispatch]);

  const testSse = async () => {
    setSseLog("");
    const chunks: string[] = [];
    await streamRespondAuto(
      { screenId: "ep1_screen5_meeting", history: [] },
      {
        onDelta: (d) => {
          chunks.push(d);
          setSseLog(chunks.join(""));
        },
        onError: (m) => setSseLog(`error: ${m}`),
      },
    );
  };

  return (
    <div className="vn-placeholder">
      <h1 className="vn-placeholder__title">차라투스트라</h1>
      <p className="vn-placeholder__sub">EPISODE 1 — 하산</p>
      <p className="vn-placeholder__sub">[Phase 4: 타이틀 화면 구현 예정]</p>

      <div className="vn-placeholder__nav">
        <Link className="vn-placeholder__link" href="/ep1/scene/2">
          [시작] (→ Ep 1 #2)
        </Link>
        <Link className="vn-placeholder__link" href="/load">
          [불러오기] {hasSlot === false ? "(empty)" : hasSlot ? "(saved)" : ""}
        </Link>
      </div>

      <details style={{ marginTop: 48, fontSize: 12, opacity: 0.6 }}>
        <summary style={{ cursor: "pointer" }}>backend SSE 검증</summary>
        <button
          type="button"
          className="vn-placeholder__button"
          style={{ marginTop: 12 }}
          onClick={testSse}
        >
          /api/v1/respond/auto 호출
        </button>
        {sseLog && (
          <pre
            style={{
              marginTop: 12,
              maxWidth: 540,
              whiteSpace: "pre-wrap",
              fontFamily: "monospace",
              fontSize: 11,
              textAlign: "left",
            }}
          >
            {sseLog}
          </pre>
        )}
      </details>
    </div>
  );
}
