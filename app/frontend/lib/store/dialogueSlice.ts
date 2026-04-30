/**
 * dialogueSlice — 인터랙션 화면(#5~#7, Ep 2 #4) 메시지 누적.
 *
 * 화면 전환 시 messages 초기화 (resetForScreen).
 * `userTurns`는 화면 전환 버튼 활성 조건([침묵]도 1회로 카운트)에 사용.
 */

import { createSlice, PayloadAction } from "@reduxjs/toolkit";

export interface DialogueMessage {
  role: "user" | "assistant";
  content: string;
  isSilent?: boolean;
  streaming?: boolean;
}

export type StreamingState = "idle" | "booting" | "streaming";

interface DialogueState {
  screenId: string | null;
  messages: DialogueMessage[];
  streamingState: StreamingState;
  userTurns: number;
  error: string | null;
}

const initialState: DialogueState = {
  screenId: null,
  messages: [],
  streamingState: "idle",
  userTurns: 0,
  error: null,
};

const dialogueSlice = createSlice({
  name: "dialogue",
  initialState,
  reducers: {
    resetForScreen(state, action: PayloadAction<string>) {
      state.screenId = action.payload;
      state.messages = [];
      state.streamingState = "idle";
      state.userTurns = 0;
      state.error = null;
    },
    addUserMessage(
      state,
      action: PayloadAction<{ content: string; isSilent?: boolean }>,
    ) {
      state.messages.push({
        role: "user",
        content: action.payload.content,
        isSilent: action.payload.isSilent,
      });
      state.userTurns += 1;
      state.error = null;
    },
    startAssistantMessage(state) {
      state.messages.push({ role: "assistant", content: "", streaming: true });
      state.streamingState = "streaming";
    },
    appendDelta(state, action: PayloadAction<string>) {
      const last = state.messages[state.messages.length - 1];
      if (last?.streaming) last.content += action.payload;
    },
    finalizeAssistantMessage(state) {
      const last = state.messages[state.messages.length - 1];
      if (last?.streaming) last.streaming = false;
      state.streamingState = "idle";
    },
    setBooting(state) {
      state.streamingState = "booting";
    },
    setStreamingError(state, action: PayloadAction<string>) {
      const last = state.messages[state.messages.length - 1];
      if (last?.streaming) state.messages.pop();
      state.streamingState = "idle";
      state.error = action.payload;
    },
  },
});

export const {
  resetForScreen,
  addUserMessage,
  startAssistantMessage,
  appendDelta,
  finalizeAssistantMessage,
  setBooting,
  setStreamingError,
} = dialogueSlice.actions;
export default dialogueSlice.reducer;
