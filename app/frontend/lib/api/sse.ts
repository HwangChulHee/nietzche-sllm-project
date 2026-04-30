/**
 * sse.ts — SSE 스트림 파싱 공통 헬퍼.
 *
 * 백엔드 엔드포인트 컨벤션:
 *   data: {"type": "metadata", ...}
 *   data: {"type": "delta", "content": "..."}
 *   data: {"type": "done"}
 *   data: {"type": "error", "message": "..."}
 *
 * 사용처: persona / explain / summarize 클라이언트.
 */

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export type SSEMetadata = Record<string, unknown> & { type: "metadata" };

export interface SSECallbacks {
  onMetadata?: (e: SSEMetadata) => void;
  onDelta: (delta: string) => void;
  onDone?: () => void;
  onError?: (message: string) => void;
}

function isAbortError(e: unknown): boolean {
  return e instanceof Error && (e.name === "AbortError" || e.name === "DOMException");
}

export async function streamSSE(
  path: string,
  body: unknown,
  cb: SSECallbacks,
  signal?: AbortSignal,
): Promise<void> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal,
    });
  } catch (e) {
    if (isAbortError(e)) return; // 화면 전환 등으로 인한 취소는 silent
    cb.onError?.(e instanceof Error ? e.message : "fetch failed");
    return;
  }

  if (!res.ok || !res.body) {
    cb.onError?.(`HTTP ${res.status}`);
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        let event: { type: string; [k: string]: unknown };
        try {
          event = JSON.parse(line.slice(6));
        } catch {
          continue;
        }
        switch (event.type) {
          case "metadata":
            cb.onMetadata?.(event as SSEMetadata);
            break;
          case "delta":
            cb.onDelta(String(event.content ?? ""));
            break;
          case "done":
            cb.onDone?.();
            break;
          case "error":
            cb.onError?.(String(event.message ?? "unknown error"));
            break;
        }
      }
    }
  } catch (e) {
    if (isAbortError(e)) return;
    cb.onError?.(e instanceof Error ? e.message : "stream error");
  }
}

export const VN_API_BASE = API_BASE;
