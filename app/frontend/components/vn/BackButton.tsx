"use client";

type Props = {
  onClick: () => void;
  disabled?: boolean;
};

export function BackButton({ onClick, disabled = false }: Props) {
  return (
    <button
      type="button"
      className="vn-back"
      onClick={(e) => {
        e.stopPropagation();
        if (!disabled) onClick();
      }}
      disabled={disabled}
      aria-label="뒤로"
    >
      ← 뒤로
    </button>
  );
}
