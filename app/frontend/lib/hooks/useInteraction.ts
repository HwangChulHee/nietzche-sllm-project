"use client";

import { useCallback, useEffect, useRef } from "react";

import { useAppDispatch, useAppSelector } from "@/lib/hooks/useAppDispatch";
import {
  addUserMessage,
  appendDelta,
  finalizeAssistantMessage,
  resetForScreen,
  setBooting,
  setStreamingError,
  startAssistantMessage,
} from "@/lib/store/dialogueSlice";
import {
  streamRespond,
  streamRespondAuto,
  streamRespondFarewell,
} from "@/lib/api/persona";
import type { ChatMessage } from "@/lib/api/types";
import type { InteractionScene } from "@/data/scenes/types";

/**
 * useInteraction — #5/#6/#7 인터랙션 화면의 상태 머신 + SSE 호출.
 *
 * 진입 시퀀스 (VN_UI_POLICY §3.8):
 *   화면 페이드 600ms + 정적 200ms = 800ms 대기 후 자동 발화 시작.
 *   #5는 고정 발화(sLLM 호출 X), #6/#7은 /respond/auto.
 *
 * farewell:
 *   #7 [작별을 고한다] 클릭 시 /respond/farewell 호출. 학습자 마지막
 *   응답 1회는 P1로 미루고, farewell 발화 완료 후 onTransition은 페이지가
 *   자체 트리거(VN_PROGRESS Phase 6 한계 참조).
 */

const ENTRY_DELAY_MS = 800;
const SPEAKER_FADE_MS = 100;
const FIXED_CHAR_INTERVAL_MS = 32;

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export function useInteraction(scene: InteractionScene) {
  const dispatch = useAppDispatch();
  const messages = useAppSelector((s) => s.dialogue.messages);
  const streamingState = useAppSelector((s) => s.dialogue.streamingState);
  const userTurns = useAppSelector((s) => s.dialogue.userTurns);
  const error = useAppSelector((s) => s.dialogue.error);

  const abortRef = useRef<AbortController | null>(null);
  const aliveRef = useRef(true);

  // 진입: reset + 자동/고정 첫 발화
  useEffect(() => {
    aliveRef.current = true;
    dispatch(resetForScreen(scene.screenId));

    let cancelled = false;
    const timer = window.setTimeout(async () => {
      if (cancelled || !aliveRef.current) return;
      dispatch(setBooting());
      await sleep(SPEAKER_FADE_MS);
      if (!aliveRef.current) return;
      dispatch(startAssistantMessage());

      if (scene.firstUtterance.kind === "fixed") {
        for (const char of scene.firstUtterance.text) {
          if (!aliveRef.current) return;
          dispatch(appendDelta(char));
          await sleep(FIXED_CHAR_INTERVAL_MS);
        }
        if (aliveRef.current) dispatch(finalizeAssistantMessage());
        return;
      }

      const ctrl = new AbortController();
      abortRef.current = ctrl;
      await streamRespondAuto(
        { screenId: scene.screenId, history: [] },
        {
          onDelta: (d) => aliveRef.current && dispatch(appendDelta(d)),
          onDone: () =>
            aliveRef.current && dispatch(finalizeAssistantMessage()),
          onError: (m) =>
            aliveRef.current && dispatch(setStreamingError(m)),
        },
        ctrl.signal,
      );
    }, ENTRY_DELAY_MS);

    return () => {
      cancelled = true;
      aliveRef.current = false;
      window.clearTimeout(timer);
      abortRef.current?.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dispatch, scene.screenId]);

  const buildHistory = useCallback(
    (extra?: ChatMessage): ChatMessage[] => {
      const base: ChatMessage[] = messages
        .filter((m) => m.streaming !== true)
        .map((m) => ({
          role: m.role,
          content: m.isSilent ? "..." : m.content,
        }));
      return extra ? [...base, extra] : base;
    },
    [messages],
  );

  const send = useCallback(
    async (text: string) => {
      if (streamingState !== "idle") return;
      const trimmed = text.trim();
      if (!trimmed) return;
      const history = buildHistory({ role: "user", content: trimmed });
      dispatch(addUserMessage({ content: trimmed }));
      dispatch(setBooting());
      dispatch(startAssistantMessage());
      const ctrl = new AbortController();
      abortRef.current = ctrl;
      await streamRespond(
        {
          screenId: scene.screenId,
          message: trimmed,
          silent: false,
          history,
        },
        {
          onDelta: (d) => aliveRef.current && dispatch(appendDelta(d)),
          onDone: () =>
            aliveRef.current && dispatch(finalizeAssistantMessage()),
          onError: (m) =>
            aliveRef.current && dispatch(setStreamingError(m)),
        },
        ctrl.signal,
      );
    },
    [dispatch, scene.screenId, streamingState, buildHistory],
  );

  const silent = useCallback(async () => {
    if (streamingState !== "idle") return;
    const history = buildHistory({ role: "user", content: "..." });
    dispatch(addUserMessage({ content: "…", isSilent: true }));
    dispatch(setBooting());
    dispatch(startAssistantMessage());
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    await streamRespond(
      {
        screenId: scene.screenId,
        message: "",
        silent: true,
        history,
      },
      {
        onDelta: (d) => aliveRef.current && dispatch(appendDelta(d)),
        onDone: () =>
          aliveRef.current && dispatch(finalizeAssistantMessage()),
        onError: (m) =>
          aliveRef.current && dispatch(setStreamingError(m)),
      },
      ctrl.signal,
    );
  }, [dispatch, scene.screenId, streamingState, buildHistory]);

  const farewell = useCallback(async () => {
    if (streamingState !== "idle") return;
    const history = buildHistory();
    dispatch(setBooting());
    dispatch(startAssistantMessage());
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    await streamRespondFarewell(
      { screenId: scene.screenId, history },
      {
        onDelta: (d) => aliveRef.current && dispatch(appendDelta(d)),
        onDone: () =>
          aliveRef.current && dispatch(finalizeAssistantMessage()),
        onError: (m) =>
          aliveRef.current && dispatch(setStreamingError(m)),
      },
      ctrl.signal,
    );
  }, [dispatch, scene.screenId, streamingState, buildHistory]);

  const canTransition = streamingState === "idle" && userTurns >= 1;

  return {
    messages,
    streamingState,
    userTurns,
    error,
    canTransition,
    send,
    silent,
    farewell,
  };
}
