"use client";

import { usePathname } from "next/navigation";

/**
 * VnFrame — 모든 라우트의 공통 컨테이너.
 *
 * - viewport 풀스크린 검은 배경(letterbox).
 * - 안쪽 vn-page 박스가 16:10 캔버스. CSS aspect-ratio + max-width/height
 *   조합으로 viewport 비율에 따라 가운데 정렬 자동.
 * - 라우트 변경 시 children에 key={pathname}로 강제 remount → CSS
 *   `vn-fade-in` 재실행 (600ms 기본 / `#4 → #5` 진입은 800ms).
 */

const SLOW_FADE_PATHS = new Set<string>([
  "/ep1/scene/5", // 분위기 전환점 (VN_UI_POLICY §2.4)
]);

export function VnFrame({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isSlow = SLOW_FADE_PATHS.has(pathname);
  return (
    <div className="vn-frame">
      <div
        key={pathname}
        className={`vn-page ${isSlow ? "vn-page--slow" : ""}`}
      >
        {children}
      </div>
    </div>
  );
}
