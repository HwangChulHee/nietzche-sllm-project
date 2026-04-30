"use client";

import { useCallback } from "react";

import { deleteSave, getSave, postSave } from "@/lib/api/save";
import type { ChatMessage, Episode } from "@/lib/api/types";
import { useAppDispatch, useAppSelector } from "@/lib/hooks/useAppDispatch";
import { setSaveError, setSaving, setSlot } from "@/lib/store/saveSlice";

/**
 * useSave — 세이브/불러오기 백엔드 호출 + saveSlice 동기화.
 *
 * VN_UI_POLICY §6:
 *   - 첫 세이브(슬롯 비어있음): 모달 X 즉시 저장 + 토스트
 *   - 덮어쓰기(슬롯 있음): 호출 측이 모달 확인 후 save() 호출
 *   - 불러오기: 슬롯 있을 때만, 호출 측이 모달 확인 후 load() 후 navigate
 */
export function useSave() {
  const dispatch = useAppDispatch();
  const slot = useAppSelector((s) => s.save.slot);
  const saving = useAppSelector((s) => s.save.saving);

  const refresh = useCallback(async () => {
    try {
      const next = await getSave();
      dispatch(setSlot(next));
      return next;
    } catch (e) {
      dispatch(setSaveError(e instanceof Error ? e.message : String(e)));
      return null;
    }
  }, [dispatch]);

  const save = useCallback(
    async (payload: {
      episode: Episode;
      sceneIndex: number;
      recentMessages: ChatMessage[];
    }) => {
      dispatch(setSaving(true));
      try {
        await postSave({
          episode: payload.episode,
          scene_index: payload.sceneIndex,
          recent_messages: payload.recentMessages,
        });
        const fresh = await getSave();
        dispatch(setSlot(fresh));
        return { ok: true as const };
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        dispatch(setSaveError(msg));
        return { ok: false as const, error: msg };
      }
    },
    [dispatch],
  );

  const clear = useCallback(async () => {
    try {
      await deleteSave();
      dispatch(setSlot(null));
    } catch (e) {
      dispatch(setSaveError(e instanceof Error ? e.message : String(e)));
    }
  }, [dispatch]);

  return { slot, saving, refresh, save, clear };
}
