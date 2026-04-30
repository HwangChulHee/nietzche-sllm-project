"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { BackButton } from "./BackButton";
import { Frame } from "./Frame";
import { HaeseolPanel } from "./HaeseolPanel";
import { IllustrationLayer } from "./IllustrationLayer";
import type { Paragraph } from "@/data/scenes/types";
import { useAppDispatch, useAppSelector } from "@/lib/hooks/useAppDispatch";
import { openPanel } from "@/lib/store/haeseolSlice";

const FADE_MS = 600;

/**
 * 본문 안 `**...**` 마크다운식 강조 토큰을 <em class="vn-emph">로 변환.
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
  screenId: string;
  paragraphs: Paragraph[];
  enableHaeseol: boolean;
  illustration: string;
  alt: string;
  onComplete: () => void;
  onBack: () => void;
};

type Phase = "in" | "idle" | "out" | "exit";

export function NarrationScreen({
  screenId,
  paragraphs,
  enableHaeseol,
  illustration,
  alt,
  onComplete,
  onBack,
}: Props) {
  const dispatch = useAppDispatch();
  const haeseolOpen = useAppSelector((s) => s.haeseol.open);
  const [index, setIndex] = useState(0);
  const [phase, setPhase] = useState<Phase>("in");
  const completedRef = useRef(false);

  useEffect(() => {
    if (phase !== "in") return;
    const t = window.setTimeout(() => setPhase("idle"), FADE_MS);
    return () => window.clearTimeout(t);
  }, [phase, index]);

  const advance = useCallback(() => {
    if (haeseolOpen) return; // 해설 패널 열려있으면 진행 차단
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
  }, [haeseolOpen, phase, index, paragraphs.length, onComplete]);

  const goBack = useCallback(() => {
    if (haeseolOpen) return;
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
  }, [haeseolOpen, phase, index, onBack]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (haeseolOpen) return;
      if (e.key === " " || e.key === "Spacebar" || e.key === "Enter") {
        e.preventDefault();
        advance();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [advance, haeseolOpen]);

  const onHaeseolClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    dispatch(openPanel({ screenId }));
  };

  const para = paragraphs[index];
  const showIndicator = phase === "idle" && !haeseolOpen;
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

        <BackButton onClick={goBack} disabled={inFlight || haeseolOpen} />

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

        {enableHaeseol && <HaeseolPanel screenId={screenId} />}
      </div>
    </Frame>
  );
}
