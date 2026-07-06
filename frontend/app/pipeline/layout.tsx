import { AuthGate } from "../../components/AuthGate";

export default function PipelineLayout({ children }: { children: React.ReactNode }) {
  return <AuthGate>{children}</AuthGate>;
}
