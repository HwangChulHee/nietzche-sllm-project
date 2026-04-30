import type { InteractionScene } from "./types";

export const ep1Screen5Meeting: InteractionScene = {
  screenId: "ep1_screen5_meeting",
  illustration: "/illustrations/screen_05_meeting.webp",
  alt: "두 인물이 마주보는 길의 교차점",
  transitionLabel: "[그와 함께 걷는다 →]",
  firstUtterance: {
    kind: "fixed",
    text: "그대.\n어디서 왔는가.",
  },
  farewell: false,
};
