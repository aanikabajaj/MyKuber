import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ShieldCheck, Fingerprint, Gauge, Globe2, KeyRound, ScanFace,
  Smartphone, Mail, ArrowRight, Lock, Activity,
} from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const features = [
  { icon: Gauge, title: "Adaptive Risk Engine", desc: "Every login is scored 0–100 from device, network, geo and behavioural signals — in real time." },
  { icon: Fingerprint, title: "Step-Up Authentication", desc: "Factors scale with risk: SAFE asks less, HIGH demands OTP + Authenticator, CRITICAL blocks." },
  { icon: ScanFace, title: "Biometric & Passkeys", desc: "Face verification or FIDO2/WebAuthn passkeys via Windows Hello, Touch ID or fingerprint." },
  { icon: Globe2, title: "Impossible-Travel & VPN", desc: "Geo-velocity checks and VPN/proxy detection catch account-takeover attempts." },
  { icon: KeyRound, title: "Full MFA Stack", desc: "Password, 6-digit MPIN, Email OTP, SMS OTP and TOTP Authenticator — layered by design." },
  { icon: Activity, title: "Live Admin Analytics", desc: "Risk distribution, auth statistics, a global login map and a complete audit trail." },
];

const bands = [
  { band: "SAFE", range: "0–30", variant: "safe" as const, steps: "MPIN → Face/Passkey" },
  { band: "MEDIUM", range: "31–60", variant: "medium" as const, steps: "+ Email OTP" },
  { band: "HIGH", range: "61–80", variant: "high" as const, steps: "+ SMS OTP + Authenticator" },
  { band: "CRITICAL", range: "81–100", variant: "critical" as const, steps: "Login blocked & user notified" },
];

export function Landing() {
  return (
    <div className="min-h-screen">
      <Navbar />

      {/* Hero */}
      <section className="relative overflow-hidden aurora">
        <div className="absolute inset-0 grid-lines opacity-40" />
        <div className="container relative py-20 sm:py-28">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="mx-auto max-w-3xl text-center"
          >
            <Badge variant="default" className="mb-5">
              <ShieldCheck className="h-3.5 w-3.5" /> Next-Gen Adaptive Banking Authentication
            </Badge>
            <h1 className="text-4xl font-extrabold tracking-tight sm:text-6xl">
              Authentication that{" "}
              <span className="bg-gradient-to-r from-primary via-purple-400 to-accent bg-clip-text text-transparent">
                thinks before it trusts
              </span>
            </h1>
            <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground">
              IAARE — the Intelligent Adaptive Authentication &amp; Risk Assessment Engine.
              A risk-aware security layer for Punjab &amp; Sind Bank that adapts the login
              journey to the threat of every single attempt.
            </p>
            <div className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row">
              <Link to="/register">
                <Button size="lg" className="w-full sm:w-auto">
                  Open an Account <ArrowRight className="h-4 w-4" />
                </Button>
              </Link>
              <Link to="/login">
                <Button size="lg" variant="outline" className="w-full sm:w-auto">
                  <Lock className="h-4 w-4" /> Secure Login
                </Button>
              </Link>
              <Link to="/about">
                <Button size="lg" variant="ghost" className="w-full sm:w-auto">
                  About IAARE
                </Button>
              </Link>
            </div>
            <div className="mt-8 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-xs text-muted-foreground">
              <span className="flex items-center gap-1.5"><Smartphone className="h-3.5 w-3.5" /> SMS OTP</span>
              <span className="flex items-center gap-1.5"><Mail className="h-3.5 w-3.5" /> Email OTP</span>
              <span className="flex items-center gap-1.5"><KeyRound className="h-3.5 w-3.5" /> TOTP Authenticator</span>
              <span className="flex items-center gap-1.5"><ScanFace className="h-3.5 w-3.5" /> Face</span>
              <span className="flex items-center gap-1.5"><Fingerprint className="h-3.5 w-3.5" /> Passkey</span>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Features */}
      <section className="container py-16">
        <h2 className="text-center text-3xl font-bold">One engine. Every layer of defence.</h2>
        <p className="mx-auto mt-3 max-w-2xl text-center text-muted-foreground">
          IAARE combines device intelligence, geolocation and multi-factor authentication into a single adaptive flow.
        </p>
        <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {features.map((f, i) => (
            <motion.div
              key={f.title}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.06 }}
            >
              <Card className="h-full p-6 transition-colors hover:border-primary/40">
                <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-primary/15">
                  <f.icon className="h-5 w-5 text-primary" />
                </div>
                <h3 className="mt-4 font-semibold">{f.title}</h3>
                <p className="mt-1.5 text-sm text-muted-foreground">{f.desc}</p>
              </Card>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Risk bands */}
      <section className="border-y border-border/60 bg-card/40">
        <div className="container py-16">
          <h2 className="text-center text-3xl font-bold">Four risk bands. Four responses.</h2>
          <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {bands.map((b) => (
              <Card key={b.band} className="p-5">
                <div className="flex items-center justify-between">
                  <Badge variant={b.variant}>{b.band}</Badge>
                  <span className="text-sm font-semibold tabular-nums text-muted-foreground">{b.range}</span>
                </div>
                <p className="mt-4 text-sm text-muted-foreground">{b.steps}</p>
              </Card>
            ))}
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
