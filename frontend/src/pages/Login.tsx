import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { motion } from "framer-motion";
import {
  Lock, RefreshCw, ShieldAlert, KeyRound, ScanFace, Fingerprint, Mail,
  Smartphone, QrCode, FlaskConical, Globe, Server, UserX, ChevronDown, Ban,
} from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { RiskGauge } from "@/components/RiskGauge";
import { RiskFactors } from "@/components/RiskFactors";
import { StepIndicator } from "@/components/StepIndicator";
import { FaceCapture } from "@/components/FaceCapture";
import { captchaApi, loginApi, apiError, LoginSession } from "@/lib/api";
import { getDeviceInfo } from "@/lib/fingerprint";
import { performAuthentication } from "@/lib/webauthn";
import { useAuth } from "@/context/AuthContext";
import { cn, STEP_LABELS } from "@/lib/utils";

export function Login() {
  const navigate = useNavigate();
  const { setSession } = useAuth();
  const [phase, setPhase] = useState<"password" | "steps" | "blocked">("password");
  const [session, setSess] = useState<LoginSession | null>(null);

  async function handleResult(res: LoginSession) {
    setSess(res);
    if (res.status === "blocked") {
      setPhase("blocked");
      return;
    }
    if (res.status === "approved" && res.tokens) {
      await setSession(res.tokens.access_token, res.tokens.refresh_token);
      toast.success("Authenticated — welcome back!");
      navigate(res.tokens.user?.is_admin ? "/admin" : "/dashboard");
      return;
    }
    setPhase("steps");
  }

  return (
    <div className="min-h-screen aurora">
      <Navbar />
      <div className="container max-w-5xl py-10">
        {phase === "password" && <PasswordPhase onResult={handleResult} />}
        {phase === "blocked" && session && <BlockedPhase session={session} onRetry={() => setPhase("password")} />}
        {phase === "steps" && session && (
          <StepsPhase session={session} setSession={setSess} onResult={handleResult} />
        )}
      </div>
    </div>
  );
}

/* --------------------------- Password phase --------------------------- */
function PasswordPhase({ onResult }: { onResult: (r: LoginSession) => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [answer, setAnswer] = useState("");
  const [captcha, setCaptcha] = useState<{ captcha_id: string; image: string } | null>(null);
  const [loading, setLoading] = useState(false);
  const [showDemo, setShowDemo] = useState(false);
  const [sim, setSim] = useState<any>({ enabled: false });

  async function loadCaptcha() {
    try {
      setCaptcha(await captchaApi.get());
      setAnswer("");
    } catch {
      /* ignore */
    }
  }
  useEffect(() => { loadCaptcha(); }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!username || !password) return toast.error("Enter username and password");
    if (!captcha) return toast.error("Captcha not loaded");
    setLoading(true);
    try {
      const device = await getDeviceInfo();
      const payload: any = {
        username, password,
        captcha_id: captcha.captcha_id, captcha_answer: answer,
        device,
      };
      if (sim.enabled) payload.simulate = sim;
      const res = await loginApi.password(payload);
      onResult(res);
    } catch (e) {
      toast.error(apiError(e));
      loadCaptcha();
    } finally {
      setLoading(false);
    }
  }

  function forceBand(band: string) {
    setSim((s: any) => ({ ...s, enabled: true, force_band: band }));
    toast.message(`Demo scenario armed: ${band}`, { description: "Sign in to see the adaptive flow." });
  }

  return (
    <div className="grid gap-8 lg:grid-cols-[1fr_360px]">
      <Card className="animate-fade-in">
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Lock className="h-5 w-5 text-primary" /> Secure Login</CardTitle>
          <CardDescription>Your login is protected by the IAARE adaptive risk engine.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={submit} className="space-y-4">
            <div className="space-y-1.5">
              <Label>Username</Label>
              <Input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="e.g. rahul" autoComplete="username" />
            </div>
            <div className="space-y-1.5">
              <Label>Password</Label>
              <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" />
            </div>
            <div className="space-y-1.5">
              <Label>CAPTCHA</Label>
              <div className="flex items-center gap-3">
                {captcha ? (
                  <img src={captcha.image} alt="captcha" className="h-[64px] w-[200px] rounded-md border border-border" />
                ) : (
                  <div className="h-[64px] w-[200px] animate-pulse rounded-md bg-secondary" />
                )}
                <Button type="button" variant="ghost" size="icon" onClick={loadCaptcha}><RefreshCw className="h-4 w-4" /></Button>
              </div>
              <Input value={answer} onChange={(e) => setAnswer(e.target.value)} placeholder="Type the characters above" className="mt-2 max-w-[200px] uppercase tracking-widest" />
            </div>
            <Button type="submit" loading={loading} className="w-full sm:w-auto">Continue</Button>
          </form>
        </CardContent>
      </Card>

      {/* Demo console + credentials */}
      <div className="space-y-4">
        <Card className="border-accent/30">
          <button className="flex w-full items-center justify-between p-4" onClick={() => setShowDemo((s) => !s)}>
            <span className="flex items-center gap-2 font-semibold"><FlaskConical className="h-4 w-4 text-accent" /> Demo Console</span>
            <ChevronDown className={cn("h-4 w-4 transition-transform", showDemo && "rotate-180")} />
          </button>
          {showDemo && (
            <CardContent className="space-y-3 border-t border-border pt-4">
              <p className="text-xs text-muted-foreground">Arm a risk scenario, then log in to watch the flow adapt.</p>
              <div className="grid grid-cols-2 gap-2">
                {[
                  { b: "SAFE", v: "safe" }, { b: "MEDIUM", v: "medium" },
                  { b: "HIGH", v: "high" }, { b: "CRITICAL", v: "critical" },
                ].map((x) => (
                  <button key={x.b} onClick={() => forceBand(x.b)}
                    className={cn("rounded-md border px-2 py-2 text-xs font-semibold transition-colors",
                      sim.force_band === x.b ? "border-primary bg-primary/15 text-primary" : "border-border hover:bg-secondary/60")}>
                    {x.b}
                  </button>
                ))}
              </div>
              <div className="space-y-1.5 pt-1">
                <ToggleRow icon={Globe} label="Foreign country" on={sim.country === "Russia"}
                  onClick={() => setSim((s: any) => ({ ...s, enabled: true, country: s.country === "Russia" ? undefined : "Russia", city: "Moscow", latitude: 55.75, longitude: 37.61 }))} />
                <ToggleRow icon={Server} label="VPN / proxy" on={!!sim.is_vpn}
                  onClick={() => setSim((s: any) => ({ ...s, enabled: true, is_vpn: !s.is_vpn }))} />
                <ToggleRow icon={UserX} label="New device" on={!!sim.new_device}
                  onClick={() => setSim((s: any) => ({ ...s, enabled: true, new_device: !s.new_device }))} />
                <ToggleRow icon={ShieldAlert} label="3 failed attempts" on={sim.failed_attempts === 3}
                  onClick={() => setSim((s: any) => ({ ...s, enabled: true, failed_attempts: s.failed_attempts === 3 ? undefined : 3 }))} />
              </div>
              <Button variant="ghost" size="sm" className="w-full" onClick={() => setSim({ enabled: false })}>Clear scenario</Button>
            </CardContent>
          )}
        </Card>

        <Card className="p-4">
          <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Demo Accounts</div>
          <div className="mt-3 space-y-2 text-sm">
            <Cred u="admin" p="Admin@1234" pin="123456" role="Admin" onFill={() => { setUsername("admin"); setPassword("Admin@1234"); }} />
            <Cred u="rahul" p="Rahul@1234" pin="654321" role="Customer" onFill={() => { setUsername("rahul"); setPassword("Rahul@1234"); }} />
          </div>
          <p className="mt-3 text-xs text-muted-foreground">Demo accounts auto-pass the biometric step. MPIN shown above.</p>
        </Card>
      </div>
    </div>
  );
}

function ToggleRow({ icon: Icon, label, on, onClick }: { icon: any; label: string; on: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick} className="flex w-full items-center justify-between rounded-md border border-border px-3 py-2 text-sm transition-colors hover:bg-secondary/60">
      <span className="flex items-center gap-2"><Icon className="h-4 w-4 text-muted-foreground" /> {label}</span>
      <span className={cn("h-4 w-8 rounded-full p-0.5 transition-colors", on ? "bg-primary" : "bg-secondary")}>
        <span className={cn("block h-3 w-3 rounded-full bg-white transition-transform", on && "translate-x-4")} />
      </span>
    </button>
  );
}

function Cred({ u, p, pin, role, onFill }: { u: string; p: string; pin: string; role: string; onFill: () => void }) {
  return (
    <button onClick={onFill} className="flex w-full items-center justify-between rounded-md border border-border px-3 py-2 text-left transition-colors hover:bg-secondary/60">
      <div>
        <div className="font-medium">{u} <Badge variant="secondary" className="ml-1">{role}</Badge></div>
        <div className="text-xs text-muted-foreground">pw: {p} · mpin: {pin}</div>
      </div>
      <span className="text-xs text-primary">Use →</span>
    </button>
  );
}

/* ----------------------------- Blocked -------------------------------- */
function BlockedPhase({ session, onRetry }: { session: LoginSession; onRetry: () => void }) {
  return (
    <div className="mx-auto max-w-xl">
      <Card className="overflow-hidden border-risk-critical/40">
        <div className="bg-risk-critical/10 p-8 text-center">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-risk-critical/20">
            <Ban className="h-8 w-8 text-risk-critical" />
          </div>
          <h2 className="mt-4 text-2xl font-bold text-risk-critical">Login Blocked</h2>
          <p className="mx-auto mt-2 max-w-md text-muted-foreground">
            {session.message || "This login attempt was flagged as CRITICAL risk and has been blocked. Your bank has been notified."}
          </p>
        </div>
        <CardContent className="space-y-5 pt-6">
          <RiskGauge score={session.risk.score} band={session.risk.band} />
          <div>
            <div className="mb-2 text-sm font-semibold">Why was this blocked?</div>
            <RiskFactors factors={session.risk.factors} />
          </div>
          <Button variant="outline" className="w-full" onClick={onRetry}>Try again</Button>
        </CardContent>
      </Card>
    </div>
  );
}

/* ------------------------------ Steps --------------------------------- */
function StepsPhase({
  session, setSession, onResult,
}: {
  session: LoginSession;
  setSession: (s: LoginSession) => void;
  onResult: (r: LoginSession) => void;
}) {
  const next = session.next_step;

  return (
    <div className="grid gap-8 lg:grid-cols-[340px_1fr]">
      {/* Risk sidebar */}
      <div className="space-y-4">
        <Card className="p-6">
          <RiskGauge score={session.risk.score} band={session.risk.band} />
          <div className="mt-4">
            <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Risk Factors</div>
            <RiskFactors factors={session.risk.factors} />
          </div>
          {session.risk.geo && (
            <div className="mt-4 flex items-center gap-2 rounded-lg border border-border bg-secondary/30 px-3 py-2 text-xs text-muted-foreground">
              <Globe className="h-3.5 w-3.5" />
              {session.risk.geo.city || "?"}, {session.risk.geo.country || "?"} · {session.risk.geo.ip}
            </div>
          )}
        </Card>
      </div>

      {/* Step content */}
      <Card className="animate-fade-in">
        <CardHeader>
          <StepIndicator steps={session.required_steps} completed={session.completed_steps} current={next} />
          <CardTitle className="mt-4 flex items-center gap-2">
            Step-up required · {next ? STEP_LABELS[next] || next : "Finalizing"}
          </CardTitle>
          <CardDescription>
            Risk band <b>{session.risk.band}</b> requires {session.required_steps.length} additional factor(s).
          </CardDescription>
        </CardHeader>
        <CardContent>
          {next === "mpin" && <MpinStep session={session} onResult={onResult} />}
          {next === "second_factor" && <SecondFactorStep session={session} onResult={onResult} />}
          {next === "email_otp" && (
            <LoginOtpStep channel="email" icon={Mail} session={session}
              send={() => loginApi.emailOtpSend(session.session_id!)}
              verify={(c) => loginApi.emailOtpVerify(session.session_id!, c)} onResult={onResult} />
          )}
          {next === "sms_otp" && (
            <LoginOtpStep channel="sms" icon={Smartphone} session={session}
              send={() => loginApi.smsOtpSend(session.session_id!)}
              verify={(c) => loginApi.smsOtpVerify(session.session_id!, c)} onResult={onResult} />
          )}
          {next === "totp" && <TotpStep session={session} onResult={onResult} />}
        </CardContent>
      </Card>
    </div>
  );
}

function MpinStep({ session, onResult }: { session: LoginSession; onResult: (r: LoginSession) => void }) {
  const [mpin, setMpin] = useState("");
  const [loading, setLoading] = useState(false);
  async function submit() {
    if (mpin.length !== 6) return toast.error("Enter your 6-digit MPIN");
    setLoading(true);
    try { onResult(await loginApi.mpin(session.session_id!, mpin)); }
    catch (e) { toast.error(apiError(e)); }
    finally { setLoading(false); }
  }
  return (
    <div className="max-w-xs space-y-4">
      <div className="space-y-1.5">
        <Label>6-digit MPIN</Label>
        <Input type="password" value={mpin} onChange={(e) => setMpin(e.target.value.replace(/\D/g, "").slice(0, 6))}
          className="text-center text-2xl tracking-[0.5em]" placeholder="••••••" inputMode="numeric" autoFocus />
      </div>
      <Button onClick={submit} loading={loading}><KeyRound className="h-4 w-4" /> Verify MPIN</Button>
    </div>
  );
}

function SecondFactorStep({ session, onResult }: { session: LoginSession; onResult: (r: LoginSession) => void }) {
  const [busy, setBusy] = useState(false);
  const isFace = session.second_factor === "face";

  async function verifyFace(embedding: number[]) {
    setBusy(true);
    try { onResult(await loginApi.face(session.session_id!, embedding)); }
    catch (e) { toast.error(apiError(e)); }
    finally { setBusy(false); }
  }
  async function verifyPasskey() {
    setBusy(true);
    try {
      const { handle, options } = await loginApi.passkeyOptions(session.session_id!);
      const credential = await performAuthentication(options);
      onResult(await loginApi.passkeyVerify(session.session_id!, handle, credential));
    } catch (e: any) {
      toast.error(e?.name === "NotAllowedError" ? "Passkey prompt dismissed." : apiError(e));
    } finally { setBusy(false); }
  }

  if (isFace) {
    return (
      <div className="space-y-3">
        <FaceCapture onCapture={verifyFace} label="Verify Face" busy={busy} />
        <div className="text-center">
          <Button variant="ghost" size="sm" onClick={() => verifyFace(new Array(64).fill(0))}>
            Simulate capture (demo accounts)
          </Button>
        </div>
      </div>
    );
  }
  return (
    <div className="space-y-3">
      <p className="text-sm text-muted-foreground">Authenticate with your registered passkey (Windows Hello / Touch ID / security key).</p>
      <Button onClick={verifyPasskey} loading={busy} size="lg"><Fingerprint className="h-4 w-4" /> Use Passkey</Button>
    </div>
  );
}

function LoginOtpStep({
  channel, icon: Icon, session, send, verify, onResult,
}: {
  channel: string; icon: any; session: LoginSession;
  send: () => Promise<any>; verify: (code: string) => Promise<LoginSession>;
  onResult: (r: LoginSession) => void;
}) {
  const [code, setCode] = useState("");
  const [dev, setDev] = useState<string | null>(null);
  const [dest, setDest] = useState("");
  const [loading, setLoading] = useState(false);
  const sentRef = useRef(false);

  async function doSend(initial = false) {
    try {
      const res = await send();
      setDev(res.dev_code || null);
      setDest(res.destination_masked || "");
      if (!initial) toast.success(res.message || "Code sent");
    } catch (e) { toast.error(apiError(e)); }
  }
  useEffect(() => { if (!sentRef.current) { sentRef.current = true; doSend(true); } }, []);

  async function submit() {
    setLoading(true);
    try { onResult(await verify(code)); }
    catch (e) { toast.error(apiError(e)); }
    finally { setLoading(false); }
  }

  return (
    <div className="max-w-sm space-y-4">
      <p className="text-sm text-muted-foreground flex items-center gap-2">
        <Icon className="h-4 w-4" /> Code sent to <b className="text-foreground">{dest}</b>
      </p>
      {dev && (
        <Alert variant="warning">
          <AlertDescription>
            <b>Demo mode:</b>{" "}
            <button className="font-mono font-bold text-accent underline" onClick={() => setCode(dev)}>{dev}</button>{" "}
            (click to autofill)
          </AlertDescription>
        </Alert>
      )}
      <Input value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
        className="text-center text-2xl tracking-[0.5em]" placeholder="••••••" inputMode="numeric" />
      <div className="flex gap-2">
        <Button onClick={submit} loading={loading}>Verify {channel.toUpperCase()} OTP</Button>
        <Button variant="ghost" onClick={() => doSend(false)}><RefreshCw className="h-4 w-4" /> Resend</Button>
      </div>
    </div>
  );
}

function TotpStep({ session, onResult }: { session: LoginSession; onResult: (r: LoginSession) => void }) {
  const [token, setToken] = useState("");
  const [loading, setLoading] = useState(false);
  async function submit() {
    setLoading(true);
    try { onResult(await loginApi.totp(session.session_id!, token)); }
    catch (e) { toast.error(apiError(e)); }
    finally { setLoading(false); }
  }
  return (
    <div className="max-w-xs space-y-4">
      <p className="text-sm text-muted-foreground flex items-center gap-2"><QrCode className="h-4 w-4" /> Enter the code from your Authenticator app.</p>
      <Input value={token} onChange={(e) => setToken(e.target.value.replace(/\D/g, "").slice(0, 6))}
        className="text-center text-2xl tracking-[0.5em]" placeholder="••••••" inputMode="numeric" autoFocus />
      <Button onClick={submit} loading={loading}>Verify Authenticator</Button>
    </div>
  );
}
