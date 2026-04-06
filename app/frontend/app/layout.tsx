import type { Metadata } from "next";
import { Geist, Geist_Mono, Nanum_Myeongjo } from "next/font/google";
import { Providers } from "./providers";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const nanumMyeongjo = Nanum_Myeongjo({
  weight: ["400", "700", "800"],
  subsets: ["latin"],
  variable: "--font-nanum", // CSS 변수명 설정
})

export const metadata: Metadata = {
  title: "니체 AI 상담소",
  description: "심연을 들여다보는 철학적 대화",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${nanumMyeongjo.variable} font-serif min-h-full flex flex-col bg-background text-foreground antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
