"use client";

import { useState } from "react";
import { Frame } from "./Frame";
import { IllustrationLayer } from "./IllustrationLayer";
import { InputArea } from "./InputArea";
import { MessageBox } from "./MessageBox";
import { useInteraction } from "@/lib/hooks/useInteraction";
import type { InteractionScene } from "@/data/scenes/types";

type Props = {
  scene: InteractionScene;
  onComplete: () => void;
};

/**
 * InteractionScreen — #5/#6/#7, Ep 2 #4 인터랙션 화면.
 *
 * Farewell 흐름 (VN_UI_POLICY §3.10):
 *   [작별을 고한다] 클릭
 *     → ix.farewell() (작별 발화 sLLM)
 *     → transitionLabel이 "[엔딩으로 →]"로 전환
 *     → 학습자는 send/silent 한 번 더 가능 (선택)
 *     → 다시 클릭 시 onComplete (엔딩 카드 라우트로)
 */
export function InteractionScreen({ scene, onComplete }: Props) {
  const ix = useInteraction(scene);
  const [farewellTriggered, setFarewellTriggered] = useState(false);

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

  return (
    <Frame>
      <div className="vn-interaction">
        <IllustrationLayer
          imagePath={scene.illustration}
          alt={scene.alt}
          mode="interaction"
          priority
        />

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
      </div>
    </Frame>
  );
}
