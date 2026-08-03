import React, { useState } from "react";
import { Image, Text, View } from "react-native";
import { useTranslation } from "react-i18next";
import { Screen, H2, Muted, Card, AppButton, TextField, Badge, Row, AuthTabs, OtpBoxes } from "../components/ui";
import { colors, fonts } from "../theme";
import { registerApi, apiError } from "../lib/api";
import { getDeviceInfo } from "../lib/fingerprint";
import { FaceScanner } from "../components/FaceScanner";

// Registration stages now match backend:
//   details → mobile → email → sim_verify → mpin → face → done
type Step = "details" | "mobile" | "email" | "sim_verify" | "mpin" | "face" | "done";
const ORDER: Step[] = ["details", "mobile", "email", "sim_verify", "mpin", "face", "done"];

export default function RegisterScreen({ navigation }: any) {
  const { t } = useTranslation();
  const [step, setStep]   = useState<Step>("details");
  const [token, setToken] = useState("");
  const [busy, setBusy]   = useState(false);
  const [error, setError] = useState("");

  // details fields
  const [f, setF] = useState({
    first_name: "", last_name: "", email: "", mobile: "",
    username: "", password: "", confirm_password: "",
  });
  const set = (k: string, v: string) => setF((p) => ({ ...p, [k]: v }));

  // shared OTP state
  const [code, setCode]       = useState("");
  const [otpBoxes, setOtpBoxes] = useState(["", "", "", "", "", ""]);
  const [devCode, setDevCode] = useState<string | null>(null);
  const [mpin, setMpin]       = useState("");

  const idx = ORDER.indexOf(step);

  function resetOtpUi() {
    setCode("");
    setOtpBoxes(["", "", "", "", "", ""]);
  }

  // ── Step 1: account details ──────────────────────────────────────────────
  async function submitDetails() {
    setBusy(true); setError("");
    try {
      const r = await registerApi.details({ ...f, country: "India" });
      setToken(r.registration_token);
      setStep("mobile");
      await sendOtp("mobile", r.registration_token);
    } catch (e) { setError(apiError(e)); }
    finally { setBusy(false); }
  }

  // ── OTP helpers ──────────────────────────────────────────────────────────
  async function sendOtp(kind: "mobile" | "email", tk = token) {
    setError(""); resetOtpUi();
    try {
      const r = kind === "mobile"
        ? await registerApi.mobileSend(tk)
        : await registerApi.emailSend(tk);
      setDevCode(r?.dev_code || null);
    } catch (e) { setError(apiError(e)); }
  }

  async function verifyOtp(kind: "mobile" | "email", codeOverride?: string) {
    setBusy(true); setError("");
    try {
      const val = codeOverride ?? code;
      if (kind === "mobile") {
        await registerApi.mobileVerify(token, val);
        setStep("email");
        await sendOtp("email");
      } else {
        await registerApi.emailVerify(token, val);
        // After email OTP → sim_verify (backend returns stage="sim_verify")
        setStep("sim_verify");
        await sendSimOtp();
      }
      resetOtpUi(); setDevCode(null);
    } catch (e) { setError(apiError(e)); }
    finally { setBusy(false); }
  }

  function onOtpChange(kind: "mobile" | "email" | "sim", i: number, v: string) {
    const next = [...otpBoxes];
    next[i] = v;
    setOtpBoxes(next);
    const joined = next.join("");
    setCode(joined);
    if (joined.length === 6 && next.every((d) => d)) {
      if (kind === "sim") confirmSimVerify(joined);
      else verifyOtp(kind, joined);
    }
  }

  // ── Step 4: SIM verification ─────────────────────────────────────────────
  async function sendSimOtp() {
    setError(""); resetOtpUi();
    try {
      const r = await registerApi.simVerifySend(token);
      setDevCode(r?.dev_code || null);
    } catch (e) { setError(apiError(e)); }
  }

  async function confirmSimVerify(codeOverride?: string) {
    setBusy(true); setError("");
    try {
      // sim_fingerprint is Android-only. On iOS / web we skip it (undefined).
      // The backend accepts null/undefined gracefully.
      await registerApi.simVerifyConfirm(token, codeOverride ?? code, undefined);
      resetOtpUi(); setDevCode(null);
      setStep("mpin");
    } catch (e) { setError(apiError(e)); }
    finally { setBusy(false); }
  }

  // ── Step 5: MPIN ──────────────────────────────────────────────────────────
  async function submitMpin() {
    setBusy(true); setError("");
    try {
      await registerApi.setMpin(token, mpin);
      setStep("face");
    } catch (e) { setError(apiError(e)); }
    finally { setBusy(false); }
  }

  // ── Step 6: face enroll ───────────────────────────────────────────────────
  async function enrollFace(images: string[]) {
    setBusy(true); setError("");
    try {
      await registerApi.enrollFaceImages(token, images);
      const device = await getDeviceInfo();
      await registerApi.registerDevice(token, device);
      setStep("done");
    } catch (e) { setError(apiError(e)); }
    finally { setBusy(false); }
  }

  const lblStyle = { color: colors.ink, fontSize: 12, fontFamily: fonts.bodyBold, marginBottom: 6 };

  // ─────────────────────────────────────────────────────────────────────────
  return (
    <Screen>
      {step === "details" ? (
        <>
          <View style={{ flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 4 }}>
            <Image source={require("../../assets/kuber-logo-rect.png")} style={{ height: 26, width: 78 }} resizeMode="contain" />
          </View>
          <AuthTabs active="register" onSignin={() => navigation.replace("Login")} onRegister={() => {}} />
          <Text style={{ fontSize: 21, fontFamily: fonts.headingXBold, color: colors.ink, marginBottom: 5 }}>Create your account</Text>
          <Muted style={{ marginBottom: 4 }}>Set up your My Kuber twin.</Muted>
        </>
      ) : (
        <Row>
          <H2>{t("common.register")}</H2>
          {step !== "done" && <Badge label={`${idx + 1} / ${ORDER.length - 1}`} color={colors.brand} />}
        </Row>
      )}

      {/* ── Step 1: account details ── */}
      {step === "details" && (
        <Card style={{ borderWidth: 0, padding: 0, backgroundColor: "transparent", gap: 14 }}>
          <Row style={{ gap: 10 }}>
            <View style={{ flex: 1 }}>
              <Text style={lblStyle}>First name</Text>
              <TextField value={f.first_name} onChangeText={(v) => set("first_name", v)} />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={lblStyle}>Last name</Text>
              <TextField value={f.last_name} onChangeText={(v) => set("last_name", v)} />
            </View>
          </Row>
          <View>
            <Text style={lblStyle}>Email</Text>
            <TextField autoCapitalize="none" keyboardType="email-address" value={f.email} onChangeText={(v) => set("email", v)} />
          </View>
          <View>
            <Text style={lblStyle}>Mobile (+91…)</Text>
            <TextField keyboardType="phone-pad" value={f.mobile} onChangeText={(v) => set("mobile", v)} placeholder="+919812345678" />
          </View>
          <View>
            <Text style={lblStyle}>{t("login.username")}</Text>
            <TextField autoCapitalize="none" value={f.username} onChangeText={(v) => set("username", v)} />
          </View>
          <View>
            <Text style={lblStyle}>{t("login.password")}</Text>
            <TextField secureTextEntry value={f.password} onChangeText={(v) => set("password", v)} />
          </View>
          <View>
            <Text style={lblStyle}>Confirm password</Text>
            <TextField secureTextEntry value={f.confirm_password} onChangeText={(v) => set("confirm_password", v)} />
          </View>
          <Muted style={{ fontSize: 12 }}>8+ chars with upper, lower, number & symbol.</Muted>
          {error ? <Text style={{ color: colors.down }}>{error}</Text> : null}
          <AppButton title={`${t("common.continue")} →`} onPress={submitDetails} loading={busy} />
        </Card>
      )}

      {/* ── Steps 2 & 3: mobile + email OTP ── */}
      {(step === "mobile" || step === "email") && (
        <Card>
          <H2>{step === "mobile" ? "Verify mobile" : "Verify email"}</H2>
          <Muted>Enter the 6-digit code sent to your {step === "mobile" ? "phone" : "email"}.</Muted>
          {devCode ? <Badge label={`DEMO code: ${devCode}`} color={colors.brand2} /> : null}
          <OtpBoxes value={otpBoxes} onChange={(i, v) => onOtpChange(step, i, v)} />
          {error ? <Text style={{ color: colors.down }}>{error}</Text> : null}
          <AppButton title={t("common.verify")} onPress={() => verifyOtp(step as "mobile" | "email")} loading={busy} />
          <AppButton title="Resend code" variant="ghost" onPress={() => sendOtp(step as "mobile" | "email")} />
        </Card>
      )}

      {/* ── Step 4: SIM verification ── */}
      {step === "sim_verify" && (
        <Card>
          <H2>📱 Verify your SIM</H2>
          <Muted>
            We sent a 6-digit code to your registered mobile number to confirm
            your SIM card. This binds your physical SIM to this account — an
            extra layer of security that blocks logins from other devices.
          </Muted>
          {devCode ? <Badge label={`DEMO code: ${devCode}`} color={colors.brand2} /> : null}
          <OtpBoxes value={otpBoxes} onChange={(i, v) => onOtpChange("sim", i, v)} />
          {error ? <Text style={{ color: colors.down }}>{error}</Text> : null}
          <AppButton title="Confirm SIM" onPress={() => confirmSimVerify()} loading={busy} />
          <AppButton title="Resend code" variant="ghost" onPress={sendSimOtp} />
          <Muted style={{ fontSize: 11 }}>
            iOS or no SIM? Tap "Skip for now" — SIM check will be inactive until
            you bind a SIM from Settings.
          </Muted>
          <AppButton
            title="Skip for now"
            variant="ghost"
            onPress={async () => {
              // Skip without confirming OTP — backend stage stays compatible
              // because sim_enrolled defaults to false, skipping sim_check in login.
              try {
                setBusy(true);
                setStep("mpin");
              } finally {
                setBusy(false);
              }
            }}
          />
        </Card>
      )}

      {/* ── Step 5: MPIN ── */}
      {step === "mpin" && (
        <Card>
          <H2>Create MPIN</H2>
          <Muted>Choose a 6-digit PIN for quick, secure access.</Muted>
          <TextField label="6-digit MPIN" keyboardType="number-pad" secureTextEntry
            maxLength={6} value={mpin} onChangeText={setMpin} placeholder="••••••" />
          {error ? <Text style={{ color: colors.down }}>{error}</Text> : null}
          <AppButton title={`${t("common.continue")} →`} onPress={submitMpin} loading={busy} />
        </Card>
      )}

      {/* ── Step 6: face enroll ── */}
      {step === "face" && (
        <Card>
          <H2>Enroll your face</H2>
          <Muted>Look at the camera and slowly move your head so we capture a few angles.</Muted>
          <FaceScanner mode="enroll" onDone={enrollFace} busy={busy} />
          {error ? <Text style={{ color: colors.down }}>{error}</Text> : null}
        </Card>
      )}

      {/* ── Done ── */}
      {step === "done" && (
        <Card style={{ borderColor: colors.up, alignItems: "center", gap: 12 }}>
          <Text style={{ fontSize: 48 }}>🎉</Text>
          <H2>Registration complete!</H2>
          <Muted style={{ textAlign: "center" }}>
            Your account is ready. Sign in with adaptive authentication.
          </Muted>
          <AppButton title={t("landing.secureLogin")}
            onPress={() => navigation.replace("Login")} />
        </Card>
      )}
    </Screen>
  );
}
