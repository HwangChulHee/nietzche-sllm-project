"use client";

import { useCallback } from "react";
import { useAppDispatch, useAppSelector } from "./useAppDispatch";
import {
  addUserMessage,
  appendToken,
  finalizeAssistantMessage,
  fetchRooms,
  setStreamingError,
  startAssistantMessage,
} from "../store/chatSlice";

const API_BASE = "http://localhost:8000";

export function useStreamingChat() {
  const dispatch = useAppDispatch();
  const { token, currentRoomId, isStreaming } = useAppSelector((s) => s.chat);

  const sendMessage = useCallback(
    async (message: string) => {
      if (!token || isStreaming || !message.trim()) return;

      dispatch(addUserMessage(message));
      dispatch(startAssistantMessage());

      try {
        const res = await fetch(`${API_BASE}/api/v1/chat/`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            message,
            ...(currentRoomId ? { room_id: currentRoomId } : {}),
          }),
        });

        if (!res.ok || !res.body) {
          throw new Error(`HTTP ${res.status}`);
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let roomId = currentRoomId ?? "";
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() ?? "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            try {
              const event = JSON.parse(line.slice(6));
              if (event.type === "init") {
                roomId = event.room_id;
              } else if (event.type === "token") {
                dispatch(appendToken(event.text));
              } else if (event.type === "done") {
                dispatch(finalizeAssistantMessage({ roomId }));
                dispatch(fetchRooms(token));
              } else if (event.type === "error") {
                dispatch(setStreamingError(event.text));
              }
            } catch {
              // 파싱 실패 시 skip
            }
          }
        }
      } catch (err) {
        dispatch(setStreamingError("응답을 가져오지 못했습니다."));
        console.error("SSE 오류:", err);
      }
    },
    [token, currentRoomId, isStreaming, dispatch],
  );

  return { sendMessage };
}
