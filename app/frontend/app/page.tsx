"use client";

import { useEffect, useState } from "react";

import { TitleScreen } from "@/components/vn/TitleScreen";
import { getSave } from "@/lib/api/save";
import { useAppDispatch } from "@/lib/hooks/useAppDispatch";
import { useNavigate } from "@/lib/hooks/useNavigate";
import { enterTitle } from "@/lib/store/episodeSlice";
import { showToast } from "@/lib/store/uiSlice";

export default function TitlePage() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
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
      illustration="/illustrations/screen_01_title.webp"
      alt="새벽 알프스 능선과 동굴 입구의 작은 인영"
      onStart={() => navigate("/ep1/scene/2")}
      onLoad={() => navigate("/load")}
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
