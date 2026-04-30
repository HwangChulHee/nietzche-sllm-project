"use client";

import { useRouter } from "next/navigation";
import { useCallback } from "react";

import { useAppDispatch } from "@/lib/hooks/useAppDispatch";
import { setFade } from "@/lib/store/uiSlice";

const FADE_OUT_MS = 600;
const HOLD_MS = 150;

/**
 * useNavigate — 화면 전환을 검은 페이드 오버레이와 함께 수행.
 *
 * 일반 router.push 대신 사용. 페이드아웃 600ms → 라우팅 → 페이지
 * vn-fade-in 시작 → 짧은 hold 후 오버레이 페이드아웃 600ms.
 */
export function useNavigate() {
  const router = useRouter();
  const dispatch = useAppDispatch();
  return useCallback(
    (href: string) => {
      dispatch(setFade("out"));
      window.setTimeout(() => {
        router.push(href);
        window.setTimeout(() => dispatch(setFade("idle")), HOLD_MS);
      }, FADE_OUT_MS);
    },
    [dispatch, router],
  );
}
