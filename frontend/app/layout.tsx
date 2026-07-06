import type { Metadata } from "next";
import "./globals.css";
import { JarvisBar } from "../components/JarvisBar";

// Display name is configurable until the external SaaS brand is finalized.
const APP_NAME = process.env.NEXT_PUBLIC_APP_NAME || "Career OS";

export const metadata: Metadata = {
  title: `${APP_NAME} | Human-in-the-Loop AI Career Assistant`,
  description:
    "An AI agent system that finds jobs, drafts application materials, builds skills, preps interviews, and compiles daily briefings — you review and submit everything yourself.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen antialiased">
        {children}
        <JarvisBar />
      </body>
    </html>
  );
}
