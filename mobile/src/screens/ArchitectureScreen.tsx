import React from "react";
import { Text, View } from "react-native";
import { useTranslation } from "react-i18next";
import { AppShell } from "../components/AppShell";
import { Card } from "../components/ui";
import { colors, fonts } from "../theme";

const FLOW = [
  { labelKey: "architecture.flowCustomer", subKey: "architecture.flowCustomerSub", color: colors.brand },
  { labelKey: "architecture.flowWealthTwin", subKey: "architecture.flowWealthTwinSub", color: colors.brand2 },
  { labelKey: "architecture.flowProtection", subKey: "architecture.flowProtectionSub", color: "#b5628a" },
  { labelKey: "architecture.flowDecision", subKey: "architecture.flowDecisionSub", color: "#7a0a3c" },
  { labelKey: "architecture.flowLedgerAudit", subKey: "architecture.flowLedgerAuditSub", color: "#8a2d5f" },
];

const MODULES = [
  { nameKey: "architecture.modFrontend", color: colors.brand, glyph: "■", pointKeys: ["architecture.modFrontendP1", "architecture.modFrontendP2", "architecture.modFrontendP3"] },
  { nameKey: "architecture.modBackend", color: "#7a0a3c", glyph: "⇄", pointKeys: ["architecture.modBackendP1", "architecture.modBackendP2", "architecture.modBackendP3"] },
  { nameKey: "architecture.modAiTwin", color: colors.brand2, glyph: "✧", pointKeys: ["architecture.modAiTwinP1", "architecture.modAiTwinP2", "architecture.modAiTwinP3"] },
  { nameKey: "architecture.modSecurity", color: "#b5628a", glyph: "⛊", pointKeys: ["architecture.modSecurityP1", "architecture.modSecurityP2", "architecture.modSecurityP3"] },
  { nameKey: "architecture.modBlockchain", color: "#8a2d5f", glyph: "⛓", pointKeys: ["architecture.modBlockchainP1", "architecture.modBlockchainP2", "architecture.modBlockchainP3"] },
];

export default function ArchitectureScreen() {
  const { t } = useTranslation();
  return (
    <AppShell title={t("architecture.title")} mode="back">
      {FLOW.map((f, i) => (
        <View key={f.labelKey}>
          <View style={{ padding: 14, borderWidth: 1.5, borderColor: colors.line, borderLeftWidth: 3, borderLeftColor: f.color, borderRadius: 12, backgroundColor: "#fbf7f9" }}>
            <Text style={{ fontSize: 13, fontFamily: fonts.bodyBold, color: colors.ink }}>{t(f.labelKey)}</Text>
            <Text style={{ fontSize: 11.5, color: colors.grey, marginTop: 2 }}>{t(f.subKey)}</Text>
          </View>
          {i < FLOW.length - 1 && (
            <Text style={{ textAlign: "center", color: colors.pink, fontSize: 16, paddingVertical: 2 }}>↓</Text>
          )}
        </View>
      ))}

      {MODULES.map((m) => (
        <Card key={m.nameKey} style={{ borderTopWidth: 3, borderTopColor: m.color }}>
          <View style={{ flexDirection: "row", alignItems: "center", gap: 10, marginBottom: 3 }}>
            <View style={{ width: 32, height: 32, borderRadius: 9, backgroundColor: m.color, alignItems: "center", justifyContent: "center" }}>
              <Text style={{ color: "#fff", fontSize: 14 }}>{m.glyph}</Text>
            </View>
            <Text style={{ fontSize: 14, fontFamily: fonts.bodyBold, color: colors.ink }}>{t(m.nameKey)}</Text>
          </View>
          {m.pointKeys.map((pk, i) => (
            <View key={i} style={{ flexDirection: "row", gap: 6, marginBottom: 4 }}>
              <Text style={{ color: m.color, fontSize: 11.5 }}>·</Text>
              <Text style={{ flex: 1, fontSize: 11.5, color: "#5a4650", lineHeight: 16 }}>{t(pk)}</Text>
            </View>
          ))}
        </Card>
      ))}
    </AppShell>
  );
}
