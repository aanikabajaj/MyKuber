import React, { useEffect, useRef } from "react";
import { Animated, Easing, Image, Text, View } from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { useTranslation } from "react-i18next";
import { colors } from "../theme";

export default function SplashScreen() {
  const { t } = useTranslation();
  const spin = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.loop(
      Animated.timing(spin, { toValue: 1, duration: 800, easing: Easing.linear, useNativeDriver: true })
    ).start();
  }, [spin]);

  const rotate = spin.interpolate({ inputRange: [0, 1], outputRange: ["0deg", "360deg"] });

  return (
    <LinearGradient
      colors={[colors.brandDeep, colors.brand, colors.brand2]}
      start={{ x: 0.1, y: 0 }}
      end={{ x: 0.9, y: 1 }}
      style={{ flex: 1, alignItems: "center", justifyContent: "center" }}
    >
      <View
        style={{
          width: 108, height: 108, borderRadius: 26, backgroundColor: "#fff",
          alignItems: "center", justifyContent: "center", padding: 16, marginBottom: 22,
          shadowColor: "#000", shadowOpacity: 0.3, shadowRadius: 50, shadowOffset: { width: 0, height: 20 },
        }}
      >
        <Image source={require("../../assets/kuber-logo-rect.png")} style={{ width: "100%", height: "100%" }} resizeMode="contain" />
      </View>
      <Text style={{ fontSize: 10.5, color: "rgba(255,255,255,.75)", letterSpacing: 0.3, marginBottom: 30 }}>
        {t("common.poweredBy")}
      </Text>
      <Animated.View
        style={{
          width: 26, height: 26, borderRadius: 13, borderWidth: 3,
          borderColor: "rgba(255,255,255,.35)", borderTopColor: "#fff",
          transform: [{ rotate }],
        }}
      />
    </LinearGradient>
  );
}
