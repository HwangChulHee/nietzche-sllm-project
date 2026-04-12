import type { Metadata } from "next";
import { Providers } from "./providers";
import { Header } from "@/components/Header";
import "./globals.css";

export const metadata: Metadata = {
  title: "니체 sLLM 상담",
  description: "니체 페르소나 sLLM 기반 철학 상담",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <body>
        <Providers>
          <div
            className="flex min-h-screen flex-col"
            style={{
              backgroundColor: "var(--bg-primary)",
              color: "var(--text-primary)",
            }}
          >
            <Header />
            {children}
          </div>
        </Providers>
      </body>
    </html>
  );
}
