/**
 * saveSlice — 단일 세이브 슬롯 상태.
 *
 * 백엔드 GET/POST/DELETE /api/v1/save 호출 결과 캐시.
 * Thunk 호출 패턴은 lib/api/save.ts 직접 호출 + dispatch가 더 단순해 reducer만 노출.
 */

import { createSlice, PayloadAction } from "@reduxjs/toolkit";

import type { Episode } from "./episodeSlice";

export interface SaveSlot {
  episode: Episode;
  scene_index: number;
  summary: string;
  recent_messages: { role: "user" | "assistant"; content: string }[];
  timestamp: string;
}

interface SaveState {
  slot: SaveSlot | null;
  loading: boolean;
  saving: boolean;
  error: string | null;
}

const initialState: SaveState = {
  slot: null,
  loading: false,
  saving: false,
  error: null,
};

const saveSlice = createSlice({
  name: "save",
  initialState,
  reducers: {
    setLoading(state, action: PayloadAction<boolean>) {
      state.loading = action.payload;
      state.error = null;
    },
    setSaving(state, action: PayloadAction<boolean>) {
      state.saving = action.payload;
      state.error = null;
    },
    setSlot(state, action: PayloadAction<SaveSlot | null>) {
      state.slot = action.payload;
      state.loading = false;
      state.saving = false;
      state.error = null;
    },
    setSaveError(state, action: PayloadAction<string>) {
      state.loading = false;
      state.saving = false;
      state.error = action.payload;
    },
  },
});

export const { setLoading, setSaving, setSlot, setSaveError } = saveSlice.actions;
export default saveSlice.reducer;
