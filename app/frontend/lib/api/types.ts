/**
 * 백엔드 schemas/vn.py 와 1:1 미러.
 */

export interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
}

export type Episode = "ep1" | "ep2";

export interface SaveSlot {
  episode: Episode;
  scene_index: number;
  summary: string;
  recent_messages: ChatMessage[];
  timestamp: string;
}
