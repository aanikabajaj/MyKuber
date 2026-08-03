import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { motion } from "framer-motion";
import {
  Check, KeyRound, Mail, ScanFace, Smartphone, UserPlus, QrCode,
  Fingerprint, ShieldCheck, ArrowRight, RefreshCw, PartyPopper,
} from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { FaceEnroll } from "@/components/FaceEnroll";
import { registerApi, apiError } from "@/lib/api";
import { getDeviceInfo } from "@/lib/fingerprint";
import { isWebAuthnSupported, performRegistration } from "@/lib/webauthn";
import { cn } from "@/lib/utils";

const detailsSchema = z
  .object({
    first_name: z.string().min(1, "Required"),
    last_name: z.string().min(1, "Required"),
    dob: z.string().min(1, "Required"),
    gender: z.string().min(1, "Required"),
    email: z.string().email("Invalid email"),
    mobile: z.string().min(8, "Enter a valid mobile number").max(20),
    address: z.string().optional(),
    city: z.string().optional(),
    state: z.string().optional(),
    country: z.string().min(1, "Required"),
    pin_code: z.string().optional(),
    username: z.string().min(3, "Min 3 chars").regex(/^[A-Za-z0-9_.]+$/, "Letters, numbers, _ . only"),
    password: z
      .string()
      .regex(/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^\w\s]).{8,}$/, "8+ chars with upper, lower, number & symbol"),
    confirm_password: z.string(),
  })
  .refine((d) => d.password === d.confirm_password, {
    message: "Passwords do not match",
    path: ["confirm_password"],
  });

type DetailsForm = z.infer<typeof detailsSchema>;

const STEPS = [
  { key: "details", label: "Account Details", icon: UserPlus },
  { key: "mobile", label: "Mobile OTP", icon: Smartphone },
  { key: "email", label: "Email OTP", icon: Mail },
  { key: "authenticator", label: "Authenticator", icon: QrCode },
  { key: "mpin", label: "Set MPIN", icon: KeyRound },
  { key: "second_factor", label: "Face / Passkey", icon: ScanFace },
  { key: "complete", label: "Complete", icon: Check },
];

export function Register() {
  const navigate = useNavigate();
  const [stepIdx, setStepIdx] = useState(0);
  const [token, setToken] = useState("");
  const step = STEPS[stepIdx].key;

  function next() {
    setStepIdx((i) => Math.min(i + 1, STEPS.length - 1));
  }

  return (
    <div className="min-h-screen aurora">
      <Navbar />
      <div className="container max-w-5xl py-10">
        <div className="grid gap-8 lg:grid-cols-[240px_1fr]">
          {/* Stepper */}
          <aside className="hidden lg:block">
            <div className="sticky top-24 space-y-1">
              {STEPS.map((s, i) => {
                const done = i < stepIdx;
                const active = i === stepIdx;
                return (
                  <div
                    key={s.key}
                    className={cn(
                      "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors",
                      active && "bg-primary/10 text-primary",
                      done && "text-risk-safe"
                    )}
                  >
                    <div
                      className={cn(
                        "flex h-7 w-7 items-center justify-center rounded-full border text-xs",
                        active ? "border-primary bg-primary text-primary-foreground" :
                        done ? "border-risk-safe bg-risk-safe/15 text-risk-safe" :
                        "border-border text-muted-foreground"
                      )}
                    >
                      {done ? <Check className="h-3.5 w-3.5" /> : i + 1}
                    </div>
                    <span className={cn(!active && !done && "text-muted-foreground")}>{s.label}</span>
                  </div>
                );
              })}
            </div>
          </aside>

          {/* Content */}
          <div>
            <div className="mb-4 lg:hidden">
              <Badge>Step {stepIdx + 1} of {STEPS.length}</Badge>
            </div>
            <motion.div key={step} initial={{ opacity: 0, x: 16 }} animate={{ opacity: 1, x: 0 }}>
              {step === "details" && (
                <DetailsStep
                  onDone={(t) => {
                    setToken(t);
                    next();
                  }}
                />
              )}
              {step === "mobile" && (
                <OtpStep
                  title="Verify your mobile"
                  description="We sent a 6-digit code to your registered mobile number."
                  icon={Smartphone}
                  send={() => registerApi.mobileSend(token)}
                  verify={(code) => registerApi.mobileVerify(token, code)}
                  onDone={next}
                />
              )}
              {step === "email" && (
                <OtpStep
                  title="Verify your email"
                  description="Enter the 6-digit code sent to your email address."
                  icon={Mail}
                  send={() => registerApi.emailSend(token)}
                  verify={(code) => registerApi.emailVerify(token, code)}
                  onDone={next}
                />
              )}
              {step === "authenticator" && <AuthenticatorStep token={token} onDone={next} />}
              {step === "mpin" && <MpinStep token={token} onDone={next} />}
              {step === "second_factor" && <SecondFactorStep token={token} onDone={next} />}
              {step === "complete" && <CompleteStep onLogin={() => navigate("/login")} />}
            </motion.div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ------------------------------- Details ------------------------------- */
function DetailsStep({ onDone }: { onDone: (token: string) => void }) {
  const [loading, setLoading] = useState(false);
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<DetailsForm>({
    resolver: zodResolver(detailsSchema),
    defaultValues: { country: "India", gender: "" },
  });

  async function submit(values: DetailsForm) {
    setLoading(true);
    try {
      const res = await registerApi.details(values);
      toast.success("Account created. Let's verify your identity.");
      onDone(res.registration_token);
    } catch (e) {
      toast.error(apiError(e));
    } finally {
      setLoading(false);
    }
  }

  const field = (name: keyof DetailsForm, label: string, type = "text", placeholder = "") => (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      <Input type={type} placeholder={placeholder} {...register(name)} />
      {errors[name] && <p className="text-xs text-risk-high">{errors[name]?.message as string}</p>}
    </div>
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2"><UserPlus className="h-5 w-5 text-primary" /> Open your account</CardTitle>
        <CardDescription>Enter your details to begin secure enrollment.</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(submit)} className="space-y-5">
          <div className="grid gap-4 sm:grid-cols-2">
            {field("first_name", "First Name")}
            {field("last_name", "Last Name")}
            {field("dob", "Date of Birth", "date")}
            <div className="space-y-1.5">
              <Label>Gender</Label>
              <select
                className="flex h-10 w-full rounded-md border border-input bg-background/60 px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                {...register("gender")}
              >
                <option value="">Select…</option>
                <option>Male</option>
                <option>Female</option>
                <option>Other</option>
              </select>
              {errors.gender && <p className="text-xs text-risk-high">{errors.gender.message}</p>}
            </div>
            {field("email", "Email", "email", "you@example.com")}
            {field("mobile", "Mobile Number", "tel", "+91…")}
          </div>

          {field("address", "Address")}
          <div className="grid gap-4 sm:grid-cols-4">
            {field("city", "City")}
            {field("state", "State")}
            {field("country", "Country")}
            {field("pin_code", "PIN Code")}
          </div>

          <div className="grid gap-4 sm:grid-cols-3">
            {field("username", "Username")}
            {field("password", "Password", "password")}
            {field("confirm_password", "Confirm Password", "password")}
          </div>

          <Button type="submit" loading={loading} className="w-full sm:w-auto">
            Create Account <ArrowRight className="h-4 w-4" />
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

/* -------------------------------- OTP --------------------------------- */
function OtpStep({
  title, description, icon: Icon, send, verify, onDone,
}: {
  title: string; description: string; icon: any;
  send: () => Promise<any>; verify: (code: string) => Promise<any>; onDone: () => void;
}) {
  const [code, setCode] = useState("");
  const [devCode, setDevCode] = useState<string | null>(null);
  const [dest, setDest] = useState("");
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const sentRef = useRef(false);

  async function doSend(initial = false) {
    setSending(true);
    try {
      const res = await send();
      setDevCode(res.dev_code || null);
      setDest(res.destination_masked || "");
      if (!initial) toast.success(res.message || "Code sent");
    } catch (e) {
      toast.error(apiError(e));
    } finally {
      setSending(false);
    }
  }

  useEffect(() => {
    if (!sentRef.current) {
      sentRef.current = true;
      doSend(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function submit() {
    if (code.length < 4) return toast.error("Enter the code");
    setLoading(true);
    try {
      await verify(code);
      toast.success("Verified!");
      onDone();
    } catch (e) {
      toast.error(apiError(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2"><Icon className="h-5 w-5 text-primary" /> {title}</CardTitle>
        <CardDescription>{description} {dest && <span className="text-foreground">({dest})</span>}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {devCode && (
          <Alert variant="warning">
            <AlertDescription>
              <b>Demo mode:</b> your code is{" "}
              <button className="font-mono font-bold text-accent underline" onClick={() => setCode(devCode)}>
                {devCode}
              </button>{" "}
              (click to autofill). In production this is delivered via SMS/Email.
            </AlertDescription>
          </Alert>
        )}
        <div className="space-y-1.5">
          <Label>Verification Code</Label>
          <Input
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
            placeholder="••••••"
            inputMode="numeric"
            className="text-center text-2xl tracking-[0.5em]"
          />
        </div>
        <div className="flex items-center gap-3">
          <Button onClick={submit} loading={loading}>Verify &amp; Continue</Button>
          <Button variant="ghost" onClick={() => doSend(false)} loading={sending}>
            <RefreshCw className="h-4 w-4" /> Resend
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

/* --------------------------- Authenticator ---------------------------- */
function AuthenticatorStep({ token, onDone }: { token: string; onDone: () => void }) {
  const [qr, setQr] = useState("");
  const [secret, setSecret] = useState("");
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const setupRef = useRef(false);

  async function setup() {
    try {
      const res = await registerApi.authSetup(token);
      setQr(res.qr_data_uri);
      setSecret(res.secret);
    } catch (e) {
      toast.error(apiError(e));
    }
  }
  useEffect(() => {
    if (!setupRef.current) {
      setupRef.current = true;
      setup();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function verify() {
    setLoading(true);
    try {
      await registerApi.authVerify(token, code);
      toast.success("Authenticator linked!");
      onDone();
    } catch (e) {
      toast.error(apiError(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2"><QrCode className="h-5 w-5 text-primary" /> Link your Authenticator</CardTitle>
        <CardDescription>Scan the QR with any authenticator app (Authy, Microsoft Authenticator, etc.), then enter the 6-digit code.</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-6 sm:grid-cols-2">
        <div className="flex flex-col items-center gap-3">
          {qr ? (
            <img src={qr} alt="Authenticator QR" className="h-48 w-48 rounded-lg border border-border bg-white p-2" />
          ) : (
            <div className="h-48 w-48 animate-pulse rounded-lg bg-secondary" />
          )}
          {secret && (
            <div className="text-center">
              <div className="text-xs text-muted-foreground">Manual entry key</div>
              <code className="break-all text-xs text-accent">{secret}</code>
            </div>
          )}
        </div>
        <div className="space-y-4">
          <div className="space-y-1.5">
            <Label>6-digit code from your app</Label>
            <Input
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
              placeholder="••••••"
              inputMode="numeric"
              className="text-center text-2xl tracking-[0.5em]"
            />
          </div>
          <Button onClick={verify} loading={loading}>Verify Authenticator</Button>
        </div>
      </CardContent>
    </Card>
  );
}

/* -------------------------------- MPIN -------------------------------- */
function MpinStep({ token, onDone }: { token: string; onDone: () => void }) {
  const [mpin, setMpin] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit() {
    if (mpin.length !== 6) return toast.error("MPIN must be 6 digits");
    if (mpin !== confirm) return toast.error("MPINs do not match");
    setLoading(true);
    try {
      await registerApi.setMpin(token, mpin);
      toast.success("MPIN set!");
      onDone();
    } catch (e) {
      toast.error(apiError(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2"><KeyRound className="h-5 w-5 text-primary" /> Create your 6-digit MPIN</CardTitle>
        <CardDescription>Your MPIN is a quick, secure factor used at every login.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label>MPIN</Label>
            <Input type="password" value={mpin} onChange={(e) => setMpin(e.target.value.replace(/\D/g, "").slice(0, 6))}
              className="text-center text-2xl tracking-[0.5em]" placeholder="••••••" inputMode="numeric" />
          </div>
          <div className="space-y-1.5">
            <Label>Confirm MPIN</Label>
            <Input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value.replace(/\D/g, "").slice(0, 6))}
              className="text-center text-2xl tracking-[0.5em]" placeholder="••••••" inputMode="numeric" />
          </div>
        </div>
        <Button onClick={submit} loading={loading}>Set MPIN &amp; Continue</Button>
      </CardContent>
    </Card>
  );
}

/* ---------------------------- Second Factor --------------------------- */
function SecondFactorStep({ token, onDone }: { token: string; onDone: () => void }) {
  const [choice, setChoice] = useState<"face" | "passkey" | null>(null);
  const [busy, setBusy] = useState(false);

  async function finishDevice() {
    try {
      const info = await getDeviceInfo();
      await registerApi.registerDevice(token, info);
    } catch {
      /* non-fatal */
    }
  }

  async function enrollFace(embeddings: number[][]) {
    setBusy(true);
    try {
      await registerApi.enrollFace(token, embeddings);
      await finishDevice();
      toast.success("Face enrolled!");
      onDone();
    } catch (e) {
      toast.error(apiError(e));
    } finally {
      setBusy(false);
    }
  }

  async function enrollPasskey() {
    setBusy(true);
    try {
      const { handle, options } = await registerApi.passkeyOptions(token);
      const credential = await performRegistration(options);
      await registerApi.passkeyVerify(token, handle, credential);
      await finishDevice();
      toast.success("Passkey registered!");
      onDone();
    } catch (e: any) {
      toast.error(e?.name === "NotAllowedError" ? "Passkey prompt was dismissed." : apiError(e));
    } finally {
      setBusy(false);
    }
  }

  if (!choice) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><ShieldCheck className="h-5 w-5 text-primary" /> Choose your strong factor</CardTitle>
          <CardDescription>Pick one. You can add the other later from Settings.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2">
          <button onClick={() => setChoice("face")} className="group rounded-xl border border-border p-6 text-left transition-colors hover:border-primary/60 hover:bg-primary/5">
            <ScanFace className="h-8 w-8 text-primary" />
            <h3 className="mt-3 font-semibold">Face Verification</h3>
            <p className="mt-1 text-sm text-muted-foreground">Enroll your face using your device camera.</p>
          </button>
          <button
            onClick={() => (isWebAuthnSupported() ? setChoice("passkey") : toast.error("Passkeys not supported on this browser"))}
            className="group rounded-xl border border-border p-6 text-left transition-colors hover:border-primary/60 hover:bg-primary/5"
          >
            <Fingerprint className="h-8 w-8 text-primary" />
            <h3 className="mt-3 font-semibold">Passkey (WebAuthn)</h3>
            <p className="mt-1 text-sm text-muted-foreground">Windows Hello, Touch ID or a security key.</p>
          </button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          {choice === "face" ? <ScanFace className="h-5 w-5 text-primary" /> : <Fingerprint className="h-5 w-5 text-primary" />}
          {choice === "face" ? "Enroll your face" : "Register your passkey"}
        </CardTitle>
        <CardDescription>
          {choice === "face" ? "Position your face in the frame and capture." : "You'll be prompted by your device's authenticator."}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {choice === "face" ? (
          <FaceEnroll onEnroll={enrollFace} busy={busy} />
        ) : (
          <Button onClick={enrollPasskey} loading={busy} size="lg">
            <Fingerprint className="h-4 w-4" /> Create Passkey
          </Button>
        )}
        <Button variant="ghost" size="sm" onClick={() => setChoice(null)}>← Choose a different method</Button>
      </CardContent>
    </Card>
  );
}

/* ------------------------------ Complete ------------------------------ */
function CompleteStep({ onLogin }: { onLogin: () => void }) {
  return (
    <Card className="overflow-hidden">
      <div className="aurora p-10 text-center">
        <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: "spring" }}>
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-risk-safe/15">
            <PartyPopper className="h-8 w-8 text-risk-safe" />
          </div>
        </motion.div>
        <h2 className="mt-5 text-2xl font-bold">Registration complete!</h2>
        <p className="mx-auto mt-2 max-w-md text-muted-foreground">
          Your account is fully enrolled with multi-factor and adaptive protection. Sign in to
          experience the risk engine in action.
        </p>
        <Button className="mt-6" size="lg" onClick={onLogin}>
          Continue to Secure Login <ArrowRight className="h-4 w-4" />
        </Button>
      </div>
    </Card>
  );
}
