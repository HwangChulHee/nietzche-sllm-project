import { Message } from "@/lib/store/chatSlice";

interface Props {
  message: Message;
}

export function MessageBubble({ message }: Props) {
  const isUser = message.role === "user";

  return (
    <div className={`flex flex-col gap-1 ${isUser ? "items-end" : "items-start"}`}>
      <span
        className="text-xs"
        style={{
          fontFamily: "var(--font-serif)",
          color: "var(--text-secondary)",
        }}
      >
        {isUser ? "나" : "니체"}
      </span>
      <div
        className="max-w-[80%] px-5 py-3"
        style={{
          fontFamily: "var(--font-serif)",
          fontSize: "16px",
          lineHeight: "1.7",
          borderRadius: "2px",
          ...(isUser
            ? {
                backgroundColor: "var(--bg-secondary)",
                color: "var(--text-primary)",
              }
            : {
                backgroundColor: "transparent",
                color: "var(--text-primary)",
              }),
        }}
      >
        {message.content}
        {message.streaming && (
          <span
            className="ml-1 inline-block h-4 w-0.5 animate-pulse"
            style={{ backgroundColor: "var(--text-primary)", opacity: 0.6 }}
          />
        )}
      </div>
    </div>
  );
}
