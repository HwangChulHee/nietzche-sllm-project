"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect } from "react";

import { useAppDispatch } from "@/lib/hooks/useAppDispatch";
import { enterScene, type Mode } from "@/lib/store/episodeSlice";

const SCENE_LABELS: Record<string, { name: string; mode: Mode; phase: string }> = {
  "1": { name: "시장 광장 도착", mode: "narration", phase: "Phase 8" },
  "2": { name: "위버멘쉬 선포", mode: "narration", phase: "Phase 8" },
  "3": { name: "광대 사건", mode: "narration", phase: "Phase 8" },
  "4": { name: "학습자 재회", mode: "interaction", phase: "Phase 8" },
};

const NEXT: Record<string, string> = {
  "1": "/ep2/scene/2",
  "2": "/ep2/scene/3",
  "3": "/ep2/scene/4",
  "4": "/ep2/ending",
};

export default function Ep2ScenePage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const dispatch = useAppDispatch();
  const meta = SCENE_LABELS[id] ?? { name: "(unknown)", mode: "narration" as Mode, phase: "?" };

  useEffect(() => {
    const idx = Number.parseInt(id, 10);
    if (!Number.isNaN(idx)) {
      dispatch(enterScene({ episode: "ep2", sceneIndex: idx, mode: meta.mode }));
    }
  }, [dispatch, id, meta.mode]);

  return (
    <div className="vn-placeholder">
      <h1 className="vn-placeholder__title">Ep 2 · #{id}</h1>
      <p className="vn-placeholder__sub">{meta.name} ({meta.mode})</p>
      <p className="vn-placeholder__sub">[{meta.phase}에서 구현 예정]</p>

      <div className="vn-placeholder__nav">
        {NEXT[id] && (
          <Link className="vn-placeholder__link" href={NEXT[id]}>
            [다음 →]
          </Link>
        )}
        <Link className="vn-placeholder__link" href="/">
          [타이틀로]
        </Link>
      </div>
    </div>
  );
}
