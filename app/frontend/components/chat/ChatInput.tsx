"use client";

import { useState, KeyboardEvent } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

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

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex gap-3">
      <Input
        placeholder="심연에게 질문하십시오..."
        className="flex-1 bg-zinc-100 dark:bg-zinc-800 border-none focus-visible:ring-1"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={disabled}
      />
      <Button
        variant="default"
        className="px-6"
        onClick={handleSend}
        disabled={disabled || !value.trim()}
      >
        {disabled ? "응답 중..." : "전송"}
      </Button>
    </div>
  );
}
