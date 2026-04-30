"use client";

import { useEffect, useState } from "react";
import { BackButton } from "./BackButton";
import { Frame } from "./Frame";
import { IllustrationLayer } from "./IllustrationLayer";

export type EndingAction = {
  label: string;
  onClick: () => void;
};

type Props = {
  episode: string;
  title: string;
  body: string[];
  illustration: string;
  alt: string;
  actions: EndingAction[];
  onBack: () => void;
};

type Stage = "illust_only" | "text_fading_in" | "text_idle" | "menu_fading_in" | "menu_idle";

const ILLUST_HOLD_MS = 5000;
const TEXT_FADE_MS = 900;
const MENU_DELAY_MS = 3000;
const MENU_FADE_MS = 900;

export function EndingCard({
  episode,
  title,
  body,
  illustration,
  alt,
  actions,
  onBack,
}: Props) {
  const [stage, setStage] = useState<Stage>("illust_only");

  useEffect(() => {
    const timers: number[] = [];
    timers.push(
      window.setTimeout(() => setStage("text_fading_in"), ILLUST_HOLD_MS),
    );
    timers.push(
      window.setTimeout(() => setStage("text_idle"), ILLUST_HOLD_MS + TEXT_FADE_MS),
    );
    timers.push(
      window.setTimeout(
        () => setStage("menu_fading_in"),
        ILLUST_HOLD_MS + TEXT_FADE_MS + MENU_DELAY_MS,
      ),
    );
    timers.push(
      window.setTimeout(
        () => setStage("menu_idle"),
        ILLUST_HOLD_MS + TEXT_FADE_MS + MENU_DELAY_MS + MENU_FADE_MS,
      ),
    );
    return () => timers.forEach(window.clearTimeout);
  }, []);

  const textVisible = stage !== "illust_only";
  const menuVisible = stage === "menu_fading_in" || stage === "menu_idle";

  return (
    <Frame>
      <div className="vn-ending">
        <IllustrationLayer
          imagePath={illustration}
          alt={alt}
          mode="fullscreen"
          priority
        />
        <div className="vn-ending__veil" aria-hidden="true" />

        <BackButton onClick={onBack} disabled={!menuVisible} />

        <div
          className={`vn-ending__text ${textVisible ? "vn-ending__text--visible" : ""}`}
          aria-hidden={!textVisible}
        >
          <div className="vn-ending__episode">{episode}</div>
          <h1 className="vn-ending__title">{title}</h1>
          <div className="vn-ending__divider">─────────────</div>
          <div className="vn-ending__body">
            {body.map((line, i) => (
              <p key={i}>{line}</p>
            ))}
          </div>
        </div>

        <div
          className={`vn-ending__menu ${menuVisible ? "vn-ending__menu--visible" : ""}`}
          aria-hidden={!menuVisible}
        >
          {actions.map((a) => (
            <button
              key={a.label}
              type="button"
              className="vn-ending__action"
              onClick={a.onClick}
              disabled={!menuVisible}
            >
              {a.label}
            </button>
          ))}
        </div>
      </div>
    </Frame>
  );
}
