import React, { useCallback, useState } from "react";
import { Text, View } from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import { useTranslation } from "react-i18next";
import { H2, Muted, Card, AppButton, Row, Divider, Badge } from "../components/ui";
import { AppShell } from "../components/AppShell";
import { colors, radius } from "../theme";
import { aiTxnApi, TransactionAnalysis, aiApiError } from "../lib/api";

const fmt = (n: number) =>
  "₹" + Number(n || 0).toLocaleString("en-IN", { minimumFractionDigits: 0 });

// ── Simple horizontal bar chart ────────────────────────────────────────────
function BarChart({ data }: { data: Record<string, number> }) {
  const entries = Object.entries(data)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8);
  const max = Math.max(...entries.map(([, v]) => v), 1);

  const BAR_COLORS = [
    colors.brand, colors.brand2, colors.up, colors.warn,
    colors.down, "#8a2d5f", "#b5628a", "#c07d16",
  ];

  return (
    <View style={{ gap: 10 }}>
      {entries.map(([cat, val], i) => (
        <View key={cat} style={{ gap: 4 }}>
          <Row>
            <Text style={{ color: colors.text, fontSize: 13, fontWeight: "600" }}>{cat}</Text>
            <Text style={{ color: colors.textMuted, fontSize: 13 }}>{fmt(val)}</Text>
          </Row>
          <View
            style={{
              height: 8,
              backgroundColor: colors.bgElevated,
              borderRadius: radius.pill,
              overflow: "hidden",
            }}
          >
            <View
              style={{
                height: 8,
                width: `${(val / max) * 100}%`,
                backgroundColor: BAR_COLORS[i % BAR_COLORS.length],
                borderRadius: radius.pill,
              }}
            />
          </View>
        </View>
      ))}
    </View>
  );
}

// ── Monthly cashflow mini-chart ───────────────────────────────────────────────
function CashflowChart({ data }: { data: TransactionAnalysis["monthly_cashflow"] }) {
  const { t } = useTranslation();
  const recent = [...data].slice(-4);
  const maxVal = Math.max(...recent.flatMap((m) => [m.total_debit, m.total_credit]), 1);

  return (
    <View style={{ gap: 8 }}>
      {recent.map((m) => (
        <View key={m.month} style={{ gap: 4 }}>
          <Muted style={{ fontSize: 11 }}>{m.month}</Muted>
          <Row style={{ gap: 8 }}>
            {/* Debit bar */}
            <View style={{ flex: 1 }}>
              <View
                style={{
                  height: 10,
                  backgroundColor: colors.bgElevated,
                  borderRadius: radius.pill,
                  overflow: "hidden",
                }}
              >
                <View
                  style={{
                    height: 10,
                    width: `${(m.total_debit / maxVal) * 100}%`,
                    backgroundColor: colors.high,
                    borderRadius: radius.pill,
                  }}
                />
              </View>
              <Text style={{ color: colors.high, fontSize: 10, marginTop: 1 }}>
                - {fmt(m.total_debit)}
              </Text>
            </View>

            {/* Credit bar */}
            <View style={{ flex: 1 }}>
              <View
                style={{
                  height: 10,
                  backgroundColor: colors.bgElevated,
                  borderRadius: radius.pill,
                  overflow: "hidden",
                }}
              >
                <View
                  style={{
                    height: 10,
                    width: `${(m.total_credit / maxVal) * 100}%`,
                    backgroundColor: colors.safe,
                    borderRadius: radius.pill,
                  }}
                />
              </View>
              <Text style={{ color: colors.safe, fontSize: 10, marginTop: 1 }}>
                + {fmt(m.total_credit)}
              </Text>
            </View>
          </Row>
        </View>
      ))}
      <Row style={{ marginTop: 4 }}>
        <Badge label={t("insights.debits")} color={colors.high} />
        <Badge label={t("insights.credits")} color={colors.safe} />
      </Row>
    </View>
  );
}

export default function InsightsScreen({ navigation }: any) {
  const { t } = useTranslation();
  const [data, setData] = useState<TransactionAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useFocusEffect(
    useCallback(() => {
      let active = true;
      setLoading(true);
      setError("");
      aiTxnApi
        .analyze()
        .then((r) => { if (active) setData(r); })
        .catch((e) => { if (active) setError(aiApiError(e)); })
        .finally(() => { if (active) setLoading(false); });
      return () => { active = false; };
    }, [])
  );

  if (loading) {
    return (
      <AppShell title={t("insights.title")} mode="back">
        <Muted>{t("insights.analysing")}</Muted>
      </AppShell>
    );
  }

  if (error) {
    return (
      <AppShell title={t("insights.title")} mode="back">
        <Card style={{ borderColor: colors.critical }}>
          <Text style={{ color: colors.critical }}>{error}</Text>
          <Muted style={{ fontSize: 12 }}>{t("insights.unavailable")}</Muted>
        </Card>
        <AppButton
          title={t("insights.askAI")}
          onPress={() => navigation.navigate("AIChat")}
        />
      </AppShell>
    );
  }

  if (!data) return null;

  const topCategory = Object.entries(data.category_breakdown).sort((a, b) => b[1] - a[1])[0];
  const totalSpend = Object.values(data.category_breakdown).reduce((s, v) => s + v, 0);

  return (
    <AppShell title={t("insights.title")} mode="back">
      {/* Summary cards */}
      <Row style={{ gap: 10 }}>
        <Card style={{ flex: 1, alignItems: "center" }}>
          <Muted style={{ fontSize: 11 }}>{t("insights.totalSpend")}</Muted>
          <Text style={{ color: colors.high, fontWeight: "800", fontSize: 18 }}>
            {fmt(totalSpend)}
          </Text>
        </Card>
        {topCategory && (
          <Card style={{ flex: 1, alignItems: "center" }}>
            <Muted style={{ fontSize: 11 }}>{t("insights.topCategory")}</Muted>
            <Text style={{ color: colors.text, fontWeight: "800", fontSize: 14 }}>
              {topCategory[0]}
            </Text>
            <Text style={{ color: colors.accent, fontSize: 12 }}>{fmt(topCategory[1])}</Text>
          </Card>
        )}
      </Row>

      {/* Category breakdown */}
      {Object.keys(data.category_breakdown).length > 0 && (
        <>
          <H2>{t("insights.categoryBreakdown")}</H2>
          <Card>
            <BarChart data={data.category_breakdown} />
          </Card>
        </>
      )}

      {/* Monthly cashflow */}
      {data.monthly_cashflow.length > 0 && (
        <>
          <H2>{t("insights.monthlyCashflow")}</H2>
          <Card>
            <CashflowChart data={data.monthly_cashflow} />
          </Card>
        </>
      )}

      {/* Anomaly spikes */}
      {data.anomaly_spikes.length > 0 && (
        <>
          <H2>{t("insights.unusualTransactions")}</H2>
          <Card style={{ borderColor: colors.accent }}>
            {data.anomaly_spikes.slice(0, 5).map((s, i) => (
              <View key={i}>
                {i > 0 && <Divider />}
                <Row>
                  <View style={{ flex: 1 }}>
                    <Text style={{ color: colors.text, fontWeight: "600", fontSize: 13 }}>
                      {s.beneficiary_name || t("insights.unknown")}
                    </Text>
                    <Muted style={{ fontSize: 11 }}>{s.date}</Muted>
                  </View>
                  <View style={{ alignItems: "flex-end" }}>
                    <Text style={{ color: colors.high, fontWeight: "700" }}>
                      {fmt(s.amount)}
                    </Text>
                    <Badge
                      label={`z=${s.z_score?.toFixed(1) ?? "?"}`}
                      color={colors.accent}
                    />
                  </View>
                </Row>
              </View>
            ))}
          </Card>
        </>
      )}

      {/* Recurring */}
      {data.recurring_transactions.length > 0 && (
        <>
          <H2>{t("insights.recurringTransactions")}</H2>
          <Card>
            {data.recurring_transactions.slice(0, 4).map((r: any, i) => (
              <View key={i}>
                {i > 0 && <Divider />}
                <Row>
                  <Text style={{ color: colors.text, fontSize: 13, fontWeight: "600" }}>
                    {r.beneficiary_name || r.name || t("insights.recurring")}
                  </Text>
                  <Text style={{ color: colors.textMuted, fontSize: 13 }}>
                    {r.frequency || ""} {r.amount ? fmt(r.amount) : ""}
                  </Text>
                </Row>
              </View>
            ))}
          </Card>
        </>
      )}

      {/* CTA */}
      <Card
        style={{
          borderColor: colors.primary + "55",
          backgroundColor: colors.primary + "0d",
          alignItems: "center",
          gap: 6,
        }}
      >
        <Text style={{ color: colors.primary, fontWeight: "700", fontSize: 15 }}>
          {t("insights.ctaTitle")}
        </Text>
        <Muted style={{ textAlign: "center", fontSize: 12 }}>
          {t("insights.ctaDesc")}
        </Muted>
        <AppButton
          title={t("insights.openAiChat")}
          onPress={() => navigation.navigate("AIChat")}
        />
      </Card>
    </AppShell>
  );
}
