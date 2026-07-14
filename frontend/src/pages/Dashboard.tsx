import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ShieldCheck, Smartphone, MonitorSmartphone, History, Trash2,
  ScanFace, Fingerprint, KeyRound, Settings as SettingsIcon, MapPin,
} from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge, bandVariant } from "@/components/ui/badge";
import { StatCard } from "@/components/StatCard";
import { useAuth } from "@/context/AuthContext";
import { userApi } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { toast } from "sonner";

export function Dashboard() {
  const { user } = useAuth();
  const [devices, setDevices] = useState<any[]>([]);
  const [history, setHistory] = useState<any[]>([]);

  async function load() {
    try {
      setDevices(await userApi.devices());
      setHistory(await userApi.loginHistory());
    } catch { /* ignore */ }
  }
  useEffect(() => { load(); }, []);

  async function removeDevice(id: number) {
    try { await userApi.removeDevice(id); toast.success("Device removed"); load(); }
    catch { toast.error("Could not remove device"); }
  }

  const factors = [
    { on: true, label: "Password", icon: KeyRound },
    { on: !!user?.totp_enabled, label: "Authenticator", icon: KeyRound },
    { on: user?.second_factor === "face", label: "Face", icon: ScanFace },
    { on: user?.second_factor === "passkey", label: "Passkey", icon: Fingerprint },
  ];
  const activeFactors = 2 + factors.filter((f) => f.on && f.label !== "Password").length;

  return (
    <div className="min-h-screen">
      <Navbar />
      <div className="container py-10">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold">Welcome back, {user?.first_name} 👋</h1>
            <p className="mt-1 text-muted-foreground">Here's your account security overview.</p>
          </div>
          <Link to="/settings"><Button variant="outline"><SettingsIcon className="h-4 w-4" /> Security Settings</Button></Link>
        </div>

        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard label="Last Login" value={user?.last_login_at ? formatDate(user.last_login_at).split(",")[0] : "—"} icon={History} accent="primary" hint={formatDate(user?.last_login_at)} />
          <StatCard label="Trusted Devices" value={devices.length} icon={MonitorSmartphone} accent="risk-safe" />
          <StatCard label="Active Factors" value={`${activeFactors}`} icon={ShieldCheck} accent="accent" hint="Layers protecting your account" />
          <StatCard label="Strong Factor" value={user?.second_factor === "passkey" ? "Passkey" : "Face"} icon={user?.second_factor === "passkey" ? Fingerprint : ScanFace} accent="primary" />
        </div>

        <div className="mt-6 grid gap-6 lg:grid-cols-3">
          {/* Profile */}
          <Card>
            <CardHeader><CardTitle>Profile</CardTitle></CardHeader>
            <CardContent className="space-y-3 text-sm">
              <Row label="Full name" value={user?.full_name} />
              <Row label="Username" value={user?.username} />
              <Row label="Email" value={user?.email} verified={user?.email_verified} />
              <Row label="Mobile" value={user?.mobile} verified={user?.mobile_verified} />
              <Row label="Location" value={[user?.city, user?.state, user?.country].filter(Boolean).join(", ") || "—"} />
              <div className="flex flex-wrap gap-2 pt-2">
                {factors.filter((f) => f.on).map((f) => (
                  <Badge key={f.label} variant="success"><f.icon className="h-3 w-3" /> {f.label}</Badge>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Devices */}
          <Card>
            <CardHeader><CardTitle className="flex items-center gap-2"><MonitorSmartphone className="h-4 w-4" /> Trusted Devices</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              {devices.length === 0 && <p className="text-sm text-muted-foreground">No devices recorded yet.</p>}
              {devices.map((d) => (
                <div key={d.id} className="flex items-center justify-between rounded-lg border border-border bg-secondary/30 p-3">
                  <div className="flex items-center gap-3">
                    <Smartphone className="h-4 w-4 text-primary" />
                    <div>
                      <div className="text-sm font-medium">{d.browser} · {d.os}</div>
                      <div className="text-xs text-muted-foreground">{d.last_country || "—"} · {formatDate(d.last_seen)}</div>
                    </div>
                  </div>
                  <Button variant="ghost" size="icon" onClick={() => removeDevice(d.id)}><Trash2 className="h-4 w-4 text-risk-high" /></Button>
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Login history */}
          <Card className="lg:col-span-1">
            <CardHeader><CardTitle className="flex items-center gap-2"><History className="h-4 w-4" /> Recent Logins</CardTitle></CardHeader>
            <CardContent className="space-y-2">
              {history.length === 0 && <p className="text-sm text-muted-foreground">No login history yet.</p>}
              {history.slice(0, 8).map((h) => (
                <div key={h.id} className="flex items-center justify-between rounded-lg border border-border/60 px-3 py-2 text-sm">
                  <div className="flex items-center gap-2">
                    <MapPin className="h-3.5 w-3.5 text-muted-foreground" />
                    <div>
                      <div>{h.city || "?"}, {h.country || "?"}</div>
                      <div className="text-xs text-muted-foreground">{formatDate(h.created_at)}</div>
                    </div>
                  </div>
                  <Badge variant={bandVariant(h.risk_band)}>{h.risk_band}</Badge>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>
      <Footer />
    </div>
  );
}

function Row({ label, value, verified }: { label: string; value?: string; verified?: boolean }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-muted-foreground">{label}</span>
      <span className="flex items-center gap-1.5 font-medium">
        {value || "—"}
        {verified && <Badge variant="success" className="ml-1">✓</Badge>}
      </span>
    </div>
  );
}
