import { Message } from "@/lib/store/chatSlice";

interface Props {
  message: Message;
}

export function MessageBubble({ message }: Props) {
  const isUser = message.role === "user";

  return (
    <div className={`flex flex-col gap-1 ${isUser ? "items-end" : "items-start"}`}>
      <span className="text-xs font-semibold opacity-40">
        {isUser ? "나" : "니체"}
      </span>
      <div
        className={`max-w-[80%] rounded-lg px-4 py-3 leading-7 ${
          isUser
            ? "bg-zinc-800 text-zinc-100 dark:bg-zinc-700"
            : "bg-zinc-100 text-zinc-900 dark:bg-zinc-800 dark:text-zinc-100"
        }`}
      >
        {message.content}
        {message.streaming && (
          <span className="ml-1 inline-block h-4 w-0.5 animate-pulse bg-current opacity-70" />
        )}
      </div>
    </div>
  );
}
