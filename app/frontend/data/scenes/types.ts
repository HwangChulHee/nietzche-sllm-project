export type Paragraph = {
  text: string;
  kind?: "narration" | "quote";
};

export type NarrationScene = {
  screenId: string;
  paragraphs: Paragraph[];
  enableHaeseol: boolean;
  slowFade?: boolean;
  illustration: string;
  alt: string;
};

export type EndingCardData = {
  screenId: string;
  episode: string;
  title: string;
  body: string[];
  illustration: string;
  alt: string;
};

/**
 * 인터랙션 화면(#5~#7, Ep 2 #4) 메타데이터.
 *
 * - firstUtterance.kind === "fixed": 고정 발화 텍스트로 진입 (sLLM 호출 X).
 *   #5 만남이 유일 (EP1_TEXT_AND_PROMPTS §#5 안정성 명시).
 * - firstUtterance.kind === "auto":  /api/v1/respond/auto 호출.
 * - farewell === true: 화면 전환 버튼 클릭 시 /respond/farewell 호출 흐름.
 *   #7 시장 원경 + Ep 2 #4 학습자 재회.
 */
export type InteractionScene = {
  screenId: string;
  illustration: string;
  alt: string;
  transitionLabel: string;
  firstUtterance:
    | { kind: "fixed"; text: string }
    | { kind: "auto" };
  farewell: boolean;
};
