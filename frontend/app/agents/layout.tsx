import { AuthGate } from "../../components/AuthGate";

export default function AgentsLayout({ children }: { children: React.ReactNode }) {
  return <AuthGate>{children}</AuthGate>;
}
