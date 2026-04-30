import type { NarrationScene } from "./types";

export const ep1Screen4Road: NarrationScene = {
  screenId: "ep1_screen4_road",
  enableHaeseol: true,
  slowFade: true,
  illustration: "/illustrations/screen_04_prologue_road.webp",
  alt: "혼자 멀어지는 차라투스트라의 뒷모습과 광활한 앞길",
  paragraphs: [
    {
      kind: "narration",
      text: "홀로 길을 걸으며, 차라투스트라는 자신의 마음에 대고 말했다 —",
    },
    {
      kind: "quote",
      text: "“이럴 수가 있는가.\n저 늙은 성자는 숲 속에서\n**신이 죽었다는 소식**을 아직 듣지 못했구나.”",
    },
    {
      kind: "narration",
      text: "그는 길을 걸었다.\n시장이 그의 앞에 있었다.",
    },
  ],
};
