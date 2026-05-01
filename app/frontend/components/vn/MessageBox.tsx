"use client";

import { useEffect, useRef, useState } from "react";
import { useAppSelector } from "@/lib/hooks/useAppDispatch";
import type { DialogueMessage } from "@/lib/store/dialogueSlice";

const DELAY_HINT_MS = 3000;

type Props = {
  messages: DialogueMessage[];
};

export function MessageBox({ messages }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const streamingState = useAppSelector((s) => s.dialogue.streamingState);
  const [showDelayHint, setShowDelayHint] = useState(false);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages]);

  // 응답 지연 > 3초 시 좌측 italic … 인디케이터 (정책 §3.5).
  // booting 또는 빈 streaming 본문일 때 타이머 가동, 상태 변화 시 cleanup이 reset.
  const lastMsg = messages[messages.length - 1];
  const isAwaiting =
    streamingState === "booting" ||
    (streamingState === "streaming" &&
      lastMsg?.streaming === true &&
      lastMsg.content === "");

  useEffect(() => {
    if (!isAwaiting) return;
    const t = window.setTimeout(() => setShowDelayHint(true), DELAY_HINT_MS);
    return () => {
      window.clearTimeout(t);
      setShowDelayHint(false);
    };
  }, [isAwaiting]);

  return (
    <div className="vn-msgbox" ref={scrollRef}>
      {messages.map((m, i) => (
        <Bubble key={i} m={m} showDelayHint={showDelayHint} />
      ))}
    </div>
  );
}

function Bubble({
  m,
  showDelayHint,
}: {
  m: DialogueMessage;
  showDelayHint: boolean;
}) {
  const isAssistant = m.role === "assistant";
  const speaker = isAssistant ? "차라투스트라" : "그대";
  const isAwaiting = isAssistant && m.streaming && m.content === "";
  return (
    <div
      className={`vn-msgbox__bubble vn-msgbox__bubble--${
        isAssistant ? "assistant" : "user"
      }`}
    >
      <div className="vn-msgbox__speaker">{speaker}</div>
      <div
        className={`vn-msgbox__body ${
          m.isSilent ? "vn-msgbox__body--silent" : ""
        } ${isAwaiting ? "vn-msgbox__body--awaiting" : ""}`}
      >
        {isAwaiting ? (
          <span
            className={`vn-msgbox__delay-hint ${
              showDelayHint ? "vn-msgbox__delay-hint--visible" : ""
            }`}
            aria-hidden="true"
          >
            …
          </span>
        ) : (
          m.content
        )}
      </div>
    </div>
  );
}
