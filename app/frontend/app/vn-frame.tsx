"use client";

import { usePathname } from "next/navigation";

/**
 * VnFrame — 모든 라우트의 공통 컨테이너.
 *
 * - 16:10 frame은 Phase 5(책 삽화 레이아웃)에서 본격 적용. Phase 3는 풀 vh.
 * - 라우트 변경 시 children에 key={pathname}로 강제 remount → CSS `vn-fade-in` 재실행.
 * - `#4 → #5` 800ms는 페이지 컴포넌트가 자체 클래스로 처리 (Phase 5).
 */
export function VnFrame({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  return (
    <div className="vn-frame">
      <div key={pathname} className="vn-page">
        {children}
      </div>
    </div>
  );
}
