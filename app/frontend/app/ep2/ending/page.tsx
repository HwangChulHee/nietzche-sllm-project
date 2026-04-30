"use client";

import { useEffect } from "react";

import { EndingCard } from "@/components/vn/EndingCard";
import { ep2Ending } from "@/data/scenes/ep2_ending";
import { useAppDispatch } from "@/lib/hooks/useAppDispatch";
import { useNavigate } from "@/lib/hooks/useNavigate";
import { enterEnding } from "@/lib/store/episodeSlice";
import { showToast } from "@/lib/store/uiSlice";

export default function Ep2EndingPage() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();

  useEffect(() => {
    dispatch(enterEnding({ episode: "ep2" }));
  }, [dispatch]);

  return (
    <EndingCard
      episode={ep2Ending.episode}
      title={ep2Ending.title}
      body={ep2Ending.body}
      illustration={ep2Ending.illustration}
      alt={ep2Ending.alt}
      actions={[
        {
          label: "[Ep 3는 확장 비전 슬라이드로 대체]",
          onClick: () =>
            dispatch(
              showToast({
                message: "이 자리에서 외부 발표 슬라이드로 전환됩니다.",
                durationMs: 2400,
              }),
            ),
        },
        { label: "[타이틀로]", onClick: () => navigate("/") },
      ]}
      onBack={() => navigate("/ep2/scene/4")}
    />
  );
}
