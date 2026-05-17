import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/providers";
import { Toaster } from "react-hot-toast";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "NEXUS — AI-Native Engineering Intelligence",
  description:
    "Production-grade AI platform that reimagines CI/CD, quality gates, and incident response for the AI-first engineering era.",
  icons: { icon: "/favicon.svg" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.variable} font-sans antialiased`}>
        <Providers>
          {children}
          <Toaster
            position="bottom-right"
            toastOptions={{
              style: {
                background: "hsl(222 47% 9%)",
                color: "hsl(213 31% 91%)",
                border: "1px solid hsl(222 47% 16%)",
              },
            }}
          />
        </Providers>
      </body>
    </html>
  );
}
