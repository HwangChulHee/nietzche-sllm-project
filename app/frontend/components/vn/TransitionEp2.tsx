"use client";

import { useEffect } from "react";

import { useNavigate } from "@/lib/hooks/useNavigate";

const TEXT_FADE_IN_DELAY_MS = 200;
const TEXT_HOLD_MS = 3000;
const TEXT_FADE_IN_MS = 600;

/**
 * TransitionEp2 — Ep 1 → Ep 2 카운드오버 (VN_UI_POLICY §6.5).
 *
 * 시퀀스:
 *   진입(useNavigate 검은 페이드아웃 → vn-page fade-in)
 *   → 200ms 정적
 *   → 잉크 옅은 글씨 페이드인 600ms
 *   → 3000ms 정적
 *   → useNavigate("/ep2/scene/1")  (검은 페이드인 600ms → 라우팅 → 새 페이지)
 *
 * 백그라운드 요약 sLLM 호출은 Phase 9로 미룸. 현재는 시각만.
 */
export function TransitionEp2() {
  const navigate = useNavigate();

  useEffect(() => {
    const t = window.setTimeout(
      () => navigate("/ep2/scene/1"),
      TEXT_FADE_IN_DELAY_MS + TEXT_FADE_IN_MS + TEXT_HOLD_MS,
    );
    return () => window.clearTimeout(t);
  }, [navigate]);

  return (
    <div className="vn-transition-ep2">
      <p className="vn-transition-ep2__text">
        밤이 깊었다.
        <br />
        시간은 흘러, 시장의 새벽이 왔다.
      </p>
    </div>
  );
}
