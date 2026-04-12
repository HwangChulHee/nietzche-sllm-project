"use client";

import { useState, KeyboardEvent, useRef, useEffect } from "react";
import { ArrowUp } from "lucide-react";
import { useAppSelector } from "@/lib/hooks/useAppDispatch";
import { useStreamingChat } from "@/lib/hooks/useStreamingChat";

export function ChatInput() {
  const [value, setValue] = useState("");
  const { isStreaming } = useAppSelector((s) => s.chat);
  const { sendMessage } = useStreamingChat();
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [isFocused, setIsFocused] = useState(false);

  const disabled = isStreaming;
  const isActive = !disabled && value.trim().length > 0;

  // textarea 자동 높이 조절
  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    const newHeight = Math.min(ta.scrollHeight, 200);
    ta.style.height = `${newHeight}px`;
  }, [value]);

  const handleSend = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    sendMessage(trimmed);
    setValue("");
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div
      ref={containerRef}
      style={{
        display: "flex",
        flexDirection: "column",
        backgroundColor: "#ffffff",
        border: `1.5px solid ${isFocused ? "var(--accent)" : "var(--border-color)"}`,
        borderRadius: "6px",
        padding: "14px 16px 12px",
        transition: "border-color 0.15s ease, box-shadow 0.15s ease",
        boxShadow: isFocused
          ? "0 1px 3px rgba(44, 36, 22, 0.06), 0 0 0 3px rgba(139, 46, 31, 0.06)"
          : "0 1px 2px rgba(44, 36, 22, 0.04)",
      }}
    >
      <textarea
        ref={textareaRef}
        placeholder="니체에게 질문하십시오..."
        rows={1}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        onFocus={() => setIsFocused(true)}
        onBlur={() => setIsFocused(false)}
        disabled={disabled}
        style={{
          width: "100%",
          resize: "none",
          border: "none",
          outline: "none",
          padding: "0",
          fontSize: "16px",
          lineHeight: "1.7",
          fontFamily: "var(--font-serif)",
          backgroundColor: "transparent",
          color: "var(--text-primary)",
          minHeight: "28px",
          maxHeight: "200px",
          overflowY: "auto",
        }}
      />

      <div
        style={{
          display: "flex",
          justifyContent: "flex-end",
          marginTop: "8px",
        }}
      >
        <button
          onClick={handleSend}
          disabled={!isActive}
          aria-label="전송"
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            width: "34px",
            height: "34px",
            backgroundColor: isActive ? "var(--accent)" : "#d8d2c2",
            color: isActive ? "#f4f1ea" : "#8a7f6e",
            border: "none",
            borderRadius: "50%",
            cursor: isActive ? "pointer" : "not-allowed",
            transition: "background-color 0.15s ease",
            flexShrink: 0,
          }}
          onMouseEnter={(e) => {
            if (isActive) {
              e.currentTarget.style.backgroundColor = "#6d2418";
            }
          }}
          onMouseLeave={(e) => {
            if (isActive) {
              e.currentTarget.style.backgroundColor = "var(--accent)";
            }
          }}
        >
          <ArrowUp size={18} strokeWidth={2.5} />
        </button>
      </div>
    </div>
  );
}
