import type { Metadata } from "next";
import { Providers } from "./providers";
import { Sidebar } from "@/components/Sidebar";
import { Header } from "@/components/Header";
import { ChatInput } from "@/components/chat/ChatInput";
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
            style={{
              display: "flex",
              height: "100vh",
              backgroundColor: "var(--bg-primary)",
              color: "var(--text-primary)",
            }}
          >
            <Sidebar />

            {/* 메인 영역 */}
            <div
              style={{
                flex: 1,
                display: "flex",
                flexDirection: "column",
                minWidth: 0,
              }}
            >
              <Header />

              {/* children = 메시지 영역 */}
              <main
                style={{
                  flex: 1,
                  overflowY: "auto",
                  padding: "24px 32px",
                }}
              >
                <div style={{ maxWidth: "760px", margin: "0 auto" }}>
                  {children}
                </div>
              </main>

              {/* 하단 입력창 — 항상 고정 */}
              <footer
                style={{
                  padding: "20px 32px 24px",
                  // borderTop removed
                  backgroundColor: "var(--bg-primary)",
                  flexShrink: 0,
                }}
              >
                <div style={{ maxWidth: "760px", margin: "0 auto" }}>
                  <ChatInput />
                </div>
              </footer>
            </div>
          </div>
        </Providers>
      </body>
    </html>
  );
}
