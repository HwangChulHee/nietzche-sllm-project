"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect } from "react";

import { InteractionScreen } from "@/components/vn/InteractionScreen";
import { NarrationScreen } from "@/components/vn/NarrationScreen";
import { ep2Screen1MarketArrival } from "@/data/scenes/ep2_screen1_market_arrival";
import { ep2Screen2Uebermensch } from "@/data/scenes/ep2_screen2_uebermensch";
import { ep2Screen3ClownFall } from "@/data/scenes/ep2_screen3_clown_fall";
import { ep2Screen4Reunion } from "@/data/scenes/ep2_screen4_reunion";
import type { InteractionScene, NarrationScene } from "@/data/scenes/types";
import { useAppDispatch } from "@/lib/hooks/useAppDispatch";
import { useNavigate } from "@/lib/hooks/useNavigate";
import { enterScene, type Mode } from "@/lib/store/episodeSlice";

const NARRATION_SCENES: Record<string, NarrationScene> = {
  "1": ep2Screen1MarketArrival,
  "2": ep2Screen2Uebermensch,
  "3": ep2Screen3ClownFall,
};

const INTERACTION_SCENES: Record<string, InteractionScene> = {
  "4": ep2Screen4Reunion,
};

const NEXT: Record<string, string> = {
  "1": "/ep2/scene/2",
  "2": "/ep2/scene/3",
  "3": "/ep2/scene/4",
  "4": "/ep2/ending",
};

const PREV: Record<string, string> = {
  "1": "/", // transition은 자동 진행이라 타이틀로 복귀
  "2": "/ep2/scene/1",
  "3": "/ep2/scene/2",
  "4": "/ep2/scene/3",
};

export default function Ep2ScenePage() {
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
      dispatch(enterScene({ episode: "ep2", sceneIndex: idx, mode }));
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
        episode="ep2"
        sceneIndex={Number.parseInt(id, 10)}
        onComplete={() => navigate(NEXT[id])}
        onBack={() => navigate(PREV[id])}
      />
    );
  }

  return (
    <div className="vn-placeholder">
      <h1 className="vn-placeholder__title">Ep 2 · #{id}</h1>
      <p className="vn-placeholder__sub">(unknown scene)</p>

      <div className="vn-placeholder__nav">
        <Link className="vn-placeholder__link" href="/">
          [타이틀로]
        </Link>
      </div>
    </div>
  );
}
