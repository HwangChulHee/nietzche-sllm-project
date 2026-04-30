/**
 * uiSlice — 페이드 / 토스트 / 모달 등 작품 결을 가로지르는 UI 부착물.
 *
 * VN_UI_POLICY §6.4: 모달/토스트 톤은 평이한 시스템 톤.
 */

import { createSlice, PayloadAction } from "@reduxjs/toolkit";

export type FadeState = "idle" | "out" | "in";

export interface ToastState {
  message: string;
  visibleUntil: number;
}

export interface ModalState {
  kind: "save_overwrite" | "load_slot" | "load_empty";
  data?: unknown;
}

interface UiState {
  fade: FadeState;
  toast: ToastState | null;
  modal: ModalState | null;
}

const initialState: UiState = {
  fade: "idle",
  toast: null,
  modal: null,
};

const uiSlice = createSlice({
  name: "ui",
  initialState,
  reducers: {
    setFade(state, action: PayloadAction<FadeState>) {
      state.fade = action.payload;
    },
    showToast(
      state,
      action: PayloadAction<{ message: string; durationMs?: number }>,
    ) {
      state.toast = {
        message: action.payload.message,
        visibleUntil: Date.now() + (action.payload.durationMs ?? 1800),
      };
    },
    hideToast(state) {
      state.toast = null;
    },
    showModal(state, action: PayloadAction<ModalState>) {
      state.modal = action.payload;
    },
    hideModal(state) {
      state.modal = null;
    },
  },
});

export const { setFade, showToast, hideToast, showModal, hideModal } =
  uiSlice.actions;
export default uiSlice.reducer;
