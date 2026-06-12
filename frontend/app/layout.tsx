import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Career OS | AI-Powered Job Search Assistant",
  description: "An autonomous AI agent system that searches jobs, builds skills, preps interviews, and compiles daily briefings.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
