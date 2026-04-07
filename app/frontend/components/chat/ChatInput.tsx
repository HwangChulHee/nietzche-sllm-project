"use client";

import { useState, KeyboardEvent } from "react";

interface Props {
  onSend: (message: string) => void;
  disabled?: boolean;
}

export function ChatInput({ onSend, disabled }: Props) {
  const [value, setValue] = useState("");

  const handleSend = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex gap-3 items-end">
      <textarea
        placeholder="심연에게 질문하십시오..."
        className="flex-1 resize-none px-4 py-3 text-base outline-none"
        style={{
          fontFamily: "var(--font-serif)",
          backgroundColor: "var(--bg-secondary)",
          color: "var(--text-primary)",
          border: "1px solid var(--border-color)",
          borderRadius: "2px",
          minHeight: "48px",
          maxHeight: "120px",
        }}
        rows={1}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={disabled}
      />
      <button
        className="px-6 py-3 text-sm"
        style={{
          fontFamily: "var(--font-serif)",
          backgroundColor: disabled || !value.trim() ? "var(--border-color)" : "var(--accent)",
          color: disabled || !value.trim() ? "var(--text-secondary)" : "#f4f1ea",
          border: "none",
          borderRadius: "2px",
          cursor: disabled || !value.trim() ? "not-allowed" : "pointer",
        }}
        onClick={handleSend}
        disabled={disabled || !value.trim()}
      >
        {disabled ? "응답 중..." : "전송"}
      </button>
    </div>
  );
}
