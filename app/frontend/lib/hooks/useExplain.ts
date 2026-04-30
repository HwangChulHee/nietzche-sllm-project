"use client";

import { useCallback, useEffect, useRef } from "react";

import { streamExplain } from "@/lib/api/explain";
import type { ChatMessage } from "@/lib/api/types";
import { useAppDispatch, useAppSelector } from "@/lib/hooks/useAppDispatch";
import {
  addUserQuery,
  appendHaeseolDelta,
  closePanel,
  finalizeAnswer,
  openPanel,
  resetHaeseolForScreen,
  setHaeseolError,
  startAssistantAnswer,
} from "@/lib/store/haeseolSlice";

/**
 * useExplain — [더 깊이 묻기] 동적 풀이 SSE 호출.
 *
 * - 화면 전환 시 자동으로 reset (haeseolSlice가 screenId 변경 감지).
 * - 같은 화면 안에서는 history 누적 → 이전 Q&A를 백엔드 컨텍스트로 전달.
 * - panel 열려있는 동안만 호출. ESC / [닫기]로 close.
 */
export function useExplain(screenId: string) {
  const dispatch = useAppDispatch();
  const open = useAppSelector((s) => s.haeseol.open);
  const queryHistory = useAppSelector((s) => s.haeseol.queryHistory);
  const streaming = useAppSelector((s) => s.haeseol.streaming);
  const error = useAppSelector((s) => s.haeseol.error);

  const abortRef = useRef<AbortController | null>(null);
  const aliveRef = useRef(true);

  // 화면 변경 시 reset
  useEffect(() => {
    aliveRef.current = true;
    dispatch(resetHaeseolForScreen(screenId));
    return () => {
      aliveRef.current = false;
      abortRef.current?.abort();
    };
  }, [dispatch, screenId]);

  const buildHistory = useCallback(
    (extra?: ChatMessage): ChatMessage[] => {
      const base: ChatMessage[] = queryHistory
        .filter((m) => m.streaming !== true)
        .map((m) => ({ role: m.role, content: m.content }));
      return extra ? [...base, extra] : base;
    },
    [queryHistory],
  );

  const ask = useCallback(
    async (query: string) => {
      const trimmed = query.trim();
      if (!trimmed || streaming) return;
      const history = buildHistory({ role: "user", content: trimmed });
      dispatch(addUserQuery(trimmed));
      dispatch(startAssistantAnswer());
      const ctrl = new AbortController();
      abortRef.current = ctrl;
      await streamExplain(
        { screenId, query: trimmed, history },
        {
          onDelta: (d) =>
            aliveRef.current && dispatch(appendHaeseolDelta(d)),
          onDone: () => aliveRef.current && dispatch(finalizeAnswer()),
          onError: (m) =>
            aliveRef.current && dispatch(setHaeseolError(m)),
        },
        ctrl.signal,
      );
    },
    [dispatch, screenId, streaming, buildHistory],
  );

  const open_ = useCallback(() => {
    dispatch(openPanel({ screenId }));
  }, [dispatch, screenId]);

  const close_ = useCallback(() => {
    dispatch(closePanel());
  }, [dispatch]);

  return {
    open,
    queryHistory,
    streaming,
    error,
    ask,
    openPanel: open_,
    closePanel: close_,
  };
}
