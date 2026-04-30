"use client";

import { useAppSelector } from "@/lib/hooks/useAppDispatch";

/**
 * TransitionOverlay — 화면 전환 시 풀스크린 검은 페이드 오버레이.
 *
 * 시퀀스 (useNavigate):
 *   setFade("out") → 오버레이 페이드인 600ms (검정으로 덮음)
 *   → router.push → 새 페이지 vn-fade-in 시작
 *   → setFade("idle") → 오버레이 페이드아웃 600ms (페이지가 드러남)
 */
export function TransitionOverlay() {
  const fade = useAppSelector((s) => s.ui.fade);
  return (
    <div
      className={`vn-transition ${fade === "out" ? "vn-transition--opaque" : ""}`}
      aria-hidden="true"
    />
  );
}
