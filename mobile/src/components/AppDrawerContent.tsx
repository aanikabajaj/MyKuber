import React from "react";
import { Image, Pressable, Text, View } from "react-native";
import { DrawerContentScrollView } from "@react-navigation/drawer";
import { LinearGradient } from "expo-linear-gradient";
import { useTranslation } from "react-i18next";
import { colors, fonts } from "../theme";
import { useAuth } from "../context/AuthContext";

interface NavItem {
  key: string;
  labelKey: string;
  glyph: string;
  module?: string;
}
interface NavGroup {
  headKey: string;
  items: NavItem[];
}

const NAV_GROUPS: NavGroup[] = [
  { headKey: "nav.overview", items: [{ key: "Dashboard", labelKey: "nav.dashboard", glyph: "■" }] },
  {
    headKey: "nav.aiTwin",
    items: [
      { key: "AIChat", labelKey: "nav.aiAdvisor", glyph: "✧", module: "AI" },
      { key: "Simulator", labelKey: "nav.scenarioSimulator", glyph: "≈", module: "AI" },
    ],
  },
  {
    headKey: "nav.money",
    items: [
      { key: "Goals", labelKey: "nav.goalsPortfolio", glyph: "◎" },
      { key: "Transfer", labelKey: "nav.newTransaction", glyph: "⇄" },
    ],
  },
  {
    headKey: "nav.protection",
    items: [
      { key: "Protection", labelKey: "nav.wealthProtection", glyph: "⛊", module: "SEC" },
      { key: "Ledger", labelKey: "nav.blockchainLedger", glyph: "⛓", module: "CHAIN" },
    ],
  },
  { headKey: "nav.system", items: [{ key: "Architecture", labelKey: "nav.architecture", glyph: "⌘" }] },
];

export default function AppDrawerContent(props: any) {
  const { t } = useTranslation();
  const { user, logout } = useAuth();
  const activeRoute = props.state.routeNames[props.state.index];
  const initials = ((user?.first_name || user?.username || "U") as string)
    .split(" ")
    .map((w) => w[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  return (
    <LinearGradient colors={[colors.brandDeep, colors.brand]} style={{ flex: 1 }}>
      <DrawerContentScrollView {...props} contentContainerStyle={{ flexGrow: 1 }} style={{ backgroundColor: "transparent" }}>
        <View
          style={{
            flexDirection: "row", alignItems: "center", justifyContent: "space-between",
            paddingHorizontal: 16, paddingVertical: 14, borderBottomWidth: 1, borderBottomColor: "rgba(255,255,255,.12)",
          }}
        >
          <View style={{ flexDirection: "row", alignItems: "center", gap: 10 }}>
            <Image
              source={require("../../assets/kuber-logo-rect.png")}
              style={{ height: 30, width: 90, borderRadius: 7 }}
              resizeMode="contain"
            />
          </View>
          <Pressable
            onPress={() => props.navigation.closeDrawer()}
            style={{
              width: 32, height: 32, borderRadius: 9, borderWidth: 1, borderColor: "rgba(255,255,255,.18)",
              alignItems: "center", justifyContent: "center",
            }}
          >
            <Text style={{ color: "#fff", fontSize: 15 }}>✕</Text>
          </Pressable>
        </View>
        <Text style={{ fontSize: 9, color: colors.pink, paddingHorizontal: 16, paddingTop: 8, paddingBottom: 4 }}>
          {t("common.poweredBy")}
        </Text>

        <View style={{ flex: 1, paddingHorizontal: 12, paddingTop: 10 }}>
          {NAV_GROUPS.map((grp) => (
            <View key={grp.headKey} style={{ marginBottom: 14 }}>
              <Text
                style={{
                  fontSize: 10, fontFamily: fonts.bodyBold, letterSpacing: 0.8, color: "rgba(255,255,255,.4)",
                  textTransform: "uppercase", paddingHorizontal: 10, paddingBottom: 7,
                }}
              >
                {t(grp.headKey)}
              </Text>
              {grp.items.map((n) => {
                const active = activeRoute === n.key;
                return (
                  <Pressable
                    key={n.key}
                    onPress={() => props.navigation.navigate(n.key)}
                    style={{
                      flexDirection: "row", alignItems: "center", gap: 11, paddingVertical: 11, paddingHorizontal: 11,
                      borderRadius: 11, backgroundColor: active ? "rgba(255,182,193,.16)" : "transparent",
                      borderLeftWidth: 3, borderLeftColor: active ? colors.pink : "transparent",
                    }}
                  >
                    <Text style={{ width: 20, textAlign: "center", fontSize: 14, color: active ? "#fff" : "rgba(255,255,255,.72)" }}>
                      {n.glyph}
                    </Text>
                    <Text
                      style={{
                        flex: 1, fontSize: 13.5, fontFamily: active ? fonts.bodyBold : fonts.bodySemi,
                        color: active ? "#fff" : "rgba(255,255,255,.72)",
                      }}
                    >
                      {t(n.labelKey)}
                    </Text>
                    {n.module ? (
                      <View style={{ paddingHorizontal: 6, paddingVertical: 2, borderRadius: 5, backgroundColor: "rgba(255,182,193,.2)" }}>
                        <Text style={{ fontSize: 8, fontFamily: fonts.bodyBold, letterSpacing: 0.4, color: colors.pink }}>{n.module}</Text>
                      </View>
                    ) : null}
                  </Pressable>
                );
              })}
            </View>
          ))}
        </View>

        <View style={{ padding: 12, borderTopWidth: 1, borderTopColor: "rgba(255,255,255,.12)" }}>
          <View
            style={{
              flexDirection: "row", alignItems: "center", gap: 10, padding: 11, borderRadius: 12,
              backgroundColor: "rgba(255,255,255,.06)",
            }}
          >
            <View
              style={{
                width: 34, height: 34, borderRadius: 9, backgroundColor: colors.pink,
                alignItems: "center", justifyContent: "center",
              }}
            >
              <Text style={{ color: colors.brandDeep, fontFamily: fonts.bodyBold, fontSize: 13 }}>{initials}</Text>
            </View>
            <View style={{ flex: 1, minWidth: 0 }}>
              <Text numberOfLines={1} style={{ fontSize: 13, fontFamily: fonts.bodyBold, color: "#fff" }}>
                {user?.first_name || user?.username}
              </Text>
              <Text style={{ fontSize: 10.5, color: colors.pink }}>{t("nav.priorityWealth")}</Text>
            </View>
            <Pressable onPress={logout} hitSlop={8}>
              <Text style={{ color: "rgba(255,255,255,.7)", fontSize: 15 }}>⏻</Text>
            </Pressable>
          </View>
        </View>
      </DrawerContentScrollView>
    </LinearGradient>
  );
}
