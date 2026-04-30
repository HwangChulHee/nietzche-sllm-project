"use client";

import { Frame } from "./Frame";
import { IllustrationLayer } from "./IllustrationLayer";

type Props = {
  onStart: () => void;
  onLoad: () => void;
  onExit: () => void;
  hasSavedSlot: boolean;
  illustration: string;
  alt: string;
};

export function TitleScreen({
  onStart,
  onLoad,
  onExit,
  hasSavedSlot,
  illustration,
  alt,
}: Props) {
  return (
    <Frame>
      <div className="vn-title">
        <IllustrationLayer
          imagePath={illustration}
          alt={alt}
          mode="fullscreen"
          priority
        />
        <div className="vn-title__veil" aria-hidden="true" />

        <div className="vn-title__content">
          <h1 className="vn-title__main">차라투스트라</h1>
          <p className="vn-title__sub">EPISODE 1 — 하산</p>

          <div className="vn-title__menu">
            <button type="button" className="vn-title__action" onClick={onStart}>
              [ 시 작 ]
            </button>
            <button
              type="button"
              className="vn-title__action"
              onClick={onLoad}
              disabled={!hasSavedSlot}
            >
              [ 불 러 오 기 ]
            </button>
            <button type="button" className="vn-title__action" onClick={onExit}>
              [ 종 료 ]
            </button>
          </div>

          <blockquote className="vn-title__quote">
            “그대들에게 인간이란 무엇인가? 극복되어야 할 무엇이다.”
            <footer>— 『차라투스트라는 이렇게 말했다』</footer>
          </blockquote>
        </div>
      </div>
    </Frame>
  );
}
