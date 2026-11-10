import { Geist, Geist_Mono } from "next/font/google";

import type { Metadata } from "next";
import Providers from "./providers";
import Header from "@/components/layout/Header";
import { NuqsAdapter } from "nuqs/adapters/next/app";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "GlowCart",
  description: "Online Beauty and Cosmetics Store",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="fa" dir="rtl">
      <body
        className={`text-black ${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <NuqsAdapter>
          <Providers>
            <Header />
            {children}
          </Providers>
        </NuqsAdapter>
      </body>
    </html>
  );
}