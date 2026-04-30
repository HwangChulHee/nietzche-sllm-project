import { streamSSE, type SSECallbacks } from "./sse";
import type { ChatMessage, Episode } from "./types";

export function streamSummarize(
  args: { episode: Episode; sceneIndex: number; history: ChatMessage[] },
  cb: SSECallbacks,
  signal?: AbortSignal,
) {
  return streamSSE(
    "/api/v1/summarize",
    {
      episode: args.episode,
      scene_index: args.sceneIndex,
      history: args.history,
    },
    cb,
    signal,
  );
}

/**
 * 한 번에 끝까지 받아 문자열로 반환. 세이브 / transition 백그라운드용.
 */
export async function summarizeOnce(args: {
  episode: Episode;
  sceneIndex: number;
  history: ChatMessage[];
}): Promise<string> {
  const chunks: string[] = [];
  await streamSummarize(args, {
    onDelta: (d) => chunks.push(d),
  });
  return chunks.join("");
}
