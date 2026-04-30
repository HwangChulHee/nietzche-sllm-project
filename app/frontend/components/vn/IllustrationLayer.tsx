"use client";

import Image from "next/image";

export type IllustrationMode = "narration" | "interaction" | "fullscreen";

type Props = {
  imagePath: string;
  alt: string;
  mode?: IllustrationMode;
  priority?: boolean;
};

export function IllustrationLayer({
  imagePath,
  alt,
  mode = "narration",
  priority = false,
}: Props) {
  return (
    <div className={`vn-illust vn-illust--${mode}`} aria-hidden={!alt}>
      <Image
        src={imagePath}
        alt={alt}
        fill
        priority={priority}
        sizes="(min-aspect-ratio: 16/10) 100vh, 100vw"
        style={{ objectFit: "cover" }}
      />
    </div>
  );
}
