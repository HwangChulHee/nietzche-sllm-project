"use client";

import Link from "next/link";
import { useEffect } from "react";

import { useAppDispatch } from "@/lib/hooks/useAppDispatch";
import { enterEnding } from "@/lib/store/episodeSlice";

export default function Ep2EndingPage() {
  const dispatch = useAppDispatch();
  useEffect(() => {
    dispatch(enterEnding({ episode: "ep2" }));
  }, [dispatch]);

  return (
    <div className="vn-placeholder">
      <h1 className="vn-placeholder__title">EPISODE 2</h1>
      <p className="vn-placeholder__sub">시 장</p>
      <p className="vn-placeholder__sub">[Phase 8: 엔딩 카드 구현 예정]</p>
      <p className="vn-placeholder__sub" style={{ marginTop: 24, opacity: 0.7 }}>
        Ep 3는 확장 비전 슬라이드로 대체됩니다.
      </p>

      <div className="vn-placeholder__nav">
        <Link className="vn-placeholder__link" href="/">
          [타이틀로]
        </Link>
      </div>
    </div>
  );
}
