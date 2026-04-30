/**
 * episodeSlice — 현재 에피소드 / 화면 인덱스 / 모드.
 *
 * 라우터 변경과 동기화. URL이 single source of truth이고
 * 이 slice는 페이지 컴포넌트가 mount 시 dispatch하는 미러.
 */

import { createSlice, PayloadAction } from "@reduxjs/toolkit";

export type Episode = "ep1" | "ep2";
export type Mode = "title" | "narration" | "interaction" | "ending" | "transition";

interface EpisodeState {
  episode: Episode | null;
  sceneIndex: number | null;
  mode: Mode;
}

const initialState: EpisodeState = {
  episode: null,
  sceneIndex: null,
  mode: "title",
};

const episodeSlice = createSlice({
  name: "episode",
  initialState,
  reducers: {
    enterScene(
      state,
      action: PayloadAction<{ episode: Episode; sceneIndex: number; mode: Mode }>,
    ) {
      state.episode = action.payload.episode;
      state.sceneIndex = action.payload.sceneIndex;
      state.mode = action.payload.mode;
    },
    enterTitle(state) {
      state.episode = null;
      state.sceneIndex = null;
      state.mode = "title";
    },
    enterTransition(state) {
      state.mode = "transition";
    },
    enterEnding(state, action: PayloadAction<{ episode: Episode }>) {
      state.episode = action.payload.episode;
      state.mode = "ending";
    },
  },
});

export const { enterScene, enterTitle, enterTransition, enterEnding } =
  episodeSlice.actions;
export default episodeSlice.reducer;
