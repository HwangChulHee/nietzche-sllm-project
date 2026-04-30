"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect } from "react";

import { useAppDispatch } from "@/lib/hooks/useAppDispatch";
import { enterScene, type Mode } from "@/lib/store/episodeSlice";

const SCENE_LABELS: Record<string, { name: string; mode: Mode; phase: string }> = {
  "2": { name: "산 정상", mode: "narration", phase: "Phase 4" },
  "3": { name: "숲의 성자", mode: "narration", phase: "Phase 4" },
  "4": { name: "길로 나섬", mode: "narration", phase: "Phase 4" },
  "5": { name: "만남", mode: "interaction", phase: "Phase 6" },
  "6": { name: "동행", mode: "interaction", phase: "Phase 6" },
  "7": { name: "시장 원경", mode: "interaction", phase: "Phase 6" },
};

const NEXT: Record<string, string> = {
  "2": "/ep1/scene/3",
  "3": "/ep1/scene/4",
  "4": "/ep1/scene/5",
  "5": "/ep1/scene/6",
  "6": "/ep1/scene/7",
  "7": "/ep1/ending",
};

export default function Ep1ScenePage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const dispatch = useAppDispatch();
  const meta = SCENE_LABELS[id] ?? { name: "(unknown)", mode: "narration" as Mode, phase: "?" };

  useEffect(() => {
    const idx = Number.parseInt(id, 10);
    if (!Number.isNaN(idx)) {
      dispatch(enterScene({ episode: "ep1", sceneIndex: idx, mode: meta.mode }));
    }
  }, [dispatch, id, meta.mode]);

  return (
    <div className="vn-placeholder">
      <h1 className="vn-placeholder__title">Ep 1 · #{id}</h1>
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
