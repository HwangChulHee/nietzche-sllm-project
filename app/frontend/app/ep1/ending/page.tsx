"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { EndingCard } from "@/components/vn/EndingCard";
import { ep1Screen8Ending } from "@/data/scenes/ep1_screen8_ending";
import { useAppDispatch } from "@/lib/hooks/useAppDispatch";
import { enterEnding } from "@/lib/store/episodeSlice";

export default function Ep1EndingPage() {
  const dispatch = useAppDispatch();
  const router = useRouter();

  useEffect(() => {
    dispatch(enterEnding({ episode: "ep1" }));
  }, [dispatch]);

  return (
    <EndingCard
      episode={ep1Screen8Ending.episode}
      title={ep1Screen8Ending.title}
      body={ep1Screen8Ending.body}
      actions={[
        { label: "[Ep 2로 계속]", onClick: () => router.push("/ep2/transition") },
        { label: "[타이틀로]", onClick: () => router.push("/") },
      ]}
    />
  );
}
