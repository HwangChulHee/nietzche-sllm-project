/**
 * haeseolSlice — 해설 패널 상태.
 *
 * `open` true일 때 우측 슬라이드 패널이 마운트.
 * `queryHistory`는 [더 깊이 묻기] 누적. 화면 전환 시 reset.
 */

import { createSlice, PayloadAction } from "@reduxjs/toolkit";

export interface HaeseolMessage {
  role: "user" | "assistant";
  content: string;
  streaming?: boolean;
}

interface HaeseolState {
  open: boolean;
  screenId: string | null;
  queryHistory: HaeseolMessage[];
  streaming: boolean;
  error: string | null;
}

const initialState: HaeseolState = {
  open: false,
  screenId: null,
  queryHistory: [],
  streaming: false,
  error: null,
};

const haeseolSlice = createSlice({
  name: "haeseol",
  initialState,
  reducers: {
    openPanel(state, action: PayloadAction<{ screenId: string }>) {
      state.open = true;
      if (state.screenId !== action.payload.screenId) {
        state.screenId = action.payload.screenId;
        state.queryHistory = [];
      }
      state.error = null;
    },
    closePanel(state) {
      state.open = false;
    },
    resetForScreen(state, action: PayloadAction<string>) {
      state.screenId = action.payload;
      state.queryHistory = [];
      state.streaming = false;
      state.error = null;
    },
    addUserQuery(state, action: PayloadAction<string>) {
      state.queryHistory.push({ role: "user", content: action.payload });
      state.error = null;
    },
    startAssistantAnswer(state) {
      state.queryHistory.push({ role: "assistant", content: "", streaming: true });
      state.streaming = true;
    },
    appendDelta(state, action: PayloadAction<string>) {
      const last = state.queryHistory[state.queryHistory.length - 1];
      if (last?.streaming) last.content += action.payload;
    },
    finalizeAnswer(state) {
      const last = state.queryHistory[state.queryHistory.length - 1];
      if (last?.streaming) last.streaming = false;
      state.streaming = false;
    },
    setHaeseolError(state, action: PayloadAction<string>) {
      const last = state.queryHistory[state.queryHistory.length - 1];
      if (last?.streaming) state.queryHistory.pop();
      state.streaming = false;
      state.error = action.payload;
    },
  },
});

export const {
  openPanel,
  closePanel,
  resetForScreen: resetHaeseolForScreen,
  addUserQuery,
  startAssistantAnswer,
  appendDelta: appendHaeseolDelta,
  finalizeAnswer,
  setHaeseolError,
} = haeseolSlice.actions;
export default haeseolSlice.reducer;
