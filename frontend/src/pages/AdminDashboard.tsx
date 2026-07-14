import { useEffect, useMemo, useState } from "react";
import {
  Users, LogIn, ShieldBan, AlertTriangle, MonitorSmartphone, Activity,
  Globe2, ScrollText,
} from "lucide-react";
import {
  PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, YAxis,
  Tooltip, CartesianGrid, AreaChart, Area, Legend,
} from "recharts";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge, bandVariant } from "@/components/ui/badge";
import { StatCard } from "@/components/StatCard";
import { WorldMap } from "@/components/WorldMap";
import { adminApi } from "@/lib/api";
import { bandHex, formatDate } from "@/lib/utils";

export function AdminDashboard() {
  const [stats, setStats] = useState<any>(null);
  const [risk, setRisk] = useState<any[]>([]);
  const [authStats, setAuthStats] = useState<any[]>([]);
  const [attempts, setAttempts] = useState<any[]>([]);
  const [audit, setAudit] = useState<any[]>([]);
  const [users, setUsers] = useState<any[]>([]);
  const [mapPts, setMapPts] = useState<any[]>([]);

  useEffect(() => {
    (async () => {
      try {
        const [s, r, a, at, au, u, m] = await Promise.all([
          adminApi.stats(), adminApi.riskDistribution(), adminApi.authStats(),
          adminApi.loginAttempts(), adminApi.auditLogs(), adminApi.users(), adminApi.map(),
        ]);
        setStats(s); setRisk(r); setAuthStats(a); setAttempts(at);
        setAudit(au); setUsers(u); setMapPts(m);
      } catch { /* ignore */ }
    })();
  }, []);

  const timeline = useMemo(() => {
    const days: Record<string, { date: string; logins: number; blocked: number }> = {};
    for (let i = 6; i >= 0; i--) {
      const d = new Date(); d.setDate(d.getDate() - i);
      const key = d.toISOString().slice(5, 10);
      days[key] = { date: key, logins: 0, blocked: 0 };
    }
    attempts.forEach((a) => {
      if (!a.created_at) return;
      const key = new Date(a.created_at).toISOString().slice(5, 10);
      if (days[key]) {
        if (a.decision === "BLOCK") days[key].blocked++;
        else if (a.success) days[key].logins++;
      }
    });
    return Object.values(days);
  }, [attempts]);

  return (
    <div className="min-h-screen">
      <Navbar />
      <div className="container py-10">
        <div className="flex items-center gap-2">
          <h1 className="text-3xl font-bold">Admin Command Center</h1>
          <Badge variant="default"><Activity className="h-3 w-3" /> Live</Badge>
        </div>
        <p className="mt-1 text-muted-foreground">Fleet-wide authentication analytics &amp; risk intelligence.</p>

        {/* Stat cards */}
        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
          <StatCard label="Total Users" value={stats?.total_users ?? "—"} icon={Users} accent="primary" />
          <StatCard label="Logins Today" value={stats?.logins_today ?? "—"} icon={LogIn} accent="risk-safe" />
          <StatCard label="Blocked" value={stats?.blocked_logins ?? "—"} icon={ShieldBan} accent="risk-critical" />
          <StatCard label="High Risk" value={stats?.high_risk_logins ?? "—"} icon={AlertTriangle} accent="risk-high" />
          <StatCard label="Devices" value={stats?.total_devices ?? "—"} icon={MonitorSmartphone} accent="accent" />
          <StatCard label="Active Sessions" value={stats?.active_sessions ?? "—"} icon={Activity} accent="primary" />
        </div>

        {/* Charts row */}
        <div className="mt-6 grid gap-6 lg:grid-cols-3">
          <Card>
            <CardHeader><CardTitle>Risk Distribution</CardTitle></CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={240}>
                <PieChart>
                  <Pie data={risk} dataKey="count" nameKey="band" cx="50%" cy="50%" innerRadius={55} outerRadius={90} paddingAngle={3}>
                    {risk.map((r, i) => <Cell key={i} fill={bandHex(r.band)} />)}
                  </Pie>
                  <Tooltip contentStyle={tooltipStyle} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Authentication Factors</CardTitle></CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={authStats}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                  <XAxis dataKey="factor" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                  <YAxis tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} allowDecimals={false} />
                  <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "hsl(var(--secondary) / 0.4)" }} />
                  <Bar dataKey="count" fill="hsl(var(--primary))" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Logins (7 days)</CardTitle></CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={240}>
                <AreaChart data={timeline}>
                  <defs>
                    <linearGradient id="gL" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="hsl(152 62% 45%)" stopOpacity={0.5} />
                      <stop offset="100%" stopColor="hsl(152 62% 45%)" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="gB" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="hsl(0 84% 60%)" stopOpacity={0.5} />
                      <stop offset="100%" stopColor="hsl(0 84% 60%)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                  <XAxis dataKey="date" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                  <YAxis tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} allowDecimals={false} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Area type="monotone" dataKey="logins" stroke="hsl(152 62% 45%)" fill="url(#gL)" strokeWidth={2} />
                  <Area type="monotone" dataKey="blocked" stroke="hsl(0 84% 60%)" fill="url(#gB)" strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </div>

        {/* Map */}
        <Card className="mt-6">
          <CardHeader><CardTitle className="flex items-center gap-2"><Globe2 className="h-5 w-5 text-primary" /> Global Login Activity</CardTitle></CardHeader>
          <CardContent><WorldMap points={mapPts} /></CardContent>
        </Card>

        {/* Tables */}
        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader><CardTitle>Recent Login Attempts</CardTitle></CardHeader>
            <CardContent className="max-h-[420px] overflow-auto">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-card text-left text-xs uppercase text-muted-foreground">
                  <tr><th className="py-2">User</th><th>Location</th><th>Risk</th><th>Decision</th></tr>
                </thead>
                <tbody>
                  {attempts.slice(0, 40).map((a) => (
                    <tr key={a.id} className="border-t border-border/50">
                      <td className="py-2">{a.username || "—"}<div className="text-xs text-muted-foreground">{a.ip_address}</div></td>
                      <td>{a.city || "?"}, {a.country || "?"}{a.is_vpn && <Badge variant="high" className="ml-1">VPN</Badge>}</td>
                      <td><Badge variant={bandVariant(a.risk_band)}>{a.risk_band}</Badge></td>
                      <td>{a.success ? <span className="text-risk-safe">ALLOW</span> : <span className="text-risk-critical">{a.decision}</span>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle className="flex items-center gap-2"><ScrollText className="h-5 w-5 text-primary" /> Audit Log</CardTitle></CardHeader>
            <CardContent className="max-h-[420px] space-y-2 overflow-auto">
              {audit.map((e) => (
                <div key={e.id} className="rounded-lg border border-border/50 px-3 py-2 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="font-medium">{e.event_type}</span>
                    <Badge variant={e.severity === "critical" ? "critical" : e.severity === "warning" ? "medium" : "secondary"}>{e.severity}</Badge>
                  </div>
                  <div className="text-xs text-muted-foreground">{e.description}</div>
                  <div className="text-[10px] text-muted-foreground">{formatDate(e.created_at)}</div>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>

        {/* Users table */}
        <Card className="mt-6">
          <CardHeader><CardTitle>Users</CardTitle></CardHeader>
          <CardContent className="overflow-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase text-muted-foreground">
                <tr><th className="py-2">User</th><th>Email</th><th>Location</th><th>Factor</th><th>Role</th><th>Last Login</th></tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id} className="border-t border-border/50">
                    <td className="py-2 font-medium">{u.full_name}<div className="text-xs text-muted-foreground">@{u.username}</div></td>
                    <td>{u.email}</td>
                    <td>{[u.city, u.country].filter(Boolean).join(", ") || "—"}</td>
                    <td>{u.second_factor ? <Badge variant="secondary">{u.second_factor}</Badge> : "—"}</td>
                    <td>{u.is_admin ? <Badge>Admin</Badge> : <Badge variant="secondary">Customer</Badge>}</td>
                    <td className="text-xs text-muted-foreground">{u.last_login_at ? formatDate(u.last_login_at) : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      </div>
      <Footer />
    </div>
  );
}

const tooltipStyle = {
  background: "hsl(224 40% 9%)",
  border: "1px solid hsl(223 30% 20%)",
  borderRadius: 8,
  fontSize: 12,
};
