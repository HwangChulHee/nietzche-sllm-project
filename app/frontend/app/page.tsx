"use client";

import { useEffect, useRef } from "react";
import { MessageBubble } from "@/components/chat/MessageBubble";
import { useAppSelector } from "@/lib/hooks/useAppDispatch";

export default function Home() {
  const { messages, error } = useAppSelector((s) => s.chat);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const isEmpty = messages.length === 0;

  if (isEmpty) {
    return (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: "16px",
          padding: "120px 0",
        }}
      >
        <p
          style={{
            fontFamily: "var(--font-serif)",
            fontSize: "20px",
            fontStyle: "italic",
            color: "var(--text-secondary)",
            textAlign: "center",
          }}
        >
          &ldquo;무엇이 그대를 심연으로 이끌었는가?&rdquo;
        </p>
        <p
          style={{
            fontFamily: "var(--font-serif)",
            fontSize: "14px",
            color: "var(--text-secondary)",
          }}
        >
          아래에 고민을 적어보세요.
        </p>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "32px", padding: "16px 0" }}>
      {messages.map((msg, i) => (
        <MessageBubble key={i} message={msg} />
      ))}
      {error && (
        <p style={{ fontSize: "13px", textAlign: "center", color: "var(--accent)" }}>
          {error}
        </p>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
