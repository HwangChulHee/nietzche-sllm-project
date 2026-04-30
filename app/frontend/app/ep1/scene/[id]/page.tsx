"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect } from "react";

import { InteractionScreen } from "@/components/vn/InteractionScreen";
import { NarrationScreen } from "@/components/vn/NarrationScreen";
import { ep1Screen2Summit } from "@/data/scenes/ep1_screen2_summit";
import { ep1Screen3Forest } from "@/data/scenes/ep1_screen3_forest";
import { ep1Screen4Road } from "@/data/scenes/ep1_screen4_road";
import { ep1Screen5Meeting } from "@/data/scenes/ep1_screen5_meeting";
import { ep1Screen6Walking } from "@/data/scenes/ep1_screen6_walking";
import { ep1Screen7MarketDistant } from "@/data/scenes/ep1_screen7_market_distant";
import type { InteractionScene, NarrationScene } from "@/data/scenes/types";
import { useAppDispatch } from "@/lib/hooks/useAppDispatch";
import { useNavigate } from "@/lib/hooks/useNavigate";
import { enterScene, type Mode } from "@/lib/store/episodeSlice";

const NARRATION_SCENES: Record<string, NarrationScene> = {
  "2": ep1Screen2Summit,
  "3": ep1Screen3Forest,
  "4": ep1Screen4Road,
};

const INTERACTION_SCENES: Record<string, InteractionScene> = {
  "5": ep1Screen5Meeting,
  "6": ep1Screen6Walking,
  "7": ep1Screen7MarketDistant,
};

const NEXT: Record<string, string> = {
  "2": "/ep1/scene/3",
  "3": "/ep1/scene/4",
  "4": "/ep1/scene/5",
  "5": "/ep1/scene/6",
  "6": "/ep1/scene/7",
  "7": "/ep1/ending",
};

const PREV: Record<string, string> = {
  "2": "/",
  "3": "/ep1/scene/2",
  "4": "/ep1/scene/3",
  "5": "/ep1/scene/4",
  "6": "/ep1/scene/5",
  "7": "/ep1/scene/6",
};

export default function Ep1ScenePage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const dispatch = useAppDispatch();
  const navigate = useNavigate();

  const narration = NARRATION_SCENES[id];
  const interaction = INTERACTION_SCENES[id];
  const mode: Mode = narration ? "narration" : interaction ? "interaction" : "narration";

  useEffect(() => {
    const idx = Number.parseInt(id, 10);
    if (!Number.isNaN(idx)) {
      dispatch(enterScene({ episode: "ep1", sceneIndex: idx, mode }));
    }
  }, [dispatch, id, mode]);

  if (narration) {
    return (
      <NarrationScreen
        screenId={narration.screenId}
        paragraphs={narration.paragraphs}
        enableHaeseol={narration.enableHaeseol}
        illustration={narration.illustration}
        alt={narration.alt}
        onComplete={() => navigate(NEXT[id])}
        onBack={() => navigate(PREV[id])}
      />
    );
  }

  if (interaction) {
    return (
      <InteractionScreen
        scene={interaction}
        episode="ep1"
        sceneIndex={Number.parseInt(id, 10)}
        onComplete={() => navigate(NEXT[id])}
        onBack={() => navigate(PREV[id])}
      />
    );
  }

  return (
    <div className="vn-placeholder">
      <h1 className="vn-placeholder__title">Ep 1 · #{id}</h1>
      <p className="vn-placeholder__sub">(unknown scene)</p>

      <div className="vn-placeholder__nav">
        <Link className="vn-placeholder__link" href="/">
          [타이틀로]
        </Link>
      </div>
    </div>
  );
}
