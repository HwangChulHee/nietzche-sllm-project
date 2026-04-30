"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { BackButton } from "./BackButton";
import { Frame } from "./Frame";
import { IllustrationLayer } from "./IllustrationLayer";
import type { Paragraph } from "@/data/scenes/types";
import { showToast } from "@/lib/store/uiSlice";
import { useAppDispatch } from "@/lib/hooks/useAppDispatch";

const FADE_MS = 600;

/**
 * 본문 안 `**...**` 마크다운식 강조 토큰을 <em class="vn-emph">로 변환.
 * 강조 부분 외 텍스트는 그대로 노출. (multiline / 빈 마커 등 edge case는
 * 작성자 책임 — VN 텍스트는 사람이 직접 작성하므로 단순 split로 충분.)
 */
function renderInline(text: string): React.ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*)/g).map((seg, i) => {
    if (seg.startsWith("**") && seg.endsWith("**")) {
      return (
        <em key={i} className="vn-emph">
          {seg.slice(2, -2)}
        </em>
      );
    }
    return <span key={i}>{seg}</span>;
  });
}

type Props = {
  paragraphs: Paragraph[];
  enableHaeseol: boolean;
  illustration: string;
  alt: string;
  onComplete: () => void;
  onBack: () => void;
};

type Phase = "in" | "idle" | "out" | "exit";

export function NarrationScreen({
  paragraphs,
  enableHaeseol,
  illustration,
  alt,
  onComplete,
  onBack,
}: Props) {
  const dispatch = useAppDispatch();
  const [index, setIndex] = useState(0);
  const [phase, setPhase] = useState<Phase>("in");
  const completedRef = useRef(false);

  useEffect(() => {
    if (phase !== "in") return;
    const t = window.setTimeout(() => setPhase("idle"), FADE_MS);
    return () => window.clearTimeout(t);
  }, [phase, index]);

  const advance = useCallback(() => {
    if (phase !== "idle" || completedRef.current) return;
    if (index >= paragraphs.length - 1) {
      completedRef.current = true;
      setPhase("exit");
      window.setTimeout(onComplete, FADE_MS);
      return;
    }
    setPhase("out");
    window.setTimeout(() => {
      setIndex((i) => i + 1);
      setPhase("in");
    }, FADE_MS);
  }, [phase, index, paragraphs.length, onComplete]);

  /** 첫 단락이면 이전 화면, 아니면 한 단락 전. */
  const goBack = useCallback(() => {
    if (phase !== "idle" || completedRef.current) return;
    if (index === 0) {
      onBack();
      return;
    }
    setPhase("out");
    window.setTimeout(() => {
      setIndex((i) => Math.max(0, i - 1));
      setPhase("in");
    }, FADE_MS);
  }, [phase, index, onBack]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === " " || e.key === "Spacebar" || e.key === "Enter") {
        e.preventDefault();
        advance();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [advance]);

  const onHaeseolClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    dispatch(
      showToast({
        message: "[해설] 패널은 Phase 7에서 구현됩니다.",
        durationMs: 1800,
      }),
    );
  };

  const para = paragraphs[index];
  const showIndicator = phase === "idle";
  const fading = phase !== "idle";
  const inFlight = fading;

  return (
    <Frame>
      <div className="vn-narration" onClick={advance} role="presentation">
        <IllustrationLayer
          imagePath={illustration}
          alt={alt}
          mode="narration"
          priority
        />

        <BackButton onClick={goBack} disabled={inFlight} />

        <div className="vn-narration__textbox">
          <p
            className={`vn-narration__text ${
              para.kind === "quote" ? "vn-narration__text--quote" : ""
            } ${fading ? "vn-narration__text--fading" : ""}`}
          >
            {renderInline(para.text)}
          </p>
          <span
            className={`vn-narration__indicator ${
              showIndicator ? "" : "vn-narration__indicator--hidden"
            }`}
            aria-hidden="true"
          >
            ▼
          </span>
        </div>

        {enableHaeseol && (
          <button
            type="button"
            className="vn-narration__haeseol"
            onClick={onHaeseolClick}
            disabled={inFlight}
          >
            [해설]
          </button>
        )}
      </div>
    </Frame>
  );
}
