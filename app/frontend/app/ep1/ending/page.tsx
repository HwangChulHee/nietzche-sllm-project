"use client";

import { useEffect } from "react";

import { EndingCard } from "@/components/vn/EndingCard";
import { ep1Screen8Ending } from "@/data/scenes/ep1_screen8_ending";
import { useAppDispatch } from "@/lib/hooks/useAppDispatch";
import { useNavigate } from "@/lib/hooks/useNavigate";
import { enterEnding } from "@/lib/store/episodeSlice";

export default function Ep1EndingPage() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();

  useEffect(() => {
    dispatch(enterEnding({ episode: "ep1" }));
  }, [dispatch]);

  return (
    <EndingCard
      episode={ep1Screen8Ending.episode}
      title={ep1Screen8Ending.title}
      body={ep1Screen8Ending.body}
      illustration={ep1Screen8Ending.illustration}
      alt={ep1Screen8Ending.alt}
      actions={[
        { label: "[Ep 2로 계속]", onClick: () => navigate("/ep2/transition") },
        { label: "[타이틀로]", onClick: () => navigate("/") },
      ]}
      onBack={() => navigate("/ep1/scene/7")}
    />
  );
}
