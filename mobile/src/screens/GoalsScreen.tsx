import React, { useEffect, useState } from "react";
import { Pressable, Text, View } from "react-native";
import { useTranslation } from "react-i18next";
import { AppShell } from "../components/AppShell";
import { Card, H2, Muted, AppButton, TextField, Divider } from "../components/ui";
import { colors, fonts, radius } from "../theme";
import { aiProfileApi, FinancialProfile, aiApiError } from "../lib/api";

const RISK_OPTIONS = [
  { value: "conservative", labelKey: "goals.riskConservative", icon: "🛡️", descKey: "goals.riskConservativeDesc" },
  { value: "moderate", labelKey: "goals.riskModerate", icon: "⚖️", descKey: "goals.riskModerateDesc" },
  { value: "aggressive", labelKey: "goals.riskAggressive", icon: "🚀", descKey: "goals.riskAggressiveDesc" },
];

const GOAL_OPTIONS = [
  { value: "Retirement", labelKey: "goals.goalRetirement" }, { value: "Home Purchase", labelKey: "goals.goalHome" },
  { value: "Child Education", labelKey: "goals.goalChildEducation" }, { value: "Wealth Creation", labelKey: "goals.goalWealthCreation" },
  { value: "Emergency Fund", labelKey: "goals.goalEmergencyFund" }, { value: "Tax Saving", labelKey: "goals.goalTaxSaving" },
  { value: "Travel", labelKey: "goals.goalTravel" }, { value: "Business", labelKey: "goals.goalBusiness" },
];

const ASSET_OPTIONS = [
  { value: "Equity", labelKey: "goals.assetEquity" }, { value: "Debt", labelKey: "goals.assetDebt" },
  { value: "Gold", labelKey: "goals.assetGold" }, { value: "Real Estate", labelKey: "goals.assetRealEstate" },
  { value: "Mutual Funds", labelKey: "goals.assetMutualFunds" }, { value: "Fixed Deposits", labelKey: "goals.assetFixedDeposits" },
  { value: "PPF", labelKey: "goals.assetPPF" }, { value: "NPS", labelKey: "goals.assetNPS" },
];

function ChipSelect({ options, selected, onToggle }: { options: { value: string; labelKey: string }[]; selected: string[]; onToggle: (v: string) => void }) {
  const { t } = useTranslation();
  return (
    <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
      {options.map((o) => {
        const active = selected.includes(o.value);
        return (
          <Pressable
            key={o.value}
            onPress={() => onToggle(o.value)}
            style={{
              paddingHorizontal: 14, paddingVertical: 7, borderRadius: radius.pill, borderWidth: 1.5,
              borderColor: active ? colors.brand : colors.border, backgroundColor: active ? colors.pinkTint : "transparent",
            }}
          >
            <Text style={{ color: active ? colors.brand : colors.muted, fontSize: 13, fontFamily: active ? fonts.bodyBold : fonts.body }}>{t(o.labelKey)}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

export default function GoalsScreen() {
  const { t } = useTranslation();
  const [profile, setProfile] = useState<FinancialProfile>({
    risk_profile: null, investment_goals: [], holdings: [], sip_details: [],
    investment_horizon_years: null, preferred_asset_classes: [],
  });
  const [horizon, setHorizon] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const p = await aiProfileApi.get();
        setProfile(p);
        setHorizon(p.investment_horizon_years ? String(p.investment_horizon_years) : "");
      } catch (e) { setError(aiApiError(e)); }
      finally { setLoading(false); }
    })();
  }, []);

  function toggleGoal(g: string) {
    setProfile((p) => ({ ...p, investment_goals: p.investment_goals.includes(g) ? p.investment_goals.filter((x) => x !== g) : [...p.investment_goals, g] }));
  }
  function toggleAsset(a: string) {
    setProfile((p) => ({ ...p, preferred_asset_classes: p.preferred_asset_classes.includes(a) ? p.preferred_asset_classes.filter((x) => x !== a) : [...p.preferred_asset_classes, a] }));
  }

  async function save() {
    setSaving(true); setMsg(""); setError("");
    try {
      const updated = await aiProfileApi.update({
        risk_profile: profile.risk_profile,
        investment_goals: profile.investment_goals,
        preferred_asset_classes: profile.preferred_asset_classes,
        investment_horizon_years: horizon ? Number(horizon) : undefined,
      });
      setProfile(updated);
      setMsg(t("goals.savedMsg"));
    } catch (e) { setError(aiApiError(e)); }
    finally { setSaving(false); }
  }

  if (loading) {
    return (
      <AppShell title={t("goals.title")} mode="back">
        <Muted>{t("goals.loadingProfile")}</Muted>
      </AppShell>
    );
  }

  return (
    <AppShell title={t("goals.title")} mode="back">
      {error ? (
        <Card style={{ borderColor: colors.down }}>
          <Text style={{ color: colors.down }}>{error}</Text>
          <Muted style={{ fontSize: 12 }}>{t("goals.aiOffline")}</Muted>
        </Card>
      ) : null}

      <Card>
        <Text style={{ fontSize: 13.5, fontFamily: fonts.bodyBold, color: colors.ink }}>{t("goals.riskAppetite")}</Text>
        <View style={{ gap: 8 }}>
          {RISK_OPTIONS.map((r) => {
            const active = profile.risk_profile === r.value;
            return (
              <Pressable
                key={r.value}
                onPress={() => setProfile((p) => ({ ...p, risk_profile: r.value }))}
                style={{
                  backgroundColor: active ? colors.pinkTint : "#fff", borderWidth: 1.5, borderColor: active ? colors.brand : colors.border,
                  borderRadius: 12, padding: 14, flexDirection: "row", alignItems: "center", gap: 12,
                }}
              >
                <Text style={{ fontSize: 22 }}>{r.icon}</Text>
                <View style={{ flex: 1 }}>
                  <Text style={{ color: active ? colors.brand : colors.ink, fontFamily: fonts.bodyBold, fontSize: 14.5 }}>{t(r.labelKey)}</Text>
                  <Muted style={{ fontSize: 12 }}>{t(r.descKey)}</Muted>
                </View>
                <View style={{ width: 20, height: 20, borderRadius: 10, borderWidth: 2, borderColor: active ? colors.brand : colors.border, backgroundColor: active ? colors.brand : "transparent" }} />
              </Pressable>
            );
          })}
        </View>
      </Card>

      <Card>
        <TextField label={t("goals.horizonLabel")} keyboardType="number-pad" maxLength={2} value={horizon} onChangeText={setHorizon} placeholder={t("goals.horizonPlaceholder")} />
        <Muted style={{ fontSize: 12 }}>{t("goals.horizonHint")}</Muted>
      </Card>

      <Card>
        <Text style={{ fontSize: 13.5, fontFamily: fonts.bodyBold, color: colors.ink }}>{t("goals.investmentGoalsLabel")}</Text>
        <ChipSelect options={GOAL_OPTIONS} selected={profile.investment_goals} onToggle={toggleGoal} />
      </Card>

      <Card>
        <Text style={{ fontSize: 13.5, fontFamily: fonts.bodyBold, color: colors.ink }}>{t("goals.preferredAssetClasses")}</Text>
        <ChipSelect options={ASSET_OPTIONS} selected={profile.preferred_asset_classes} onToggle={toggleAsset} />
      </Card>

      {profile.holdings && profile.holdings.length > 0 && (
        <Card>
          <Text style={{ fontSize: 13.5, fontFamily: fonts.bodyBold, color: colors.ink, marginBottom: 4 }}>{t("goals.holdingsLabel")}</Text>
          {profile.holdings.map((h, i) => (
            <View key={i}>
              {i > 0 && <Divider />}
              <Text style={{ color: colors.ink, paddingVertical: 4, fontFamily: fonts.body, fontSize: 13 }}>
                {typeof h === "string" ? h : JSON.stringify(h)}
              </Text>
            </View>
          ))}
        </Card>
      )}

      {msg ? (
        <Card style={{ borderColor: colors.up }}>
          <Text style={{ color: colors.up, fontSize: 13 }}>{msg}</Text>
        </Card>
      ) : null}

      <AppButton title={t("goals.saveProfile")} onPress={save} loading={saving} />
      <Muted style={{ fontSize: 11, textAlign: "center" }}>{t("goals.footerNote")}</Muted>
    </AppShell>
  );
}
