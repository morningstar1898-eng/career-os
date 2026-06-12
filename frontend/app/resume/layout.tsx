import { AuthGate } from "../../components/AuthGate";

export default function ResumeLayout({ children }: { children: React.ReactNode }) {
  return <AuthGate>{children}</AuthGate>;
}
