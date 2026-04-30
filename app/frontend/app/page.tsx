"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { TitleScreen } from "@/components/vn/TitleScreen";
import { getSave } from "@/lib/api/save";
import { useAppDispatch } from "@/lib/hooks/useAppDispatch";
import { enterTitle } from "@/lib/store/episodeSlice";
import { showToast } from "@/lib/store/uiSlice";

export default function TitlePage() {
  const dispatch = useAppDispatch();
  const router = useRouter();
  const [hasSlot, setHasSlot] = useState<boolean>(false);

  useEffect(() => {
    dispatch(enterTitle());

    getSave()
      .then((slot) => setHasSlot(slot !== null))
      .catch(() => setHasSlot(false));
  }, [dispatch]);

  return (
    <TitleScreen
      hasSavedSlot={hasSlot}
      onStart={() => router.push("/ep1/scene/2")}
      onLoad={() => router.push("/load")}
      onExit={() =>
        dispatch(
          showToast({
            message: "[종료]는 패키징(Tauri) 단계에서 동작합니다.",
            durationMs: 1800,
          }),
        )
      }
    />
  );
}
