"use client";

import Link from "next/link";
import { useAppDispatch } from "@/lib/hooks/useAppDispatch";
import { clearChat } from "@/lib/store/chatSlice";

const FAKE_CONVERSATIONS = [
  "권태와 무의미에 대하여",
  "운명을 사랑한다는 것",
  "약자의 도덕에 관하여",
  "영원회귀의 사유",
  "초인의 길",
];

export function Sidebar() {
  const dispatch = useAppDispatch();

  return (
    <aside
      style={{
        width: "260px",
        flexShrink: 0,
        height: "100vh",
        display: "flex",
        flexDirection: "column",
        backgroundColor: "#ede8db",
        borderRight: "1px solid var(--border-color)",
      }}
    >
      {/* 상단 — 타이틀 */}
      <div
        style={{
          padding: "24px 20px 20px",
          borderBottom: "1px solid var(--border-color)",
        }}
      >
        <h2
          style={{
            fontFamily: "var(--font-serif)",
            fontSize: "17px",
            fontWeight: 700,
            color: "var(--text-primary)",
            letterSpacing: "0.02em",
          }}
        >
          니체 페르소나 sLLM
        </h2>
        <p
          style={{
            fontFamily: "var(--font-serif)",
            fontSize: "12px",
            color: "var(--text-secondary)",
            marginTop: "4px",
            letterSpacing: "0.05em",
          }}
        >
          캡스톤 디자인 데모
        </p>
      </div>

      {/* 새 대화 버튼 */}
      <div style={{ padding: "16px 16px 8px" }}>
        <Link
          href="/"
          onClick={() => dispatch(clearChat())}
          style={{
            display: "block",
            padding: "12px 16px",
            fontFamily: "var(--font-serif)",
            fontSize: "14px",
            fontWeight: 600,
            color: "var(--accent)",
            backgroundColor: "transparent",
            border: "1.5px solid var(--accent)",
            borderRadius: "3px",
            textDecoration: "none",
            textAlign: "center",
            letterSpacing: "0.03em",
            transition: "all 0.15s ease",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = "var(--accent)";
            e.currentTarget.style.color = "#f4f1ea";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = "transparent";
            e.currentTarget.style.color = "var(--accent)";
          }}
        >
          + 새 대화
        </Link>
      </div>

      {/* 최근 대화 */}
      <div style={{ padding: "16px 20px 8px" }}>
        <p
          style={{
            fontFamily: "var(--font-serif)",
            fontSize: "11px",
            fontWeight: 600,
            color: "var(--text-secondary)",
            letterSpacing: "0.12em",
            textTransform: "uppercase",
            marginBottom: "8px",
          }}
        >
          최근 대화
        </p>
      </div>

      <nav
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "0 12px",
        }}
      >
        {FAKE_CONVERSATIONS.map((title, i) => (
          <div
            key={i}
            style={{
              padding: "10px 12px",
              fontFamily: "var(--font-serif)",
              fontSize: "13px",
              color: "var(--text-secondary)",
              borderRadius: "3px",
              cursor: "pointer",
              marginBottom: "2px",
              transition: "background-color 0.15s ease",
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = "rgba(196, 186, 169, 0.4)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = "transparent";
            }}
          >
            {title}
          </div>
        ))}
      </nav>

      {/* 하단 캡션 */}
      <div
        style={{
          padding: "16px 20px",
          borderTop: "1px solid var(--border-color)",
          fontFamily: "var(--font-serif)",
          fontSize: "11px",
          color: "var(--text-secondary)",
          letterSpacing: "0.05em",
          fontStyle: "italic",
        }}
      >
        &ldquo;신은 죽었다.&rdquo;
        <br />
        — Friedrich Nietzsche
      </div>
    </aside>
  );
}
