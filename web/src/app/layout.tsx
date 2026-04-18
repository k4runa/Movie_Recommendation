import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { BackgroundPaths } from "@/components/layout/background-paths";
import { Toaster } from "@/components/ui/sonner";
import { ThemeProvider } from "@/components/theme-provider";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "CineWave — AI Movie Recommendations",
  description:
    "AI-powered movie recommendations based on your watching habits.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <ThemeProvider
          attribute="class"
          defaultTheme="dark"
          enableSystem
          disableTransitionOnChange
        >
          <BackgroundPaths />
          <main className="relative z-10 min-h-screen flex flex-col items-center justify-center p-4">
            {children}
          </main>
          <Toaster theme="system" position="top-right" closeButton />
        </ThemeProvider>
      </body>
    </html>
  );
}
