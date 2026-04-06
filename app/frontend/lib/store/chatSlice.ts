import { createSlice, createAsyncThunk, PayloadAction } from "@reduxjs/toolkit";

const API_BASE = "http://localhost:8000";

// ─── Types ───────────────────────────────────────────

export interface Message {
  id?: number;
  role: "user" | "assistant";
  content: string;
  streaming?: boolean;
}

export interface ChatRoom {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

interface ChatState {
  userId: string | null;
  token: string | null;
  rooms: ChatRoom[];
  currentRoomId: string | null;
  messages: Message[];
  isStreaming: boolean;
  error: string | null;
}

// ─── Initial state ───────────────────────────────────

const initialState: ChatState = {
  userId: null,
  token: null,
  rooms: [],
  currentRoomId: null,
  messages: [],
  isStreaming: false,
  error: null,
};

// ─── Thunks ──────────────────────────────────────────

export const initUser = createAsyncThunk(
  "chat/initUser",
  async ({ name, password }: { name: string; password: string }) => {
    const res = await fetch(`${API_BASE}/api/v1/user/signup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, password }),
    });
    if (!res.ok) throw new Error("사용자 생성 실패");
    const data = await res.json();
    return { id: data.id as string, token: data.token as string };
  },
);

export const loginUser = createAsyncThunk(
  "chat/loginUser",
  async ({ name, password }: { name: string; password: string }) => {
    const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, password }),
    });
    if (!res.ok) throw new Error("로그인 실패");
    const data = await res.json();
    return { id: data.id as string, token: data.token as string };
  },
);

export const fetchRooms = createAsyncThunk(
  "chat/fetchRooms",
  async (token: string) => {
    const res = await fetch(`${API_BASE}/api/v1/chat/rooms`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error("채팅방 목록 로드 실패");
    return (await res.json()) as ChatRoom[];
  },
);

export const fetchMessages = createAsyncThunk(
  "chat/fetchMessages",
  async ({ roomId, token }: { roomId: string; token: string }) => {
    const res = await fetch(
      `${API_BASE}/api/v1/chat/rooms/${roomId}/messages`,
      { headers: { Authorization: `Bearer ${token}` } },
    );
    if (!res.ok) throw new Error("메시지 로드 실패");
    return (await res.json()) as Message[];
  },
);

export const deleteRoom = createAsyncThunk(
  "chat/deleteRoom",
  async ({ roomId, token }: { roomId: string; token: string }) => {
    const res = await fetch(`${API_BASE}/api/v1/chat/rooms/${roomId}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error("채팅방 삭제 실패");
    return roomId;
  },
);

// ─── Slice ───────────────────────────────────────────

const chatSlice = createSlice({
  name: "chat",
  initialState,
  reducers: {
    setAuth(state, action: PayloadAction<{ id: string; token: string }>) {
      state.userId = action.payload.id;
      state.token = action.payload.token;
    },
    setCurrentRoom(state, action: PayloadAction<string | null>) {
      state.currentRoomId = action.payload;
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
    appendToken(state, action: PayloadAction<string>) {
      const last = state.messages[state.messages.length - 1];
      if (last?.streaming) {
        last.content += action.payload;
      }
    },
    finalizeAssistantMessage(state, action: PayloadAction<{ roomId: string }>) {
      const last = state.messages[state.messages.length - 1];
      if (last?.streaming) {
        last.streaming = false;
      }
      state.isStreaming = false;
      state.currentRoomId = action.payload.roomId;
    },
    setStreamingError(state, action: PayloadAction<string>) {
      state.isStreaming = false;
      const last = state.messages[state.messages.length - 1];
      if (last?.streaming) {
        state.messages.pop();
      }
      state.error = action.payload;
    },
    clearMessages(state) {
      state.messages = [];
      state.currentRoomId = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(initUser.fulfilled, (state, action) => {
        state.userId = action.payload.id;
        state.token = action.payload.token;
      })
      .addCase(loginUser.fulfilled, (state, action) => {
        state.userId = action.payload.id;
        state.token = action.payload.token;
      })
      .addCase(fetchRooms.fulfilled, (state, action) => {
        state.rooms = action.payload;
      })
      .addCase(fetchMessages.fulfilled, (state, action) => {
        state.messages = action.payload;
        state.isStreaming = false;
      })
      .addCase(deleteRoom.fulfilled, (state, action) => {
        state.rooms = state.rooms.filter((r) => r.id !== action.payload);
        if (state.currentRoomId === action.payload) {
          state.currentRoomId = null;
          state.messages = [];
        }
      });
  },
});

export const {
  setAuth,
  setCurrentRoom,
  addUserMessage,
  startAssistantMessage,
  appendToken,
  finalizeAssistantMessage,
  setStreamingError,
  clearMessages,
} = chatSlice.actions;

export default chatSlice.reducer;
