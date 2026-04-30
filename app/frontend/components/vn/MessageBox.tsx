"use client";

import { useEffect, useRef } from "react";
import type { DialogueMessage } from "@/lib/store/dialogueSlice";

type Props = {
  messages: DialogueMessage[];
};

export function MessageBox({ messages }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages]);

  return (
    <div className="vn-msgbox" ref={scrollRef}>
      {messages.map((m, i) => (
        <Bubble key={i} m={m} />
      ))}
    </div>
  );
}

function Bubble({ m }: { m: DialogueMessage }) {
  const isAssistant = m.role === "assistant";
  const speaker = isAssistant ? "차라투스트라" : "그대";
  const showWaiting = isAssistant && m.streaming && m.content === "";
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
        } ${showWaiting ? "vn-msgbox__body--waiting" : ""}`}
      >
        {showWaiting ? "…" : m.content}
      </div>
    </div>
  );
}
