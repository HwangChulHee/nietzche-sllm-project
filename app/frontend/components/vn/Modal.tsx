"use client";

import { useEffect } from "react";

export type ModalAction = {
  label: string;
  onClick: () => void;
  primary?: boolean;
};

type Props = {
  title: string;
  body: React.ReactNode;
  actions: ModalAction[];
  onClose?: () => void;
  closeOnBackdrop?: boolean;
};

/**
 * Modal — 평이한 시스템 톤 (VN_UI_POLICY §6.4). 작품 결 X.
 * 백드롭 클릭 또는 ESC로 닫기 (옵션). actions[0]은 default focus.
 */
export function Modal({
  title,
  body,
  actions,
  onClose,
  closeOnBackdrop = true,
}: Props) {
  useEffect(() => {
    if (!onClose) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div
      className="vn-modal__backdrop"
      onClick={() => closeOnBackdrop && onClose?.()}
      role="presentation"
    >
      <div
        className="vn-modal"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="vn-modal-title"
      >
        <h2 id="vn-modal-title" className="vn-modal__title">
          {title}
        </h2>
        <div className="vn-modal__divider">─────────────────────</div>
        <div className="vn-modal__body">{body}</div>
        <div className="vn-modal__actions">
          {actions.map((a) => (
            <button
              key={a.label}
              type="button"
              className={`vn-modal__action ${a.primary ? "vn-modal__action--primary" : ""}`}
              onClick={a.onClick}
            >
              {a.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
