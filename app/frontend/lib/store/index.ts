import { configureStore } from "@reduxjs/toolkit";

import dialogueReducer from "./dialogueSlice";
import episodeReducer from "./episodeSlice";
import haeseolReducer from "./haeseolSlice";
import saveReducer from "./saveSlice";
import uiReducer from "./uiSlice";

export const store = configureStore({
  reducer: {
    episode: episodeReducer,
    dialogue: dialogueReducer,
    haeseol: haeseolReducer,
    save: saveReducer,
    ui: uiReducer,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
