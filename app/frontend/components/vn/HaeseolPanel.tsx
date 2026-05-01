"use client";

import { useEffect, useRef, useState } from "react";

import { getHaeseolByScreenId } from "@/data/haeseol";
import type { HaeseolMessage } from "@/lib/store/haeseolSlice";
import { useExplain } from "@/lib/hooks/useExplain";

type Props = {
  screenId: string;
};

/**
 * HaeseolPanel — 우측 슬라이드 50% 패널 (VN_UI_POLICY §4).
 *
 * 정적 풀이(위, data/haeseol/) + 동적 풀이([더 깊이 묻기] 입력창 + 응답 누적).
 * ESC 또는 [해설 닫기]로 슬라이드 아웃.
 */
export function HaeseolPanel({ screenId }: Props) {
  const ix = useExplain(screenId);
  const entry = getHaeseolByScreenId(screenId);
  const [draft, setDraft] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  // ESC로 닫기
  useEffect(() => {
    if (!ix.open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") ix.closePanel();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [ix]);

  // 동적 풀이 누적 시 자동 스크롤
  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [ix.queryHistory]);

  const submit = () => {
    if (!draft.trim() || ix.streaming) return;
    ix.ask(draft);
    setDraft("");
  };

  const handleKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <aside
      className={`vn-haeseol ${ix.open ? "vn-haeseol--open" : ""}`}
      aria-hidden={!ix.open}
    >
      <div className="vn-haeseol__header">
        <button
          type="button"
          className="vn-haeseol__close"
          onClick={ix.closePanel}
          aria-label="해설 닫기"
        >
          [해설 닫기 ✕]
        </button>
      </div>

      <div className="vn-haeseol__scroll" ref={scrollRef}>
        {entry ? (
          <>
            <h3 className="vn-haeseol__title">{entry.title}</h3>
            <div className="vn-haeseol__divider">─────────────────────</div>
            <p className="vn-haeseol__summary">{entry.oneLineSummary}</p>

            <div className="vn-haeseol__quotes-header">▸ 핵심 구절 풀이</div>
            {entry.quotes.map((q, i) => (
              <div key={i} className="vn-haeseol__quote-block">
                <blockquote className="vn-haeseol__quote">“{q.text}”</blockquote>
                <p className="vn-haeseol__explanation">{q.explanation}</p>
              </div>
            ))}

            <div className="vn-haeseol__divider">─────────────────────</div>
            <div className="vn-haeseol__dynamic-header">▸ 더 깊이 묻기</div>

            {ix.queryHistory.map((m, i) => (
              <DynamicLine key={i} m={m} />
            ))}

            {ix.error && (
              <p className="vn-haeseol__error">길이 잠시 끊겼습니다.</p>
            )}
          </>
        ) : (
          <p className="vn-haeseol__empty">이 화면의 해설은 준비 중입니다.</p>
        )}
      </div>

      <div className="vn-haeseol__input">
        <textarea
          className="vn-haeseol__textarea"
          placeholder={ix.streaming ? "…" : "사상이나 구절에 대해 묻기"}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={handleKey}
          disabled={ix.streaming}
          rows={2}
        />
        <button
          type="button"
          className="vn-haeseol__ask"
          onClick={submit}
          disabled={ix.streaming || !draft.trim()}
        >
          묻기
        </button>
      </div>
    </aside>
  );
}

function DynamicLine({ m }: { m: HaeseolMessage }) {
  if (m.role === "user") {
    return (
      <div className="vn-haeseol__user">
        <span className="vn-haeseol__user-mark">묻기</span>
        <span className="vn-haeseol__user-text">{m.content}</span>
      </div>
    );
  }
  const showWaiting = m.streaming && m.content === "";
  return (
    <div className={`vn-haeseol__answer ${showWaiting ? "vn-haeseol__answer--waiting" : ""}`}>
      {showWaiting ? "…" : m.content}
    </div>
  );
}
