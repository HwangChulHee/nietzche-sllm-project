export type HaeseolQuote = {
  text: string;
  explanation: string;
};

export type HaeseolEntry = {
  screenId: string;
  title: string;
  oneLineSummary: string;
  quotes: HaeseolQuote[];
};
