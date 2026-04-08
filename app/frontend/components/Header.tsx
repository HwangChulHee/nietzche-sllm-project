"use client";

import Link from "next/link";
import { useAppDispatch } from "@/lib/hooks/useAppDispatch";
import { clearChat } from "@/lib/store/chatSlice";

export function Header() {
  const dispatch = useAppDispatch();

  return (
    <header
      className="flex items-center justify-between py-8 px-6 shrink-0"
      style={{ borderBottom: "1px solid var(--border-color)" }}
    >
      <div className="flex-1" />
      <div className="flex flex-col items-center">
        <h1
          className="text-2xl tracking-tight"
          style={{ fontFamily: "var(--font-serif)" }}
        >
          니체 페르소나 sLLM 상담
        </h1>
        <p className="text-sm mt-1" style={{ color: "var(--text-secondary)" }}>
          캡스톤 디자인 데모
        </p>
      </div>
      <div className="flex-1 flex justify-end">
        <Link
          href="/"
          onClick={() => dispatch(clearChat())}
          className="text-sm px-3 py-1"
          style={{
            fontFamily: "var(--font-serif)",
            color: "var(--text-secondary)",
            border: "1px solid var(--border-color)",
            borderRadius: "2px",
            textDecoration: "none",
          }}
        >
          새 대화
        </Link>
      </div>
    </header>
  );
}
