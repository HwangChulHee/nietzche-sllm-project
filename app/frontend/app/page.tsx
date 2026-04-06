"use client";

import { useEffect, useRef, useState } from "react";
import { Quote } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { MessageBubble } from "@/components/chat/MessageBubble";
import { ChatInput } from "@/components/chat/ChatInput";
import { RoomList } from "@/components/chat/RoomList";
import { useAppDispatch, useAppSelector } from "@/lib/hooks/useAppDispatch";
import { initUser, setAuth } from "@/lib/store/chatSlice";
import { useStreamingChat } from "@/lib/hooks/useStreamingChat";

const USER_ID_KEY = "nietzsche_user_id";
const USER_TOKEN_KEY = "nietzsche_token";

export default function Home() {
  const dispatch = useAppDispatch();
  const { messages, isStreaming, error, token } = useAppSelector((s) => s.chat);
  const { sendMessage } = useStreamingChat();
  const bottomRef = useRef<HTMLDivElement>(null);
  const [ready, setReady] = useState(false);

  // 사용자 초기화: localStorage에 저장된 토큰 재사용 또는 신규 생성
  useEffect(() => {
    const storedId = localStorage.getItem(USER_ID_KEY);
    const storedToken = localStorage.getItem(USER_TOKEN_KEY);

    if (storedId && storedToken) {
      dispatch(setAuth({ id: storedId, token: storedToken }));
      setReady(true);
    } else {
      const guestName = `guest_${Date.now()}`;
      const guestPassword = Math.random().toString(36).slice(2) + "aA1!";
      dispatch(initUser({ name: guestName, password: guestPassword })).then(
        (action) => {
          if (initUser.fulfilled.match(action)) {
            localStorage.setItem(USER_ID_KEY, action.payload.id);
            localStorage.setItem(USER_TOKEN_KEY, action.payload.token);
          }
          setReady(true);
        },
      );
    }
  }, [dispatch]);

  // 새 메시지가 오면 스크롤 하단으로
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const isEmpty = messages.length === 0;

  return (
    <div className="flex h-screen bg-background text-foreground">
      {/* 사이드바 — 채팅방 목록 */}
      {ready && <RoomList />}

      {/* 메인 채팅 영역 */}
      <div className="flex flex-1 flex-col min-w-0">
        {/* 헤더 */}
        <header className="flex flex-col items-center justify-center border-b py-6 shrink-0">
          <Quote className="mb-1 h-6 w-6 opacity-40" />
          <h1 className="text-xl font-bold tracking-tight font-serif">
            Friedrich Nietzsche
          </h1>
          <p className="text-xs text-muted-foreground italic">
            "나의 시대는 아직 오지 않았다."
          </p>
        </header>

        {/* 메시지 목록 */}
        <main className="flex-1 overflow-hidden p-4">
          <ScrollArea className="h-full max-w-2xl mx-auto">
            {isEmpty ? (
              <div className="flex flex-col items-center justify-center h-full py-20 gap-3 text-muted-foreground">
                <Quote className="h-10 w-10 opacity-20" />
                <p className="text-sm italic font-serif">
                  무엇이 그대를 심연으로 이끌었는가?
                </p>
              </div>
            ) : (
              <div className="space-y-6 py-4">
                {messages.map((msg, i) => (
                  <MessageBubble key={i} message={msg} />
                ))}
                {error && (
                  <p className="text-xs text-red-500 text-center">{error}</p>
                )}
                <div ref={bottomRef} />
              </div>
            )}
          </ScrollArea>
        </main>

        {/* 입력 영역 */}
        <footer className="border-t p-4 shrink-0">
          <div className="max-w-2xl mx-auto">
            <ChatInput onSend={sendMessage} disabled={isStreaming || !ready} />
          </div>
        </footer>
      </div>
    </div>
  );
}
