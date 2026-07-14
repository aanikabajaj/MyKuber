import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Cpu, Database, Layers, Lock, ShieldCheck, Workflow } from "lucide-react";

const stack = [
  { icon: Layers, title: "Frontend", items: ["React 19 + TypeScript", "Vite", "Tailwind CSS", "Recharts", "React Router"] },
  { icon: Cpu, title: "Backend", items: ["Python 3 · FastAPI", "SQLAlchemy", "Pydantic", "JWT + bcrypt", "PyOTP · WebAuthn"] },
  { icon: Database, title: "Data & Security", items: ["SQLite", "Fernet encryption", "Audit logging", "Rate limiting", "Device fingerprinting"] },
];

const flow = [
  "Password + CAPTCHA verified",
  "Risk Engine scores the attempt (0–100)",
  "MPIN challenge",
  "Face verification or Passkey",
  "Email OTP (MEDIUM+)",
  "SMS OTP + Authenticator (HIGH)",
  "Access granted — or blocked at CRITICAL",
];

export function About() {
  return (
    <div className="min-h-screen">
      <Navbar />
      <div className="container max-w-5xl py-16">
        <Badge className="mb-4"><ShieldCheck className="h-3.5 w-3.5" /> About the Engine</Badge>
        <h1 className="text-4xl font-bold">Intelligent Adaptive Authentication &amp; Risk Assessment Engine</h1>
        <p className="mt-4 text-lg text-muted-foreground">
          IAARE re-imagines banking login as a risk-aware decision rather than a fixed checklist.
          It continuously evaluates who is logging in, from where, and on what device — then
          escalates or de-escalates the authentication requirements accordingly.
        </p>

        <div className="mt-10 grid gap-5 md:grid-cols-3">
          {stack.map((s) => (
            <Card key={s.title} className="p-6">
              <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-primary/15">
                <s.icon className="h-5 w-5 text-primary" />
              </div>
              <h3 className="mt-4 font-semibold">{s.title}</h3>
              <ul className="mt-3 space-y-1.5 text-sm text-muted-foreground">
                {s.items.map((i) => (
                  <li key={i} className="flex items-center gap-2">
                    <span className="h-1.5 w-1.5 rounded-full bg-primary" /> {i}
                  </li>
                ))}
              </ul>
            </Card>
          ))}
        </div>

        <Card className="mt-10 p-8">
          <div className="flex items-center gap-2">
            <Workflow className="h-5 w-5 text-primary" />
            <h2 className="text-xl font-semibold">The Adaptive Authentication Flow</h2>
          </div>
          <ol className="mt-6 space-y-3">
            {flow.map((step, i) => (
              <li key={i} className="flex items-start gap-3">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/15 text-xs font-bold text-primary">
                  {i + 1}
                </span>
                <span className="text-sm">{step}</span>
              </li>
            ))}
          </ol>
        </Card>

        <Card className="mt-6 border-accent/30 bg-accent/5 p-6">
          <div className="flex items-center gap-2 text-accent">
            <Lock className="h-5 w-5" />
            <h3 className="font-semibold">Prototype Notice</h3>
          </div>
          <p className="mt-2 text-sm text-muted-foreground">
            This is a high-fidelity hackathon demonstration prototype, not a production banking
            system. SMS/Email delivery is abstracted behind a provider interface — add credentials
            to go live; otherwise codes are surfaced in demo mode.
          </p>
        </Card>
      </div>
      <Footer />
    </div>
  );
}
