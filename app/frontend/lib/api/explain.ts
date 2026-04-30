import { streamSSE, type SSECallbacks } from "./sse";
import type { ChatMessage } from "./types";

export function streamExplain(
  args: { screenId: string; query: string; history: ChatMessage[] },
  cb: SSECallbacks,
  signal?: AbortSignal,
) {
  return streamSSE(
    "/api/v1/explain",
    {
      screen_id: args.screenId,
      query: args.query,
      history: args.history,
    },
    cb,
    signal,
  );
}
