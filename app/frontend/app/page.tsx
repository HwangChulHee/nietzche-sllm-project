"use client";

import { useEffect, useRef } from "react";
import { MessageBubble } from "@/components/chat/MessageBubble";
import { ChatInput } from "@/components/chat/ChatInput";
import { useAppSelector } from "@/lib/hooks/useAppDispatch";
import { useStreamingChat } from "@/lib/hooks/useStreamingChat";

export default function Home() {
  const { messages, isStreaming, error } = useAppSelector((s) => s.chat);
  const { sendMessage } = useStreamingChat();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const isEmpty = messages.length === 0;

  return (
    <div className="flex min-h-screen flex-col" style={{ backgroundColor: "var(--bg-primary)", color: "var(--text-primary)" }}>
      {/* 헤더 */}
      <header
        className="flex flex-col items-center justify-center py-8 shrink-0"
        style={{ borderBottom: "1px solid var(--border-color)" }}
      >
        <h1 className="text-2xl tracking-tight" style={{ fontFamily: "var(--font-serif)" }}>
          니체 페르소나 sLLM 상담
        </h1>
        <p className="text-sm mt-1" style={{ color: "var(--text-secondary)" }}>
          캡스톤 디자인 데모
        </p>
      </header>

      {/* 메시지 영역 */}
      <main className="flex-1 overflow-y-auto py-6 px-6">
        <div className="max-w-[720px] mx-auto">
          {isEmpty ? (
            <div className="flex flex-col items-center justify-center py-32 gap-4">
              <p
                className="text-lg italic"
                style={{
                  fontFamily: "var(--font-serif)",
                  color: "var(--text-secondary)",
                }}
              >
                &ldquo;무엇이 그대를 심연으로 이끌었는가?&rdquo;
              </p>
              <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
                아래에 고민을 적어보세요.
              </p>
            </div>
          ) : (
            <div className="flex flex-col gap-7 py-4">
              {messages.map((msg, i) => (
                <MessageBubble key={i} message={msg} />
              ))}
              {error && (
                <p className="text-xs text-center" style={{ color: "var(--accent)" }}>
                  {error}
                </p>
              )}
              <div ref={bottomRef} />
            </div>
          )}
        </div>
      </main>

      {/* 입력 영역 */}
      <footer
        className="py-4 px-6 shrink-0"
        style={{ borderTop: "1px solid var(--border-color)" }}
      >
        <div className="max-w-[720px] mx-auto">
          <ChatInput onSend={sendMessage} disabled={isStreaming} />
        </div>
      </footer>
    </div>
  );
}
