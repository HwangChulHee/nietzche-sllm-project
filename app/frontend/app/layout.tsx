import type { Metadata } from "next";

import { Providers } from "./providers";
import { VnFrame } from "./vn-frame";
import "./globals.css";

export const metadata: Metadata = {
  title: "차라투스트라와의 동행",
  description: "니체 페르소나 비주얼 노벨 — Episode 1 하산",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ko">
      <body>
        <Providers>
          <VnFrame>{children}</VnFrame>
        </Providers>
      </body>
    </html>
  );
}
