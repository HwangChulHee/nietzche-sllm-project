"use client";

import { useEffect, useState } from "react";

import { Modal } from "@/components/vn/Modal";
import { TitleScreen } from "@/components/vn/TitleScreen";
import { useAppDispatch } from "@/lib/hooks/useAppDispatch";
import { useNavigate } from "@/lib/hooks/useNavigate";
import { useSave } from "@/lib/hooks/useSave";
import { enterTitle } from "@/lib/store/episodeSlice";
import type { SaveSlot } from "@/lib/store/saveSlice";
import { showToast } from "@/lib/store/uiSlice";

function slotToPath(slot: SaveSlot): string {
  if (slot.episode === "ep1") return `/ep1/scene/${slot.scene_index}`;
  return `/ep2/scene/${slot.scene_index}`;
}

function formatTimestamp(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  const hh = String(d.getHours()).padStart(2, "0");
  const mi = String(d.getMinutes()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}  ${hh}:${mi}`;
}

function sceneLabel(slot: SaveSlot): string {
  const ep = slot.episode === "ep1" ? "Ep 1" : "Ep 2";
  return `${ep} — 화면 #${slot.scene_index}`;
}

export default function TitlePage() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const { slot, refresh } = useSave();
  const [loadOpen, setLoadOpen] = useState(false);

  useEffect(() => {
    dispatch(enterTitle());
    refresh();
  }, [dispatch, refresh]);

  return (
    <>
      <TitleScreen
        hasSavedSlot={!!slot}
        illustration="/illustrations/screen_01_title.webp"
        alt="새벽 알프스 능선과 동굴 입구의 작은 인영"
        onStart={() => navigate("/ep1/scene/2")}
        onLoad={() => setLoadOpen(true)}
        onExit={() =>
          dispatch(
            showToast({
              message: "[종료]는 데스크톱 앱 버전에서 동작합니다.",
              durationMs: 1800,
            }),
          )
        }
      />
      {loadOpen && !slot && (
        <Modal
          title="불러오기"
          body={<>저장된 게임이 없습니다.</>}
          actions={[{ label: "돌아가기", onClick: () => setLoadOpen(false) }]}
          onClose={() => setLoadOpen(false)}
        />
      )}
      {loadOpen && slot && (
        <Modal
          title="불러오기"
          body={
            <div className="vn-load-preview">
              <p className="vn-load-preview__scene">{sceneLabel(slot)}</p>
              <p className="vn-load-preview__time">
                {formatTimestamp(slot.timestamp)}
              </p>
              {slot.summary && (
                <p className="vn-load-preview__summary">“{slot.summary}”</p>
              )}
            </div>
          }
          actions={[
            { label: "취소", onClick: () => setLoadOpen(false) },
            {
              label: "불러오기",
              primary: true,
              onClick: () => {
                setLoadOpen(false);
                navigate(slotToPath(slot));
              },
            },
          ]}
          onClose={() => setLoadOpen(false)}
        />
      )}
    </>
  );
}
