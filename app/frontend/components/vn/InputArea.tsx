"use client";

import { useEffect, useRef, useState } from "react";
import type { StreamingState } from "@/lib/store/dialogueSlice";

const MAX_CHARS = 500;
const WARN_CHARS = 450;
const TEXTAREA_MAX_PX = 120;

type Props = {
  streamingState: StreamingState;
  canTransition: boolean;
  transitionLabel: string;
  onSend: (text: string) => void;
  onSilent: () => void;
  onTransition: () => void;
};

export function InputArea({
  streamingState,
  canTransition,
  transitionLabel,
  onSend,
  onSilent,
  onTransition,
}: Props) {
  const [value, setValue] = useState("");
  const taRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const ta = taRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = `${Math.min(ta.scrollHeight, TEXTAREA_MAX_PX)}px`;
  }, [value]);

  const inFlight = streamingState !== "idle";
  const len = value.length;
  const tooLong = len > MAX_CHARS;
  const sendable = !inFlight && value.trim().length > 0 && !tooLong;

  const handleSend = () => {
    if (!sendable) return;
    onSend(value);
    setValue("");
  };

  const handleKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const counterClass =
    `vn-input__counter` +
    (tooLong ? " vn-input__counter--over" : len > WARN_CHARS ? " vn-input__counter--warn" : "");

  return (
    <div className="vn-input">
      <div className="vn-input__row">
        <textarea
          ref={taRef}
          className="vn-input__textarea"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKey}
          placeholder={inFlight ? "…" : "입력..."}
          disabled={inFlight}
          rows={1}
        />
        <span className={counterClass}>
          {len} / {MAX_CHARS}
        </span>
      </div>
      <div className="vn-input__actions">
        <div className="vn-input__actions-left">
          <button
            type="button"
            className="vn-input__btn vn-input__btn--primary"
            onClick={handleSend}
            disabled={!sendable}
          >
            발화하기
          </button>
          <button
            type="button"
            className="vn-input__btn"
            onClick={onSilent}
            disabled={inFlight}
          >
            침묵
          </button>
        </div>
        <button
          type="button"
          className="vn-input__transition"
          onClick={onTransition}
          disabled={!canTransition}
        >
          {transitionLabel}
        </button>
      </div>
    </div>
  );
}
