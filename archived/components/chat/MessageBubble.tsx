import { Message } from "@/lib/store/chatSlice";

interface Props {
  message: Message;
}

export function MessageBubble({ message }: Props) {
  const isUser = message.role === "user";

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "8px",
        alignItems: isUser ? "flex-end" : "flex-start",
      }}
    >
      <span
        style={{
          fontSize: "13px",
          fontFamily: "var(--font-serif)",
          fontWeight: 600,
          letterSpacing: "0.08em",
          color: isUser ? "var(--text-secondary)" : "var(--accent)",
          textTransform: "uppercase",
        }}
      >
        {isUser ? "나" : "Nietzsche"}
      </span>
      <div
        style={{
          maxWidth: "85%",
          padding: isUser ? "14px 20px" : "4px 0 4px 20px",
          fontFamily: "var(--font-serif)",
          fontSize: "16px",
          lineHeight: "1.85",
          color: "var(--text-primary)",
          ...(isUser
            ? {
                backgroundColor: "#e8e3d6",
                border: "1px solid #d8d2c2",
                borderRadius: "3px",
              }
            : {
                borderLeft: "3px solid var(--accent)",
              }),
        }}
      >
        {message.content}
        {message.streaming && (
          <span
            style={{
              display: "inline-block",
              width: "2px",
              height: "1.1em",
              marginLeft: "4px",
              verticalAlign: "text-bottom",
              backgroundColor: "var(--accent)",
              animation: "pulse 1.2s ease-in-out infinite",
            }}
          />
        )}
      </div>
    </div>
  );
}
