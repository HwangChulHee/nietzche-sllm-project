"use client";

type Props = {
  onStart: () => void;
  onLoad: () => void;
  onExit: () => void;
  hasSavedSlot: boolean;
};

export function TitleScreen({ onStart, onLoad, onExit, hasSavedSlot }: Props) {
  return (
    <div className="vn-title">
      <div className="vn-title__illust" aria-hidden="true">
        <div className="vn-title__illust-placeholder" />
      </div>

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
  );
}
