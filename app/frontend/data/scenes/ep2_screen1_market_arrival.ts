import type { NarrationScene } from "./types";

export const ep2Screen1MarketArrival: NarrationScene = {
  screenId: "ep2_screen1_market",
  enableHaeseol: true,
  illustration: "/illustrations/ep2_screen_01_market_arrival.webp",
  alt: "시장 광장에 도착한 차라투스트라와 줄타기 광대를 기다리는 군중",
  paragraphs: [
    {
      kind: "narration",
      text: "차라투스트라가 가까운 마을에 이르렀을 때,\n시장 광장에 군중이 모여 있었다.\n줄타기 광대 한 사람이 곧 보여 줄 것이라는 소문이 돌았다.",
    },
    {
      kind: "narration",
      text: "차라투스트라는 군중을 향해 입을 열었다.",
    },
    {
      kind: "quote",
      text: "“나는 그대들에게 위버멘쉬를 가르치노라.\n인간이란 극복되어야 할 그 무엇이다.\n그대들은 인간을 극복하기 위해 무엇을 했는가.”",
    },
    {
      kind: "narration",
      text: "지금까지 모든 존재는 자신을 넘어서는 무엇을 만들어 왔다.\n그런데 그대들은 이 거대한 밀물의 썰물이 되려 하는가 ―\n인간을 극복하기보다 짐승으로 돌아가려 하는가.",
    },
    {
      kind: "narration",
      text: "군중은 그를 보았다. 그리고 웃었다.\n그가 줄타기 광대를 가리켜 한 말이라고 여긴 것이다.",
    },
  ],
};
