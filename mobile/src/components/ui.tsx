import React, { useEffect, useRef } from "react";
import {
  ActivityIndicator,
  Animated,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TextInputProps,
  View,
  ViewStyle,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { LinearGradient } from "expo-linear-gradient";
import { useTranslation } from "react-i18next";
import { colors, fonts, radius, spacing } from "../theme";

export function Screen({
  children,
  scroll = true,
  padded = true,
}: {
  children: React.ReactNode;
  scroll?: boolean;
  padded?: boolean;
}) {
  const opacity = useRef(new Animated.Value(0)).current;
  const translateY = useRef(new Animated.Value(14)).current;
  useEffect(() => {
    Animated.parallel([
      Animated.timing(opacity, { toValue: 1, duration: 360, useNativeDriver: true }),
      Animated.timing(translateY, { toValue: 0, duration: 360, useNativeDriver: true }),
    ]).start();
  }, [opacity, translateY]);

  const inner = (
    <Animated.View
      style={{ padding: padded ? spacing.lg : 0, gap: spacing.md, flexGrow: 1, opacity, transform: [{ translateY }] }}
    >
      {children}
    </Animated.View>
  );
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.page }} edges={["top", "bottom"]}>
      {scroll ? (
        <ScrollView keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator={false}>
          {inner}
        </ScrollView>
      ) : (
        inner
      )}
    </SafeAreaView>
  );
}

export function H1({ children, style }: { children: React.ReactNode; style?: any }) {
  return <Text style={[s.h1, style]}>{children}</Text>;
}
export function H2({ children, style }: { children: React.ReactNode; style?: any }) {
  return <Text style={[s.h2, style]}>{children}</Text>;
}
export function Muted({ children, style }: { children: React.ReactNode; style?: any }) {
  return <Text style={[s.muted, style]}>{children}</Text>;
}
export function Mono({ children, style }: { children: React.ReactNode; style?: any }) {
  return <Text style={[s.mono, style]}>{children}</Text>;
}

export function Card({ children, style }: { children: React.ReactNode; style?: ViewStyle }) {
  return <View style={[s.card, style]}>{children}</View>;
}

/** Gradient-free brand hero surface — pass colors via style.backgroundColor,
 *  or use GradientCard below for the two-tone brand gradient look. */
export function Divider() {
  return <View style={s.divider} />;
}

export function Badge({ label, color = colors.brand }: { label: string; color?: string }) {
  return (
    <View style={[s.badge, { backgroundColor: color + "1a", borderColor: color + "55" }]}>
      <Text style={{ color, fontFamily: fonts.bodyBold, fontSize: 12 }}>{label}</Text>
    </View>
  );
}

export function AppButton({
  title,
  onPress,
  variant = "primary",
  loading,
  disabled,
  icon,
}: {
  title: string;
  onPress?: () => void;
  variant?: "primary" | "outline" | "ghost" | "danger" | "accent";
  loading?: boolean;
  disabled?: boolean;
  icon?: React.ReactNode;
}) {
  const bg =
    variant === "primary" ? colors.brand
    : variant === "danger" ? colors.down
    : variant === "accent" ? colors.pink
    : variant === "outline" ? colors.card
    : "transparent";
  const border = variant === "outline" ? colors.border : "transparent";
  const fg =
    variant === "outline" || variant === "ghost" ? colors.ink
    : variant === "accent" ? colors.brandDeep
    : "#fff";
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled || loading}
      style={({ pressed }) => [
        s.btn,
        { backgroundColor: bg, borderColor: border, borderWidth: variant === "outline" ? 1.5 : 0, opacity: disabled ? 0.5 : pressed ? 0.85 : 1 },
      ]}
    >
      {loading ? (
        <ActivityIndicator color={fg} />
      ) : (
        <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
          {icon}
          <Text style={{ color: fg, fontFamily: fonts.bodyBold, fontSize: 15 }}>{title}</Text>
        </View>
      )}
    </Pressable>
  );
}

export function TextField({
  label,
  style,
  ...props
}: TextInputProps & { label?: string }) {
  return (
    <View style={{ gap: 6 }}>
      {label ? <Text style={s.label}>{label}</Text> : null}
      <TextInput
        placeholderTextColor={colors.grey}
        style={[s.input, style]}
        {...props}
      />
    </View>
  );
}

export function Row({ children, style }: { children: React.ReactNode; style?: ViewStyle }) {
  return <View style={[{ flexDirection: "row", alignItems: "center", justifyContent: "space-between" }, style]}>{children}</View>;
}

/** A pill-shaped progress bar with the brand gradient fill, used for goals / holdings progress. */
export function ProgressBar({ pct, style }: { pct: number; style?: ViewStyle }) {
  const w = Math.max(0, Math.min(100, pct));
  return (
    <View style={[s.progressTrack, style]}>
      <LinearGradient
        colors={[colors.brand, colors.brand2]}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 0 }}
        style={{ height: "100%", width: `${w}%`, borderRadius: 5 }}
      />
    </View>
  );
}

/** Sign in / Register tab switcher shown atop the auth flow. */
export function AuthTabs({
  active,
  onSignin,
  onRegister,
}: {
  active: "signin" | "register";
  onSignin: () => void;
  onRegister: () => void;
}) {
  const { t } = useTranslation();
  return (
    <View style={{ flexDirection: "row", padding: 4, backgroundColor: colors.line, borderRadius: 12, gap: 3, marginBottom: 22 }}>
      <Pressable
        onPress={onSignin}
        style={{ flex: 1, paddingVertical: 9, borderRadius: 9, backgroundColor: active === "signin" ? colors.brand : "transparent", alignItems: "center" }}
      >
        <Text style={{ color: active === "signin" ? "#fff" : colors.muted, fontFamily: fonts.bodyBold, fontSize: 13 }}>{t("common.signIn")}</Text>
      </Pressable>
      <Pressable
        onPress={onRegister}
        style={{ flex: 1, paddingVertical: 9, borderRadius: 9, backgroundColor: active === "register" ? colors.brand : "transparent", alignItems: "center" }}
      >
        <Text style={{ color: active === "register" ? "#fff" : colors.muted, fontFamily: fonts.bodyBold, fontSize: 13 }}>{t("common.register")}</Text>
      </Pressable>
    </View>
  );
}

/** 6-box OTP input row matching the design's verification screens. */
export function OtpBoxes({
  value,
  onChange,
}: {
  value: string[];
  onChange: (i: number, v: string) => void;
}) {
  const refs = useRef<(TextInput | null)[]>([]);
  return (
    <View style={{ flexDirection: "row", gap: 8, marginBottom: 4 }}>
      {value.map((v, i) => (
        <TextInput
          key={i}
          ref={(r) => { refs.current[i] = r; }}
          value={v}
          maxLength={1}
          keyboardType="number-pad"
          onChangeText={(t) => {
            const digit = t.replace(/[^0-9]/g, "").slice(-1);
            onChange(i, digit);
            if (digit && i < value.length - 1) refs.current[i + 1]?.focus();
          }}
          style={{
            width: 44, aspectRatio: 1, textAlign: "center", fontSize: 18, fontFamily: fonts.mono,
            borderWidth: 1.5, borderColor: colors.border, borderRadius: 11, backgroundColor: "#fbf7f9", color: colors.ink,
          }}
        />
      ))}
    </View>
  );
}

/** Small rounded tag used for asset-class / risk-tier labels. */
export function Tag({ label, bg, color }: { label: string; bg: string; color: string }) {
  return (
    <View style={{ paddingHorizontal: 7, paddingVertical: 3, borderRadius: 5, backgroundColor: bg }}>
      <Text style={{ fontSize: 9, fontFamily: fonts.bodyBold, color }}>{label}</Text>
    </View>
  );
}

const s = StyleSheet.create({
  h1: { color: colors.ink, fontSize: 26, fontFamily: fonts.headingXBold },
  h2: { color: colors.ink, fontSize: 18, fontFamily: fonts.heading },
  muted: { color: colors.muted, fontSize: 14, fontFamily: fonts.body },
  mono: { color: colors.ink, fontFamily: fonts.mono },
  card: { backgroundColor: colors.card, borderColor: colors.border, borderWidth: 1, borderRadius: radius.lg, padding: spacing.md, gap: spacing.sm },
  divider: { height: 1, backgroundColor: colors.line, marginVertical: spacing.sm },
  badge: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: radius.pill, borderWidth: 1, alignSelf: "flex-start" },
  btn: { height: 52, borderRadius: radius.md, alignItems: "center", justifyContent: "center", paddingHorizontal: 18 },
  label: { color: colors.ink, fontSize: 12, fontFamily: fonts.bodyBold },
  input: { height: 50, borderWidth: 1.5, borderColor: colors.border, borderRadius: radius.md, paddingHorizontal: 14, color: colors.ink, backgroundColor: "#fbf7f9", fontSize: 15, fontFamily: fonts.body },
  progressTrack: { height: 7, borderRadius: 5, backgroundColor: "#f0e8ec", overflow: "hidden" },
  progressFill: { height: "100%", backgroundColor: colors.brand, borderRadius: 5 },
});
