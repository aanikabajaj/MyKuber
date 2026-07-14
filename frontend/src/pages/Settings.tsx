import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Fingerprint, KeyRound, ScanFace, Trash2, Plus, ShieldCheck } from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { FaceCapture } from "@/components/FaceCapture";
import { useAuth } from "@/context/AuthContext";
import { userApi, apiError } from "@/lib/api";
import { performRegistration } from "@/lib/webauthn";
import { formatDate } from "@/lib/utils";

export function Settings() {
  const { user, refresh } = useAuth();
  return (
    <div className="min-h-screen">
      <Navbar />
      <div className="container max-w-4xl py-10">
        <h1 className="text-3xl font-bold">Security Settings</h1>
        <p className="mt-1 text-muted-foreground">Manage the factors protecting your account.</p>

        <Tabs defaultValue="mpin" className="mt-8">
          <TabsList>
            <TabsTrigger value="mpin">MPIN</TabsTrigger>
            <TabsTrigger value="face">Face</TabsTrigger>
            <TabsTrigger value="passkeys">Passkeys</TabsTrigger>
          </TabsList>

          <TabsContent value="mpin"><MpinReset /></TabsContent>
          <TabsContent value="face"><FaceReenroll onDone={refresh} enabled={user?.second_factor === "face"} /></TabsContent>
          <TabsContent value="passkeys"><Passkeys /></TabsContent>
        </Tabs>
      </div>
      <Footer />
    </div>
  );
}

function MpinReset() {
  const [pw, setPw] = useState("");
  const [mpin, setMpin] = useState("");
  const [loading, setLoading] = useState(false);
  async function submit() {
    if (mpin.length !== 6) return toast.error("MPIN must be 6 digits");
    setLoading(true);
    try { await userApi.resetMpin(pw, mpin); toast.success("MPIN updated"); setPw(""); setMpin(""); }
    catch (e) { toast.error(apiError(e)); }
    finally { setLoading(false); }
  }
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2"><KeyRound className="h-5 w-5 text-primary" /> Reset MPIN</CardTitle>
        <CardDescription>Confirm your password, then set a new 6-digit MPIN.</CardDescription>
      </CardHeader>
      <CardContent className="max-w-sm space-y-4">
        <div className="space-y-1.5"><Label>Current password</Label>
          <Input type="password" value={pw} onChange={(e) => setPw(e.target.value)} /></div>
        <div className="space-y-1.5"><Label>New MPIN</Label>
          <Input type="password" value={mpin} onChange={(e) => setMpin(e.target.value.replace(/\D/g, "").slice(0, 6))}
            className="text-center text-2xl tracking-[0.5em]" placeholder="••••••" inputMode="numeric" /></div>
        <Button onClick={submit} loading={loading}>Update MPIN</Button>
      </CardContent>
    </Card>
  );
}

function FaceReenroll({ onDone, enabled }: { onDone: () => void; enabled: boolean }) {
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState(false);
  async function capture(embedding: number[]) {
    setBusy(true);
    try { await userApi.reenrollFace(embedding); toast.success("Face re-enrolled"); setOpen(false); onDone(); }
    catch (e) { toast.error(apiError(e)); }
    finally { setBusy(false); }
  }
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2"><ScanFace className="h-5 w-5 text-primary" /> Face Verification</CardTitle>
        <CardDescription>
          {enabled ? <Badge variant="success"><ShieldCheck className="h-3 w-3" /> Enrolled</Badge> : "Not currently your strong factor."} Re-capture to update your enrolled face.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {open ? (
          <FaceCapture onCapture={capture} label="Save New Face" busy={busy} />
        ) : (
          <Button onClick={() => setOpen(true)} variant="outline"><ScanFace className="h-4 w-4" /> Re-enroll Face</Button>
        )}
      </CardContent>
    </Card>
  );
}

function Passkeys() {
  const [list, setList] = useState<any[]>([]);
  const [busy, setBusy] = useState(false);
  async function load() { try { setList(await userApi.passkeys()); } catch { /* ignore */ } }
  useEffect(() => { load(); }, []);

  async function add() {
    setBusy(true);
    try {
      const { handle, options } = await userApi.addPasskeyOptions();
      const credential = await performRegistration(options);
      await userApi.addPasskeyVerify(handle, credential);
      toast.success("Passkey added"); load();
    } catch (e: any) {
      toast.error(e?.name === "NotAllowedError" ? "Passkey prompt dismissed." : apiError(e));
    } finally { setBusy(false); }
  }
  async function remove(id: number) {
    try { await userApi.removePasskey(id); toast.success("Passkey removed"); load(); }
    catch (e) { toast.error(apiError(e)); }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2"><Fingerprint className="h-5 w-5 text-primary" /> Passkeys</CardTitle>
        <CardDescription>FIDO2/WebAuthn credentials bound to this device or a security key.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {list.length === 0 && <p className="text-sm text-muted-foreground">No passkeys registered.</p>}
        {list.map((p) => (
          <div key={p.id} className="flex items-center justify-between rounded-lg border border-border bg-secondary/30 p-3">
            <div className="flex items-center gap-3">
              <Fingerprint className="h-4 w-4 text-primary" />
              <div>
                <div className="text-sm font-medium">{p.label || "Passkey"}</div>
                <div className="text-xs text-muted-foreground">Added {formatDate(p.created_at)}</div>
              </div>
            </div>
            <Button variant="ghost" size="icon" onClick={() => remove(p.id)}><Trash2 className="h-4 w-4 text-risk-high" /></Button>
          </div>
        ))}
        <Button onClick={add} loading={busy} variant="outline"><Plus className="h-4 w-4" /> Add Passkey</Button>
      </CardContent>
    </Card>
  );
}
