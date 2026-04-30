import { streamSSE, type SSECallbacks } from "./sse";
import type { ChatMessage } from "./types";

export function streamRespond(
  args: {
    screenId: string;
    message: string;
    silent: boolean;
    history: ChatMessage[];
  },
  cb: SSECallbacks,
  signal?: AbortSignal,
) {
  return streamSSE(
    "/api/v1/respond",
    {
      screen_id: args.screenId,
      message: args.message,
      silent: args.silent,
      history: args.history,
    },
    cb,
    signal,
  );
}

export function streamRespondAuto(
  args: { screenId: string; history: ChatMessage[] },
  cb: SSECallbacks,
  signal?: AbortSignal,
) {
  return streamSSE(
    "/api/v1/respond/auto",
    { screen_id: args.screenId, history: args.history },
    cb,
    signal,
  );
}

export function streamRespondFarewell(
  args: { screenId: string; history: ChatMessage[] },
  cb: SSECallbacks,
  signal?: AbortSignal,
) {
  return streamSSE(
    "/api/v1/respond/farewell",
    { screen_id: args.screenId, history: args.history },
    cb,
    signal,
  );
}
