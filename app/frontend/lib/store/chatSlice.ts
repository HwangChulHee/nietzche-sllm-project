import { createSlice, createAsyncThunk, PayloadAction } from "@reduxjs/toolkit";

const API_BASE = "http://localhost:8000";

// ─── Types ───────────────────────────────────────────

export interface Message {
  id?: string;
  role: "user" | "assistant";
  content: string;
  streaming?: boolean;
  created_at?: string;
}

interface ChatState {
  currentConversationId: string | null;
  messages: Message[];
  isStreaming: boolean;
  error: string | null;
}

// ─── Initial state ───────────────────────────────────

const initialState: ChatState = {
  currentConversationId: null,
  messages: [],
  isStreaming: false,
  error: null,
};

// ─── Thunks ──────────────────────────────────────────

export const fetchMessages = createAsyncThunk(
  "chat/fetchMessages",
  async (conversationId: string) => {
    const res = await fetch(
      `${API_BASE}/api/v1/conversations/${conversationId}/messages`,
    );
    if (!res.ok) throw new Error("메시지 로드 실패");
    const data = await res.json();
    return data as { conversation_id: string; messages: Message[] };
  },
);

// ─── Slice ───────────────────────────────────────────

const chatSlice = createSlice({
  name: "chat",
  initialState,
  reducers: {
    setConversation(state, action: PayloadAction<string | null>) {
      state.currentConversationId = action.payload;
      state.messages = [];
      state.error = null;
    },
    addUserMessage(state, action: PayloadAction<string>) {
      state.messages.push({ role: "user", content: action.payload });
      state.isStreaming = true;
      state.error = null;
    },
    startAssistantMessage(state) {
      state.messages.push({ role: "assistant", content: "", streaming: true });
    },
    appendDelta(state, action: PayloadAction<string>) {
      const last = state.messages[state.messages.length - 1];
      if (last?.streaming) {
        last.content += action.payload;
      }
    },
    finalizeAssistantMessage(
      state,
      action: PayloadAction<{ conversationId: string }>,
    ) {
      const last = state.messages[state.messages.length - 1];
      if (last?.streaming) {
        last.streaming = false;
      }
      state.isStreaming = false;
      state.currentConversationId = action.payload.conversationId;
    },
    setStreamingError(state, action: PayloadAction<string>) {
      state.isStreaming = false;
      const last = state.messages[state.messages.length - 1];
      if (last?.streaming) {
        state.messages.pop();
      }
      state.error = action.payload;
    },
    clearChat(state) {
      state.messages = [];
      state.currentConversationId = null;
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder.addCase(fetchMessages.fulfilled, (state, action) => {
      state.currentConversationId = action.payload.conversation_id;
      state.messages = action.payload.messages;
      state.isStreaming = false;
    });
  },
});

export const {
  setConversation,
  addUserMessage,
  startAssistantMessage,
  appendDelta,
  finalizeAssistantMessage,
  setStreamingError,
  clearChat,
} = chatSlice.actions;

export default chatSlice.reducer;
