"use client";

import { useEffect, useRef } from "react";
import { useParams } from "next/navigation";
import { MessageBubble } from "@/components/chat/MessageBubble";
import { ChatInput } from "@/components/chat/ChatInput";
import { useAppDispatch, useAppSelector } from "@/lib/hooks/useAppDispatch";
import { useStreamingChat } from "@/lib/hooks/useStreamingChat";
import { fetchMessages } from "@/lib/store/chatSlice";

export default function ConversationPage() {
  const params = useParams();
  const conversationId = params.conversationId as string;
  const dispatch = useAppDispatch();
  const { messages, isStreaming, error, currentConversationId, messagesLoading } =
    useAppSelector((s) => s.chat);
  const { sendMessage } = useStreamingChat();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (conversationId && conversationId !== currentConversationId) {
      dispatch(fetchMessages(conversationId));
    }
  }, [conversationId, currentConversationId, dispatch]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <>
      <main className="flex-1 overflow-y-auto py-6 px-6">
        <div className="max-w-[720px] mx-auto">
          {messagesLoading ? (
            <div className="flex items-center justify-center py-32">
              <p
                className="text-sm"
                style={{
                  fontFamily: "var(--font-serif)",
                  color: "var(--text-secondary)",
                }}
              >
                대화를 불러오는 중...
              </p>
            </div>
          ) : (
            <div className="flex flex-col gap-7 py-4">
              {messages.map((msg, i) => (
                <MessageBubble key={i} message={msg} />
              ))}
              {error && (
                <p
                  className="text-xs text-center"
                  style={{ color: "var(--accent)" }}
                >
                  {error}
                </p>
              )}
              <div ref={bottomRef} />
            </div>
          )}
        </div>
      </main>

      <footer
        className="py-4 px-6 shrink-0"
        style={{ borderTop: "1px solid var(--border-color)" }}
      >
        <div className="max-w-[720px] mx-auto">
          <ChatInput onSend={sendMessage} disabled={isStreaming} />
        </div>
      </footer>
    </>
  );
}
