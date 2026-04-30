import { VN_API_BASE } from "./sse";
import type { ChatMessage, Episode, SaveSlot } from "./types";

export async function getSave(): Promise<SaveSlot | null> {
  const res = await fetch(`${VN_API_BASE}/api/v1/save`);
  if (!res.ok) throw new Error(`getSave HTTP ${res.status}`);
  const data = (await res.json()) as SaveSlot | null;
  return data;
}

export async function postSave(payload: {
  episode: Episode;
  scene_index: number;
  recent_messages: ChatMessage[];
}): Promise<{ ok: boolean; summary_preview: string }> {
  const res = await fetch(`${VN_API_BASE}/api/v1/save`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`postSave HTTP ${res.status}`);
  return (await res.json()) as { ok: boolean; summary_preview: string };
}

export async function deleteSave(): Promise<{ deleted: boolean }> {
  const res = await fetch(`${VN_API_BASE}/api/v1/save`, { method: "DELETE" });
  if (!res.ok) throw new Error(`deleteSave HTTP ${res.status}`);
  return (await res.json()) as { deleted: boolean };
}
