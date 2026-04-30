import type { NarrationScene } from "./types";

export const ep1Screen2Summit: NarrationScene = {
  screenId: "ep1_screen2_summit",
  enableHaeseol: true,
  illustration: "/illustrations/screen_02_prologue_summit.webp",
  alt: "산 정상 동굴 앞 인물의 뒷모습과 떠오르는 해",
  paragraphs: [
    {
      kind: "narration",
      text: "서른 살이 되었을 때, 그는 고향과 고향의 호수를 떠나 산으로 들어갔다.",
    },
    {
      kind: "narration",
      text: "그곳에서 그는 자신의 정신과 고독을 즐겼다.\n열 해 동안 그는 지치지 않았다.",
    },
    {
      kind: "narration",
      text: "그러나 마침내 그의 마음에 변화가 일어났다.\n어느 날 새벽, 그는 떠오르는 해와 함께 일어나\n그 앞에 마주서서 말했다 —",
    },
    {
      kind: "quote",
      text: "“위대한 별이여, 그대가 비추어 줄 자들이 없다면\n그대의 행복이란 무엇인가.”",
    },
    {
      kind: "narration",
      text: "그는 다시 인간이 되어야 한다.\n**산을 내려가야 한다.**",
    },
  ],
};
