"use client";

import Link from "next/link";
import { useEffect } from "react";

import { useAppDispatch } from "@/lib/hooks/useAppDispatch";
import { enterEnding } from "@/lib/store/episodeSlice";

export default function Ep1EndingPage() {
  const dispatch = useAppDispatch();
  useEffect(() => {
    dispatch(enterEnding({ episode: "ep1" }));
  }, [dispatch]);

  return (
    <div className="vn-placeholder">
      <h1 className="vn-placeholder__title">EPISODE 1</h1>
      <p className="vn-placeholder__sub">하 산</p>
      <p className="vn-placeholder__sub">[Phase 4: 엔딩 카드 구현 예정]</p>

      <div className="vn-placeholder__nav">
        <Link className="vn-placeholder__link" href="/ep2/transition">
          [Ep 2로 계속]
        </Link>
        <Link className="vn-placeholder__link" href="/">
          [타이틀로]
        </Link>
      </div>
    </div>
  );
}
