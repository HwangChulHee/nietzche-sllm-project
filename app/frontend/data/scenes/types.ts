export type Paragraph = {
  text: string;
  kind?: "narration" | "quote";
};

export type NarrationScene = {
  screenId: string;
  paragraphs: Paragraph[];
  enableHaeseol: boolean;
  slowFade?: boolean;
};

export type EndingCardData = {
  screenId: string;
  episode: string;
  title: string;
  body: string[];
};
