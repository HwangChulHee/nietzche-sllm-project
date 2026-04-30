"use client";

import { useEffect, useRef } from "react";
import { useParams } from "next/navigation";
import { MessageBubble } from "@/components/chat/MessageBubble";
import { useAppDispatch, useAppSelector } from "@/lib/hooks/useAppDispatch";
import { fetchMessages } from "@/lib/store/chatSlice";

export default function ConversationPage() {
  const params = useParams();
  const conversationId = params.conversationId as string;
  const dispatch = useAppDispatch();
  const { messages, error, currentConversationId, messagesLoading } =
    useAppSelector((s) => s.chat);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (conversationId && conversationId !== currentConversationId) {
      dispatch(fetchMessages(conversationId));
    }
  }, [conversationId, currentConversationId, dispatch]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (messagesLoading) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "120px 0",
        }}
      >
        <p
          style={{
            fontFamily: "var(--font-serif)",
            fontSize: "14px",
            color: "var(--text-secondary)",
          }}
        >
          대화를 불러오는 중...
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
