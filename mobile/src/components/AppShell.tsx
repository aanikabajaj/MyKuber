import React from "react";
import { Pressable, ScrollView, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { DrawerActions, useNavigation } from "@react-navigation/native";
import { colors, fonts, radius } from "../theme";
import { useAuth } from "../context/AuthContext";

/** Derives an approximate protection score from the account's real security
 *  signals (verification + biometric/2FA enrolment) — not a fabricated number. */
export function securityScoreFor(user: any): number {
  if (!user) return 60;
  let score = 55;
  if (user.mobile_verified) score += 10;
  if (user.email_verified) score += 10;
  if (user.face_enabled) score += 12;
  if (user.totp_enabled) score += 8;
  if (user.sim_enrolled) score += 5;
  return Math.min(99, score);
}

export function AppShell({
  title,
  mode = "back",
  hideFab = false,
  scroll = true,
  noPadding = false,
  children,
  footer,
}: {
  title: string;
  mode?: "menu" | "back";
  hideFab?: boolean;
  scroll?: boolean;
  noPadding?: boolean;
  children: React.ReactNode;
  footer?: React.ReactNode;
}) {
  const navigation = useNavigation<any>();
  const { user } = useAuth();
  const score = securityScoreFor(user);

  const content = noPadding ? (
    <>{children}</>
  ) : (
    <View style={{ padding: 16, paddingBottom: 100, gap: 14 }}>{children}</View>
  );

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.page }} edges={["top", "bottom"]}>
      {/* Header */}
      <View
        style={{
          flexDirection: "row",
          alignItems: "center",
          gap: 10,
          paddingHorizontal: 14,
          paddingVertical: 13,
          borderBottomWidth: 1,
          borderBottomColor: colors.border,
          backgroundColor: "#fff",
        }}
      >
        {mode === "menu" ? (
          <Pressable
            onPress={() => navigation.dispatch(DrawerActions.openDrawer())}
            style={{
              width: 36, height: 36, borderRadius: 10, borderWidth: 1, borderColor: colors.border,
              backgroundColor: "#fff", alignItems: "center", justifyContent: "center", gap: 3.5,
            }}
          >
            <View style={{ width: 15, height: 2, backgroundColor: colors.brand, borderRadius: 2, marginBottom: 3 }} />
            <View style={{ width: 15, height: 2, backgroundColor: colors.brand, borderRadius: 2, marginBottom: 3 }} />
            <View style={{ width: 15, height: 2, backgroundColor: colors.brand, borderRadius: 2 }} />
          </Pressable>
        ) : (
          <Pressable
            onPress={() => navigation.navigate("Dashboard")}
            style={{
              width: 36, height: 36, borderRadius: 10, borderWidth: 1, borderColor: colors.border,
              backgroundColor: "#fff", alignItems: "center", justifyContent: "center",
            }}
          >
            <Text style={{ color: colors.brand, fontSize: 16 }}>←</Text>
          </Pressable>
        )}
        <Text
          style={{ flex: 1, color: colors.ink, fontSize: 15, fontFamily: fonts.heading }}
          numberOfLines={1}
        >
          {title}
        </Text>
        <View
          style={{
            flexDirection: "row", alignItems: "center", gap: 5, paddingHorizontal: 9, paddingVertical: 6,
            borderRadius: 9, borderWidth: 1, borderColor: colors.border,
          }}
        >
          <Text style={{ fontSize: 9, color: colors.muted, fontFamily: fonts.bodyBold }}>SEC</Text>
          <Text style={{ fontFamily: fonts.monoSemi, fontSize: 12, color: colors.brand }}>{score}</Text>
        </View>
      </View>

      {/* Content */}
      {scroll ? (
        <ScrollView style={{ flex: 1 }} showsVerticalScrollIndicator={false} keyboardShouldPersistTaps="handled">
          {content}
        </ScrollView>
      ) : (
        <View style={{ flex: 1 }}>{content}</View>
      )}

      {footer}

      {/* Floating AI Advisor button */}
      {!hideFab && (
        <Pressable
          onPress={() => navigation.navigate("AIChat")}
          style={{
            position: "absolute", right: 16, bottom: 20, width: 54, height: 54, borderRadius: 27,
            backgroundColor: colors.brand, alignItems: "center", justifyContent: "center",
            shadowColor: colors.brand, shadowOpacity: 0.4, shadowRadius: 12, shadowOffset: { width: 0, height: 6 }, elevation: 8,
          }}
        >
          <Text style={{ color: "#fff", fontSize: 20 }}>✦</Text>
        </Pressable>
      )}
    </SafeAreaView>
  );
}

export const radiusPill = radius.pill;
