"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Frame } from "./Frame";
import { IllustrationLayer } from "./IllustrationLayer";
import type { Paragraph } from "@/data/scenes/types";
import { showToast } from "@/lib/store/uiSlice";
import { useAppDispatch } from "@/lib/hooks/useAppDispatch";

const FADE_MS = 290;

type Props = {
  paragraphs: Paragraph[];
  enableHaeseol: boolean;
  illustration: string;
  alt: string;
  onComplete: () => void;
};

type Phase = "in" | "idle" | "out" | "exit";

export function NarrationScreen({
  paragraphs,
  enableHaeseol,
  illustration,
  alt,
  onComplete,
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

        <div className="vn-narration__textbox">
          <p
            className={`vn-narration__text ${
              para.kind === "quote" ? "vn-narration__text--quote" : ""
            } ${fading ? "vn-narration__text--fading" : ""}`}
          >
            {para.text}
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
