import React from "react";
import { Text, View } from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { useTranslation } from "react-i18next";
import { AppShell } from "../components/AppShell";
import { Card, Muted } from "../components/ui";
import { colors, fonts } from "../theme";

const BONES = [
  { n: "Bone 1", titleKey: "ledger.bone1Title", descKey: "ledger.bone1Desc", glyph: "⛓" },
  { n: "Bone 2", titleKey: "ledger.bone2Title", descKey: "ledger.bone2Desc", glyph: "✍" },
  { n: "Bone 3", titleKey: "ledger.bone3Title", descKey: "ledger.bone3Desc", glyph: "▤" },
  { n: "Bone 4", titleKey: "ledger.bone4Title", descKey: "ledger.bone4Desc", glyph: "⚙" },
  { n: "Bone 5", titleKey: "ledger.bone5Title", descKey: "ledger.bone5Desc", glyph: "⛊" },
  { n: "Bone 6", titleKey: "ledger.bone6Title", descKey: "ledger.bone6Desc", glyph: "⌘" },
];

export default function LedgerScreen() {
  const { t } = useTranslation();
  return (
    <AppShell title={t("ledger.title")} mode="back">
      <LinearGradient colors={[colors.brand, colors.brandDeep]} start={{ x: 0.1, y: 0 }} end={{ x: 0.9, y: 1 }} style={{ borderRadius: 16, padding: 18 }}>
        <View style={{ flexDirection: "row", alignItems: "center", gap: 11 }}>
          <Text style={{ fontSize: 18 }}>⛓</Text>
          <View>
            <Text style={{ fontSize: 14, fontFamily: fonts.bodyBold, color: "#fff" }}>{t("ledger.chainVerified")}</Text>
            <Text style={{ fontSize: 11, color: "rgba(255,255,255,.8)" }}>{t("ledger.blocksInfo")}</Text>
          </View>
        </View>
      </LinearGradient>

      {BONES.map((b) => (
        <Card key={b.n}>
          <View style={{ flexDirection: "row", alignItems: "center", gap: 9, marginBottom: 2 }}>
            <Text style={{ color: colors.brand }}>{b.glyph}</Text>
            <Text style={{ fontSize: 10, fontFamily: fonts.mono, color: colors.grey }}>{b.n}</Text>
          </View>
          <Text style={{ fontSize: 13, fontFamily: fonts.bodyBold, color: colors.ink, marginBottom: 3 }}>{t(b.titleKey)}</Text>
          <Muted style={{ fontSize: 11.5, lineHeight: 16 }}>{t(b.descKey)}</Muted>
        </Card>
      ))}

      <Muted style={{ fontSize: 11, textAlign: "center" }}>
        {t("ledger.footer")}
      </Muted>
    </AppShell>
  );
}
