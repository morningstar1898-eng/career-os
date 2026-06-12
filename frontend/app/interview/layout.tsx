import { AuthGate } from "../../components/AuthGate";

export default function InterviewLayout({ children }: { children: React.ReactNode }) {
  return <AuthGate>{children}</AuthGate>;
}
