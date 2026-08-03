import React, { useEffect, useState } from "react";
import { Pressable, Switch, Text, View } from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { useTranslation } from "react-i18next";
import { AppShell, securityScoreFor } from "../components/AppShell";
import { Card, Muted, AppButton, TextField, Row, Divider } from "../components/ui";
import { colors, fonts, radius } from "../theme";
import { userApi, apiError } from "../lib/api";
import { LANGUAGES, setLanguage } from "../i18n";
import { useAuth } from "../context/AuthContext";

const DECISION_TIERS = [
  { tierKey: "settings.tierAllow", condKey: "settings.tierAllowCond", glyph: "✔", color: colors.up, bg: colors.upBg },
  { tierKey: "settings.tierMpin", condKey: "settings.tierMpinCond", glyph: "✉", color: colors.brand, bg: colors.pinkTint },
  { tierKey: "settings.tierSim", condKey: "settings.tierSimCond", glyph: "⛊", color: colors.warn, bg: colors.warnBg },
  { tierKey: "settings.tierBlock", condKey: "settings.tierBlockCond", glyph: "✕", color: colors.down, bg: colors.downBg },
];

export default function ProtectionScreen() {
  const { t, i18n } = useTranslation();
  const { logout, refresh, user } = useAuth();
  const [faceLogin, setFaceLogin] = useState(true);
  const [faceTxn, setFaceTxn] = useState(true);
  const [threshold, setThreshold] = useState("10000");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [lang, setLang] = useState(i18n.language);

  useEffect(() => {
    (async () => {
      try {
        const p = await userApi.prefs();
        setFaceLogin(!!p.face_login_enabled);
        setFaceTxn(!!p.face_txn_enabled);
        setThreshold(String(p.txn_face_threshold ?? 10000));
      } catch {}
    })();
  }, []);

  async function save() {
    setBusy(true); setMsg("");
    try {
      await userApi.updatePrefs({
        face_login_enabled: faceLogin,
        face_txn_enabled: faceTxn,
        txn_face_threshold: Number(threshold) || 0,
        preferred_language: lang,
      });
      setMsg(t("settings.saved"));
      refresh();
    } catch (e) { setMsg(apiError(e)); }
    finally { setBusy(false); }
  }

  async function pickLang(code: string) {
    setLang(code);
    await setLanguage(code);
  }

  const score = securityScoreFor(user);

  return (
    <AppShell title={t("nav.wealthProtection")} mode="back">
      {/* Protection score hero */}
      <LinearGradient colors={[colors.brandDeep, colors.brand]} start={{ x: 0.1, y: 0 }} end={{ x: 0.9, y: 1 }} style={{ borderRadius: 16, padding: 22, alignItems: "center" }}>
        <Text style={{ fontSize: 11, color: "rgba(255,255,255,.75)" }}>{t("settings.protectionScore")}</Text>
        <Text style={{ fontFamily: fonts.mono, fontSize: 44, fontWeight: "600", color: colors.pink, marginVertical: 4 }}>{score}</Text>
        <Text style={{ fontSize: 12, color: "rgba(255,255,255,.82)" }}>
          {score >= 85 ? t("settings.riskLow") : score >= 65 ? t("settings.riskModerate") : t("settings.riskAddFactors")}
        </Text>
      </LinearGradient>

      {/* Decision tiers (real backend policy) */}
      <View style={{ gap: 9 }}>
        {DECISION_TIERS.map((d) => (
          <View key={d.tierKey} style={{ flexDirection: "row", alignItems: "center", gap: 11, padding: 13, backgroundColor: colors.card, borderWidth: 1.5, borderColor: colors.line, borderRadius: 12 }}>
            <View style={{ width: 32, height: 32, borderRadius: 9, backgroundColor: d.bg, alignItems: "center", justifyContent: "center" }}>
              <Text style={{ color: d.color, fontSize: 14 }}>{d.glyph}</Text>
            </View>
            <View>
              <Text style={{ fontSize: 12.5, fontFamily: fonts.bodyBold, color: colors.ink }}>{t(d.tierKey)}</Text>
              <Text style={{ fontSize: 10.5, color: colors.grey, fontFamily: fonts.mono }}>{t(d.condKey)}</Text>
            </View>
          </View>
        ))}
      </View>

      {/* Real security settings */}
      <Card>
        <Text style={{ fontSize: 13.5, fontFamily: fonts.bodyBold, color: colors.ink }}>{t("settings.security")}</Text>
        <Row>
          <View style={{ flex: 1, paddingRight: 12 }}>
            <Text style={{ color: colors.ink, fontFamily: fonts.bodySemi }}>{t("settings.faceLogin")}</Text>
            <Muted style={{ fontSize: 12 }}>{t("settings.faceLoginDesc")}</Muted>
          </View>
          <Switch value={faceLogin} onValueChange={setFaceLogin} trackColor={{ true: colors.brand }} />
        </Row>
        <Divider />
        <Row>
          <View style={{ flex: 1, paddingRight: 12 }}>
            <Text style={{ color: colors.ink, fontFamily: fonts.bodySemi }}>{t("settings.faceTxn")}</Text>
            <Muted style={{ fontSize: 12 }}>{t("settings.faceTxnDesc")}</Muted>
          </View>
          <Switch value={faceTxn} onValueChange={setFaceTxn} trackColor={{ true: colors.brand }} />
        </Row>
        <Divider />
        <TextField label={t("settings.threshold")} keyboardType="number-pad" value={threshold} onChangeText={setThreshold} editable={faceTxn} />
        <Muted style={{ fontSize: 12 }}>{t("settings.thresholdHint")}</Muted>
      </Card>

      <Card>
        <Text style={{ fontSize: 13.5, fontFamily: fonts.bodyBold, color: colors.ink }}>{t("settings.language")}</Text>
        {LANGUAGES.map((l, i) => (
          <View key={l.code}>
            {i > 0 && <Divider />}
            <Pressable onPress={() => pickLang(l.code)} style={{ paddingVertical: 6 }}>
              <Row>
                <View>
                  <Text style={{ color: colors.ink, fontFamily: fonts.bodySemi, fontSize: 16 }}>{l.native}</Text>
                  <Muted style={{ fontSize: 12 }}>{l.label}</Muted>
                </View>
                <View style={{
                  width: 22, height: 22, borderRadius: radius.pill, borderWidth: 2,
                  borderColor: lang === l.code ? colors.brand : colors.border,
                  backgroundColor: lang === l.code ? colors.brand : "transparent",
                }} />
              </Row>
            </Pressable>
          </View>
        ))}
      </Card>

      {msg ? <Text style={{ color: colors.up }}>{msg}</Text> : null}
      <AppButton title={t("common.save")} onPress={save} loading={busy} />
      <AppButton title={t("common.logout")} variant="danger" onPress={logout} />
    </AppShell>
  );
}
