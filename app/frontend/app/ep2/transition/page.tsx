"use client";

import { useEffect } from "react";

import { TransitionEp2 } from "@/components/vn/TransitionEp2";
import { useAppDispatch } from "@/lib/hooks/useAppDispatch";
import { enterTransition } from "@/lib/store/episodeSlice";

export default function Ep2TransitionPage() {
  const dispatch = useAppDispatch();
  useEffect(() => {
    dispatch(enterTransition());
  }, [dispatch]);
  return <TransitionEp2 />;
}
