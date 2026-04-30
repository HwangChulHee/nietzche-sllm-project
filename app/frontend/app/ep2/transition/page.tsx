"use client";

import Link from "next/link";
import { useEffect } from "react";

import { useAppDispatch } from "@/lib/hooks/useAppDispatch";
import { enterTransition } from "@/lib/store/episodeSlice";

export default function Ep2TransitionPage() {
  const dispatch = useAppDispatch();
  useEffect(() => {
    dispatch(enterTransition());
  }, [dispatch]);

  return (
    <div className="vn-placeholder">
      <h1 className="vn-placeholder__title">…</h1>
      <p className="vn-placeholder__sub">밤이 깊었다. 시간은 흘러, 시장의 새벽이 왔다.</p>
      <p className="vn-placeholder__sub">[Phase 8: transition + 백그라운드 요약 구현 예정]</p>

      <div className="vn-placeholder__nav">
        <Link className="vn-placeholder__link" href="/ep2/scene/1">
          [Ep 2 시작]
        </Link>
        <Link className="vn-placeholder__link" href="/">
          [타이틀로]
        </Link>
      </div>
    </div>
  );
}
