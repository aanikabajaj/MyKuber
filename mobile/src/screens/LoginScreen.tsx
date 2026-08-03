import React, { useEffect, useState } from "react";
import { Image, Pressable, Text, View } from "react-native";
import { useTranslation } from "react-i18next";
import {
  Screen, H2, Muted, Card, AppButton, TextField, Badge, Row, Divider, AuthTabs, OtpBoxes,
} from "../components/ui";
import { colors, fonts, bandColor } from "../theme";
import { captchaApi, loginApi, apiError, LoginSession } from "../lib/api";
import { getDeviceInfo } from "../lib/fingerprint";
import { verifyBiometric } from "../lib/biometric";
import { FaceScanner } from "../components/FaceScanner";
import { useAuth } from "../context/AuthContext";

export default function LoginScreen({ navigation }: any) {
  const { t } = useTranslation();
  const { setSession } = useAuth();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [captcha, setCaptcha] = useState<{ captcha_id: string; question: string } | null>(null);
  const [captchaAns, setCaptchaAns] = useState("");
  const [session, setSess] = useState<LoginSession | null>(null);
  const [stepValue, setStepValue] = useState("");
  const [otp, setOtp] = useState(["", "", "", "", "", ""]);
  const [otpSent, setOtpSent] = useState(false);
  const [devCode, setDevCode] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function loadCaptcha() {
    try { setCaptcha(await captchaApi.math()); setCaptchaAns(""); } catch {}
  }
  useEffect(() => { loadCaptcha(); }, []);

  function apply(s: LoginSession) {
    setSess(s);
    setStepValue("");
    setOtp(["", "", "", "", "", ""]);
    setOtpSent(false);
    setDevCode(null);
    if (s.status === "approved" && s.tokens) {
      setSession(s.tokens.access_token, s.tokens.refresh_token);
    }
  }

  async function submitPassword() {
    if (!captcha) return;
    setBusy(true); setError("");
    try {
      const device = await getDeviceInfo();
      const s = await loginApi.password({
        username, password,
        captcha_id: captcha.captcha_id, captcha_answer: captchaAns,
        device,
      });
      apply(s);
    } catch (e) { setError(apiError(e)); loadCaptcha(); setCaptchaAns(""); }
    finally { setBusy(false); }
  }

  async function sendOtp(kind: "email" | "sms") {
    if (!session?.session_id) return;
    setBusy(true); setError("");
    try {
      const r = kind === "email"
        ? await loginApi.emailOtpSend(session.session_id)
        : await loginApi.smsOtpSend(session.session_id);
      setOtpSent(true);
      setDevCode(r?.dev_code || null);
    } catch (e) { setError(apiError(e)); }
    finally { setBusy(false); }
  }

  async function doStep(otpOverride?: string) {
    if (!session?.session_id) return;
    const step = session.next_step;
    const val = otpOverride ?? stepValue;
    setBusy(true); setError("");
    try {
      let s: LoginSession;
      if (step === "mpin") s = await loginApi.mpin(session.session_id, val);
      else if (step === "email_otp") s = await loginApi.emailOtpVerify(session.session_id, val);
      else if (step === "sms_otp") s = await loginApi.smsOtpVerify(session.session_id, val);
      else if (step === "totp") s = await loginApi.totp(session.session_id, val);
      else return;
      apply(s);
    } catch (e) { setError(apiError(e)); }
    finally { setBusy(false); }
  }

  function onOtpChange(i: number, v: string) {
    const next = [...otp];
    next[i] = v;
    setOtp(next);
    const joined = next.join("");
    setStepValue(joined);
    if (joined.length === 6 && next.every((d) => d)) doStep(joined);
  }

  async function doSimCheck() {
    if (!session?.session_id) return;
    setBusy(true); setError("");
    try {
      // On Android this would come from IaareSimModule.getSimFingerprint().
      // On iOS / web we send a placeholder — the backend auto-passes demo accounts,
      // and non-demo users without a SIM enrolled never reach this step.
      const PLACEHOLDER_SIM = "0".repeat(64);
      const s = await loginApi.simVerify(session.session_id, PLACEHOLDER_SIM);
      apply(s);
    } catch (e) { setError(apiError(e)); }
    finally { setBusy(false); }
  }

  async function onFaceCaptured(images: string[]) {
    if (!session?.session_id || !images.length) return;
    setBusy(true); setError("");
    try { apply(await loginApi.faceImage(session.session_id, images[0])); }
    catch (e) { setError(apiError(e)); }
    finally { setBusy(false); }
  }

  async function doBiometric() {
    if (!session?.session_id) return;
    setBusy(true); setError("");
    try {
      const ok = await verifyBiometric("Verify to sign in");
      if (!ok) { setError("Biometric verification failed."); setBusy(false); return; }
      apply(await loginApi.biometric(session.session_id));
    } catch (e) { setError(apiError(e)); }
    finally { setBusy(false); }
  }

  const lblStyle = { color: colors.ink, fontSize: 12, fontFamily: fonts.bodyBold, marginBottom: 6 };

  // ---------- credentials phase ----------
  if (!session) {
    return (
      <Screen>
        <View style={{ flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 4 }}>
          <Image source={require("../../assets/kuber-logo-rect.png")} style={{ height: 26, width: 78 }} resizeMode="contain" />
        </View>

        <AuthTabs active="signin" onSignin={() => {}} onRegister={() => navigation.replace("Register")} />

        <Text style={{ fontSize: 21, fontFamily: fonts.headingXBold, color: colors.ink, marginBottom: 5 }}>Welcome back</Text>
        <Muted style={{ marginBottom: 4 }}>IAARE evaluates this session before granting access.</Muted>

        <Card style={{ marginTop: 12, borderWidth: 0, padding: 0, backgroundColor: "transparent", gap: 14 }}>
          <View>
            <Text style={lblStyle}>{t("login.username")}</Text>
            <TextField autoCapitalize="none" value={username} onChangeText={setUsername} placeholder="admin" />
          </View>
          <View>
            <Text style={lblStyle}>{t("login.password")}</Text>
            <TextField secureTextEntry value={password} onChangeText={setPassword} placeholder="••••••••" />
          </View>
          {captcha && (
            <View style={{ gap: 6 }}>
              <Muted>Solve to verify you're human</Muted>
              <View style={{ flexDirection: "row", alignItems: "center", gap: 10 }}>
                <View style={{ paddingHorizontal: 18, paddingVertical: 12, borderRadius: 10, backgroundColor: "#fbf7f9", borderWidth: 1.5, borderColor: colors.border }}>
                  <Text style={{ color: colors.ink, fontSize: 22, fontFamily: fonts.headingXBold, letterSpacing: 2 }}>{captcha.question} = ?</Text>
                </View>
                <Pressable onPress={loadCaptcha} hitSlop={10}>
                  <Text style={{ color: colors.brand, fontSize: 22 }}>↻</Text>
                </Pressable>
              </View>
              <TextField keyboardType="number-pad" maxLength={3} value={captchaAns} onChangeText={setCaptchaAns} placeholder="Answer" />
            </View>
          )}
          {error ? <Text style={{ color: colors.down }}>{error}</Text> : null}
          <AppButton title={`${t("common.login")} →`} onPress={submitPassword} loading={busy} />
          <Row style={{ justifyContent: "center", gap: 7 }}>
            <View style={{ width: 6, height: 6, borderRadius: 3, backgroundColor: colors.brand }} />
            <Muted style={{ fontSize: 11.5 }}>256-bit encrypted · IAARE adaptive auth</Muted>
          </Row>
        </Card>

        <Muted style={{ marginTop: 8 }}>Demo accounts (tap to fill):</Muted>
        <Row style={{ gap: 8, justifyContent: "flex-start" }}>
          <AppButton title="admin" variant="outline" onPress={() => { setUsername("admin"); setPassword("Admin@1234"); }} />
          <AppButton title="rahul" variant="outline" onPress={() => { setUsername("rahul"); setPassword("Rahul@1234"); }} />
        </Row>
        <Muted style={{ fontSize: 12 }}>Answer the simple equation above · tap ↻ for a new one.</Muted>
      </Screen>
    );
  }

  // ---------- blocked ----------
  if (session.status === "blocked") {
    return (
      <Screen>
        <Card style={{ borderColor: colors.down, marginTop: 40 }}>
          <Badge label={t("risk.CRITICAL")} color={colors.down} />
          <H2>{t("login.blocked")}</H2>
          <Muted>{session.message}</Muted>
          <AppButton title={t("common.back")} variant="outline" onPress={() => setSess(null)} />
        </Card>
      </Screen>
    );
  }

  // ---------- stepping phase ----------
  const step = session.next_step;
  const bc = bandColor(session.risk.band);
  const needsStepUp = session.risk.band === "MEDIUM" || session.risk.band === "HIGH";
  return (
    <Screen>
      {needsStepUp && (
        <View style={{ flexDirection: "row", alignItems: "center", gap: 8, padding: 11, borderRadius: 12, backgroundColor: colors.warnBg, borderWidth: 1.5, borderColor: colors.warnBorder }}>
          <Text style={{ fontSize: 15 }}>⚠</Text>
          <Text style={{ flex: 1, fontSize: 11.5, color: "#8a6516", lineHeight: 16 }}>
            <Text style={{ fontFamily: fonts.bodyBold }}>Step-up required.</Text> Risk band <Text style={{ fontFamily: fonts.bodyBold }}>{session.risk.band}</Text>.
          </Text>
        </View>
      )}

      <Card style={{ borderColor: bc, borderWidth: 1.5 }}>
        <Row>
          <View>
            <Muted>{t("login.riskScore")}</Muted>
            <Text style={{ color: colors.ink, fontSize: 32, fontFamily: fonts.headingXBold }}>{session.risk.score}</Text>
          </View>
          <Badge label={t(`risk.${session.risk.band}`)} color={bc} />
        </Row>
        <Divider />
        {session.risk.factors.slice(0, 4).map((f, i) => (
          <Row key={i}>
            <Muted style={{ flex: 1 }}>{f.detail}</Muted>
            <Text style={{ color: f.points > 0 ? colors.down : colors.up, fontFamily: fonts.bodyBold }}>
              {f.points > 0 ? `+${f.points}` : "0"}
            </Text>
          </Row>
        ))}
      </Card>

      <Card>
        <H2>Verify it's you</H2>
        <Muted style={{ fontSize: 12.5 }}>{stepLabel(step, t)}</Muted>
        {step === "mpin" && (
          <>
            <TextField label={t("login.enterMpin")} keyboardType="number-pad" secureTextEntry maxLength={6} value={stepValue} onChangeText={setStepValue} placeholder="••••••" />
            <AppButton title={t("common.verify")} onPress={() => doStep()} loading={busy} />
          </>
        )}
        {step === "second_factor" && (
          session.second_factor === "face" ? (
            <FaceScanner mode="verify" onDone={onFaceCaptured} busy={busy} />
          ) : (
            <>
              <Muted>{t("login.faceVerify")}</Muted>
              <AppButton title={t("login.faceVerify")} onPress={doBiometric} loading={busy} variant="accent" />
            </>
          )
        )}
        {(step === "email_otp" || step === "sms_otp") && (
          <>
            {!otpSent ? (
              <AppButton title={`Send ${step === "email_otp" ? "Email" : "SMS"} OTP`} onPress={() => sendOtp(step === "email_otp" ? "email" : "sms")} loading={busy} />
            ) : (
              <>
                {devCode ? <Badge label={`DEMO code: ${devCode}`} color={colors.brand2} /> : null}
                <Muted style={{ fontSize: 12.5 }}>6-digit code sent to your {step === "email_otp" ? "email" : "phone"}.</Muted>
                <OtpBoxes value={otp} onChange={onOtpChange} />
                <AppButton title={t("common.verify")} onPress={() => doStep()} loading={busy} />
              </>
            )}
          </>
        )}
        {step === "totp" && (
          <>
            <TextField label={t("login.authenticator")} keyboardType="number-pad" maxLength={6} value={stepValue} onChangeText={setStepValue} placeholder="______" />
            <AppButton title={t("common.verify")} onPress={() => doStep()} loading={busy} />
          </>
        )}
        {step === "sim_check" && (
          <>
            <Muted style={{ textAlign: "center", fontSize: 13 }}>
              🔒 SIM Card Verification{"\n"}
              Confirming your registered SIM is present in this device.
            </Muted>
            <AppButton title="Verify SIM" variant="accent" onPress={doSimCheck} loading={busy} />
            <Muted style={{ fontSize: 11, textAlign: "center" }}>
              Make sure the SIM registered with your account is inserted.
            </Muted>
          </>
        )}
        {error ? <Text style={{ color: colors.down }}>{error}</Text> : null}
      </Card>

      <Muted style={{ textAlign: "center" }}>
        {(session.completed_steps?.length || 0)} / {session.required_steps?.length || 0} factors verified
      </Muted>
    </Screen>
  );
}

function stepLabel(step: string | null, t: any): string {
  const map: Record<string, string> = {
    mpin: t("login.enterMpin"), second_factor: t("login.faceVerify"),
    email_otp: t("login.emailOtp"), sms_otp: t("login.smsOtp"), totp: t("login.authenticator"),
  };
  return step ? map[step] || step : "—";
}
