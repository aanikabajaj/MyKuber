import React, { useCallback, useState } from "react";
import { Pressable, Text, View } from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import { useTranslation } from "react-i18next";
import Svg, { Defs, LinearGradient as SvgGradient, Polygon, Polyline, Stop } from "react-native-svg";
import { LinearGradient } from "expo-linear-gradient";
import { AppShell } from "../components/AppShell";
import { Card, H2, Muted, Row, Divider } from "../components/ui";
import { colors, fonts, radius } from "../theme";
import { txnApi, aiProfileApi, aiTxnApi } from "../lib/api";
import { useAuth } from "../context/AuthContext";

const fmt = (n: number) => "₹" + Number(n || 0).toLocaleString("en-IN", { minimumFractionDigits: 2 });
const fmtShort = (n: number) => {
  const abs = Math.abs(n);
  if (abs >= 10000000) return "₹" + (n / 10000000).toFixed(2).replace(/\.00$/, "") + " Cr";
  if (abs >= 100000) return "₹" + (n / 100000).toFixed(2).replace(/\.00$/, "") + " L";
  if (abs >= 1000) return "₹" + (n / 1000).toFixed(0) + "K";
  return "₹" + Math.round(n);
};

function buildLine(vals: number[], w: number, h: number, pad: number) {
  if (vals.length < 2) vals = [vals[0] ?? 0, vals[0] ?? 0];
  const min = Math.min(...vals), max = Math.max(...vals);
  const dx = (w - pad * 2) / (vals.length - 1);
  const pts = vals.map((v, i) => [pad + dx * i, h - pad - ((v - min) / ((max - min) || 1)) * (h - pad * 2)]);
  const line = pts.map((p) => `${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(" ");
  const area = `${pad},${h - pad} ${line} ${(pad + dx * (vals.length - 1)).toFixed(1)},${h - pad}`;
  return { line, area };
}

interface QuickAction { icon: string; labelKey: string; screen: string; }
const QUICK_ACTIONS: QuickAction[] = [
  { icon: "⇄", labelKey: "dashboard.transfer", screen: "Transfer" },
  { icon: "✧", labelKey: "dashboard.quickAI", screen: "AIChat" },
  { icon: "◎", labelKey: "dashboard.quickGoals", screen: "Goals" },
  { icon: "⛊", labelKey: "dashboard.quickProtection", screen: "Protection" },
];

export default function DashboardScreen({ navigation }: any) {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [balance, setBalance] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [goals, setGoals] = useState<string[]>([]);
  const [insight, setInsight] = useState<{ category: string; amount: string } | { anomalyCount: number } | null>(null);

  useFocusEffect(
    useCallback(() => {
      let active = true;
      (async () => {
        try {
          const [b, h] = await Promise.all([txnApi.balance(), txnApi.history()]);
          if (active) { setBalance(b); setHistory(h); }
        } catch {}
      })();
      // Best-effort AI extras — dashboard must render fine without the AI gateway.
      aiProfileApi.get().then((p) => { if (active) setGoals(p.investment_goals || []); }).catch(() => {});
      aiTxnApi.analyze().then((a) => {
        if (!active) return;
        const top = Object.entries(a.category_breakdown || {}).sort((x, y) => y[1] - x[1])[0];
        if (top) setInsight({ category: top[0], amount: fmtShort(top[1]) });
        else if (a.anomaly_spikes?.length) setInsight({ anomalyCount: a.anomaly_spikes.length });
      }).catch(() => {});
      return () => { active = false; };
    }, [])
  );

  const bal = balance?.balance ?? 0;
  const n = Math.min(history.length, 8);
  const balancesNewestFirst: number[] = [];
  let running = bal;
  for (let i = 0; i < n; i++) { balancesNewestFirst.push(running); running += Number(history[i]?.amount || 0); }
  const series = balancesNewestFirst.slice().reverse().concat(n === 0 ? [bal] : []);
  const chart = buildLine(series.length ? series : [bal, bal], 340, 90, 8);

  const monthKey = new Date().toISOString().slice(0, 7);
  const thisMonthSpend = history
    .filter((t) => (t.created_at || t.date || "").slice(0, 7) === monthKey || !t.created_at)
    .reduce((s, t) => s + Number(t.amount || 0), 0);

  return (
    <AppShell title={t("nav.dashboard")} mode="menu">
      <Row>
        <View>
          <Muted>{t("dashboard.welcomeBack")}</Muted>
          <Text style={{ color: colors.ink, fontSize: 22, fontFamily: fonts.headingXBold }}>
            {user?.first_name || user?.username}
          </Text>
        </View>
      </Row>

      {/* Net worth / balance hero */}
      <LinearGradient
        colors={[colors.brandDeep, colors.brand]}
        start={{ x: 0.1, y: 0 }} end={{ x: 0.9, y: 1 }}
        style={{ borderRadius: 16, padding: 20, gap: 4 }}
      >
        <Text style={{ color: "rgba(255,255,255,.75)", fontSize: 12 }}>{t("dashboard.availableBalance")}</Text>
        <Text style={{ color: "#fff", fontFamily: fonts.mono, fontSize: 27, fontWeight: "600", letterSpacing: -0.5 }}>
          {balance ? fmt(bal) : "…"}
        </Text>
        <Text style={{ color: colors.pink, fontSize: 12, fontFamily: fonts.bodyBold }}>
          {user?.account_number ? `${t("dashboard.accountPrefix")} ${user.account_number}` : t("dashboard.psbMyKuber")}
        </Text>
        {series.length > 1 && (
          <Svg viewBox="0 0 340 90" style={{ width: "100%", height: 70, marginTop: 10 }}>
            <Defs>
              <SvgGradient id="nwg" x1="0" y1="0" x2="0" y2="1">
                <Stop offset="0%" stopColor="#FFB6C1" stopOpacity={0.35} />
                <Stop offset="100%" stopColor="#FFB6C1" stopOpacity={0} />
              </SvgGradient>
            </Defs>
            <Polygon points={chart.area} fill="url(#nwg)" />
            <Polyline points={chart.line} fill="none" stroke="#FFB6C1" strokeWidth={2.5} strokeLinejoin="round" strokeLinecap="round" />
          </Svg>
        )}
      </LinearGradient>

      {/* KPI tiles */}
      <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 10 }}>
        <Card style={{ flex: 1, minWidth: "45%" }}>
          <Muted style={{ fontSize: 11, fontFamily: fonts.bodySemi }}>{t("dashboard.thisMonthSpend")}</Muted>
          <Text style={{ fontFamily: fonts.mono, fontSize: 19, color: colors.ink }}>{fmtShort(thisMonthSpend)}</Text>
          <Text style={{ fontSize: 11, fontFamily: fonts.bodyBold, color: colors.down }}>{t("dashboard.transfersCount", { count: history.length })}</Text>
        </Card>
        <Card style={{ flex: 1, minWidth: "45%" }}>
          <Muted style={{ fontSize: 11, fontFamily: fonts.bodySemi }}>{t("dashboard.investmentGoalsLabel")}</Muted>
          <Text style={{ fontFamily: fonts.mono, fontSize: 19, color: colors.ink }}>{goals.length || "—"}</Text>
          <Text style={{ fontSize: 11, fontFamily: fonts.bodyBold, color: colors.up }}>{t("dashboard.tracked")}</Text>
        </Card>
      </View>

      {/* Quick actions */}
      <View style={{ flexDirection: "row", gap: 10 }}>
        {QUICK_ACTIONS.map((a) => (
          <Pressable
            key={a.screen}
            onPress={() => navigation.navigate(a.screen)}
            style={({ pressed }) => ({
              flex: 1, backgroundColor: colors.card, borderWidth: 1, borderColor: colors.border,
              borderRadius: radius.lg, paddingVertical: 14, alignItems: "center", gap: 6, opacity: pressed ? 0.75 : 1,
            })}
          >
            <Text style={{ fontSize: 18, color: colors.brand }}>{a.icon}</Text>
            <Text style={{ color: colors.ink, fontSize: 11, fontFamily: fonts.bodyBold, textAlign: "center" }}>{t(a.labelKey)}</Text>
          </Pressable>
        ))}
      </View>

      {/* Investment goals */}
      {goals.length > 0 && (
        <Card>
          <Row>
            <Text style={{ fontSize: 13.5, fontFamily: fonts.bodyBold, color: colors.ink }}>{t("dashboard.yourInvestmentGoals")}</Text>
            <Pressable onPress={() => navigation.navigate("Goals")}>
              <Text style={{ fontSize: 12, color: colors.brand, fontFamily: fonts.bodyBold }}>{t("dashboard.viewAll")}</Text>
            </Pressable>
          </Row>
          <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
            {goals.slice(0, 6).map((g, i) => (
              <View key={i} style={{ paddingHorizontal: 12, paddingVertical: 7, borderRadius: radius.pill, backgroundColor: colors.pinkTint, borderWidth: 1, borderColor: colors.pinkSoft }}>
                <Text style={{ fontSize: 12.5, fontFamily: fonts.bodySemi, color: colors.brand }}>{g}</Text>
              </View>
            ))}
          </View>
        </Card>
      )}

      {/* Twin insights */}
      {insight && (
        <LinearGradient colors={[colors.brandDeep, colors.brand]} start={{ x: 0.1, y: 0 }} end={{ x: 0.9, y: 1 }} style={{ borderRadius: 16, padding: 18, gap: 10 }}>
          <Row>
            <Row style={{ justifyContent: "flex-start", gap: 8 }}>
              <Text style={{ color: colors.pink }}>✦</Text>
              <Text style={{ fontSize: 13.5, fontFamily: fonts.bodyBold, color: "#fff" }}>{t("dashboard.twinInsights")}</Text>
            </Row>
            <Pressable onPress={() => navigation.navigate("Insights")}>
              <Text style={{ fontSize: 12, color: colors.pink, fontFamily: fonts.bodyBold }}>{t("dashboard.viewAll")}</Text>
            </Pressable>
          </Row>
          <View style={{ padding: 12, backgroundColor: "rgba(255,255,255,.08)", borderWidth: 1, borderColor: "rgba(255,255,255,.12)", borderRadius: 12 }}>
            {"category" in insight ? (
              <>
                <Text style={{ fontSize: 12.5, fontFamily: fonts.bodyBold, color: "#fff", marginBottom: 4 }}>{t("dashboard.topCategoryTitle", { category: insight.category })}</Text>
                <Text style={{ fontSize: 11.5, color: "rgba(255,255,255,.8)", lineHeight: 16 }}>{t("dashboard.topCategoryBody", { amount: insight.amount })}</Text>
              </>
            ) : (
              <>
                <Text style={{ fontSize: 12.5, fontFamily: fonts.bodyBold, color: "#fff", marginBottom: 4 }}>{t("dashboard.unusualActivity")}</Text>
                <Text style={{ fontSize: 11.5, color: "rgba(255,255,255,.8)", lineHeight: 16 }}>{t("dashboard.anomalyBody", { count: insight.anomalyCount })}</Text>
              </>
            )}
          </View>
        </LinearGradient>
      )}

      {/* Recent transactions */}
      <H2>{t("dashboard.recent")}</H2>
      {history.length === 0 ? (
        <Muted>{t("dashboard.noTransactionsPeriod")}</Muted>
      ) : (
        <Card>
          {history.slice(0, 8).map((txn, i) => (
            <View key={txn.id || i}>
              {i > 0 && <Divider />}
              <Row>
                <View style={{ flex: 1 }}>
                  <Text style={{ color: colors.ink, fontFamily: fonts.bodySemi }}>{txn.beneficiary_name}</Text>
                  <Muted style={{ fontSize: 12 }}>
                    {txn.reference}{txn.step_up_required ? " · 🔐 Face" : ""}
                  </Muted>
                </View>
                <View style={{ alignItems: "flex-end" }}>
                  <Text style={{ color: colors.down, fontFamily: fonts.bodyBold }}>- {fmt(txn.amount)}</Text>
                  <Muted style={{ fontSize: 11, color: txn.status === "completed" ? colors.up : colors.muted }}>{txn.status}</Muted>
                </View>
              </Row>
            </View>
          ))}
        </Card>
      )}
    </AppShell>
  );
}
