"use client";

import { useEffect, useState } from "react";
import { BackButton } from "./BackButton";
import { Frame } from "./Frame";
import { IllustrationLayer } from "./IllustrationLayer";
import { InputArea } from "./InputArea";
import { MessageBox } from "./MessageBox";
import { Modal } from "./Modal";
import { useInteraction } from "@/lib/hooks/useInteraction";
import { useSave } from "@/lib/hooks/useSave";
import { useAppDispatch } from "@/lib/hooks/useAppDispatch";
import { showToast } from "@/lib/store/uiSlice";
import type { Episode } from "@/lib/api/types";
import type { ChatMessage } from "@/lib/api/types";
import type { InteractionScene } from "@/data/scenes/types";

type Props = {
  scene: InteractionScene;
  episode: Episode;
  sceneIndex: number;
  onComplete: () => void;
  onBack: () => void;
};

/**
 * InteractionScreen — #5/#6/#7, Ep 2 #4.
 *
 * Phase 7에서 우상단 [저장] 버튼 추가:
 *   - slot 없으면 즉시 저장 + 토스트
 *   - slot 있으면 덮어쓰기 Modal 확인
 */
export function InteractionScreen({
  scene,
  episode,
  sceneIndex,
  onComplete,
  onBack,
}: Props) {
  const ix = useInteraction(scene);
  const dispatch = useAppDispatch();
  const { slot, saving, refresh, save } = useSave();
  const [overwriteOpen, setOverwriteOpen] = useState(false);
  const [farewellTriggered, setFarewellTriggered] = useState(false);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const inFarewellPhase = scene.farewell && farewellTriggered;
  const transitionLabel = inFarewellPhase ? "[엔딩으로 →]" : scene.transitionLabel;
  const transitionEnabled =
    ix.streamingState === "idle" && (inFarewellPhase || ix.userTurns >= 1);

  const handleTransition = async () => {
    if (!transitionEnabled) return;
    if (scene.farewell && !farewellTriggered) {
      setFarewellTriggered(true);
      await ix.farewell();
      return;
    }
    onComplete();
  };

  const recentMessages = (): ChatMessage[] =>
    ix.messages
      .filter((m) => m.streaming !== true)
      .map((m) => ({
        role: m.role,
        content: m.isSilent ? "..." : m.content,
      }));

  const performSave = async () => {
    const result = await save({
      episode,
      sceneIndex,
      recentMessages: recentMessages(),
    });
    if (result.ok) {
      dispatch(showToast({ message: "저장되었습니다", durationMs: 1800 }));
    } else {
      dispatch(
        showToast({ message: "저장에 실패했습니다", durationMs: 2400 }),
      );
    }
  };

  const saveDisabled =
    saving || ix.streamingState !== "idle" || ix.messages.length === 0;

  const onSaveClick = () => {
    if (saveDisabled) return;
    if (slot) {
      setOverwriteOpen(true);
    } else {
      performSave();
    }
  };

  return (
    <Frame>
      <div className="vn-interaction">
        <IllustrationLayer
          imagePath={scene.illustration}
          alt={scene.alt}
          mode="interaction"
          priority
        />

        <BackButton
          onClick={onBack}
          disabled={ix.streamingState !== "idle"}
        />

        <button
          type="button"
          className="vn-save"
          onClick={onSaveClick}
          disabled={saveDisabled}
        >
          [저장]
        </button>

        <div className="vn-interaction__lower">
          <MessageBox messages={ix.messages} />
          <InputArea
            streamingState={ix.streamingState}
            canTransition={transitionEnabled}
            transitionLabel={transitionLabel}
            onSend={ix.send}
            onSilent={ix.silent}
            onTransition={handleTransition}
          />
        </div>

        {ix.error && (
          <div className="vn-interaction__error" role="alert">
            길이 잠시 끊겼습니다. — {ix.error}
          </div>
        )}

        {overwriteOpen && (
          <Modal
            title="저장"
            body={<>기존 저장 데이터를 덮어씁니다. 진행하시겠습니까?</>}
            actions={[
              {
                label: "취소",
                onClick: () => setOverwriteOpen(false),
              },
              {
                label: "덮어쓰기",
                primary: true,
                onClick: async () => {
                  setOverwriteOpen(false);
                  await performSave();
                },
              },
            ]}
            onClose={() => setOverwriteOpen(false)}
          />
        )}
      </div>
    </Frame>
  );
}
