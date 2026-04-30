"use client";

/**
 * Frame — 책 삽화 레이아웃의 16:10 캔버스.
 *
 * VnFrame이 letterbox(viewport 검은 띠)를 처리하고, 그 안에 들어가는
 * 16:10 캔버스가 Frame이다. IllustrationLayer / TextLayer / 인터랙션
 * 슬롯은 모두 Frame 안에 absolute positioning으로 자유 배치.
 */
export function Frame({ children }: { children: React.ReactNode }) {
  return <div className="vn-book">{children}</div>;
}
