"use client";

import { useRouter } from "next/navigation";
import { Trash2 } from "lucide-react";
import { useAppDispatch, useAppSelector } from "@/lib/hooks/useAppDispatch";
import { deleteConversation } from "@/lib/store/chatSlice";

export function Header() {
  const dispatch = useAppDispatch();
  const router = useRouter();
  const currentConversationId = useAppSelector((s) => s.chat.currentConversationId);

  const handleDelete = async () => {
    if (!currentConversationId) return;
    const ok = window.confirm("이 대화를 삭제하시겠습니까?");
    if (!ok) return;
    await dispatch(deleteConversation(currentConversationId));
    router.replace("/");
  };

  return (
    <header
      style={{
        padding: "20px 32px",
        borderBottom: "1px solid var(--border-color)",
        backgroundColor: "var(--bg-primary)",
        flexShrink: 0,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
      }}
    >
      <h1
        style={{
          fontFamily: "var(--font-serif)",
          fontSize: "20px",
          fontWeight: 600,
          color: "var(--text-primary)",
          letterSpacing: "0.02em",
          margin: 0,
        }}
      >
        니체 페르소나 sLLM 상담
      </h1>

      {currentConversationId && (
        <button
          onClick={handleDelete}
          aria-label="대화 삭제"
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            width: "38px",
            height: "38px",
            backgroundColor: "transparent",
            color: "var(--text-secondary)",
            border: "1px solid var(--border-color)",
            borderRadius: "3px",
            cursor: "pointer",
            transition: "all 0.15s ease",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.color = "var(--accent)";
            e.currentTarget.style.borderColor = "var(--accent)";
            e.currentTarget.style.backgroundColor = "rgba(139, 46, 31, 0.06)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.color = "var(--text-secondary)";
            e.currentTarget.style.borderColor = "var(--border-color)";
            e.currentTarget.style.backgroundColor = "transparent";
          }}
        >
          <Trash2 size={18} strokeWidth={1.5} />
        </button>
      )}
    </header>
  );
}
