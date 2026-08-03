import React, { useState } from "react";
import { Text, View } from "react-native";
import Slider from "@react-native-community/slider";
import Svg, { Defs, LinearGradient as SvgGradient, Polygon, Polyline, Stop } from "react-native-svg";
import { useTranslation } from "react-i18next";
import { AppShell } from "../components/AppShell";
import { Card, Muted } from "../components/ui";
import { colors, fonts } from "../theme";

const EXISTING_CORPUS = 2260000;

function buildLine(vals: number[], w: number, h: number, pad: number) {
  const min = Math.min(...vals), max = Math.max(...vals);
  const dx = (w - pad * 2) / (vals.length - 1 || 1);
  const pts = vals.map((v, i) => [pad + dx * i, h - pad - ((v - min) / ((max - min) || 1)) * (h - pad * 2)]);
  const line = pts.map((p) => `${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(" ");
  const area = `${pad},${h - pad} ${line} ${(pad + dx * (vals.length - 1)).toFixed(1)},${h - pad}`;
  return { line, area };
}

const inr = (n: number) => "₹" + Math.round(n).toLocaleString("en-IN");
const inrShort = (n: number) => {
  if (n >= 10000000) return "₹" + (n / 10000000).toFixed(2).replace(/\.00$/, "") + " Cr";
  if (n >= 100000) return "₹" + (n / 100000).toFixed(2).replace(/\.00$/, "") + " L";
  if (n >= 1000) return "₹" + (n / 1000).toFixed(0) + "K";
  return "₹" + n;
};

export default function SimulatorScreen() {
  const { t } = useTranslation();
  const [sip, setSip] = useState(15000);
  const [years, setYears] = useState(15);

  const rM = 0.11 / 12, nM = years * 12, P = sip;
  const fvSip = nM ? P * ((Math.pow(1 + rM, nM) - 1) / rM) * (1 + rM) : 0;
  const corpus = fvSip + EXISTING_CORPUS * Math.pow(1.11, years);
  const invested = P * nM + EXISTING_CORPUS;
  const gains = corpus - invested;

  const series: number[] = [];
  for (let y = 0; y <= years; y++) {
    const nn = y * 12;
    const fv = nn ? P * ((Math.pow(1 + rM, nn) - 1) / rM) * (1 + rM) : 0;
    series.push(fv + EXISTING_CORPUS * Math.pow(1.11, y));
  }
  const chart = buildLine(series.length > 1 ? series : [0, 1], 340, 130, 8);

  return (
    <AppShell title={t("simulator.title")} mode="back">
      <Card>
        <View style={{ flexDirection: "row", justifyContent: "space-between", marginBottom: 2 }}>
          <Text style={{ fontSize: 13, fontFamily: fonts.bodyBold, color: colors.ink }}>{t("simulator.monthlySip")}</Text>
          <Text style={{ fontFamily: fonts.mono, fontSize: 13.5, fontWeight: "600", color: colors.brand }}>{inr(sip)}</Text>
        </View>
        <Slider minimumValue={2000} maximumValue={60000} step={1000} value={sip} onValueChange={setSip}
          minimumTrackTintColor={colors.brand} maximumTrackTintColor={colors.border} thumbTintColor={colors.brand} style={{ marginBottom: 16 }} />
        <View style={{ flexDirection: "row", justifyContent: "space-between", marginBottom: 2 }}>
          <Text style={{ fontSize: 13, fontFamily: fonts.bodyBold, color: colors.ink }}>{t("simulator.horizon")}</Text>
          <Text style={{ fontFamily: fonts.mono, fontSize: 13.5, fontWeight: "600", color: colors.brand }}>{years} {t("simulator.yrs")}</Text>
        </View>
        <Slider minimumValue={3} maximumValue={35} step={1} value={years} onValueChange={setYears}
          minimumTrackTintColor={colors.brand} maximumTrackTintColor={colors.border} thumbTintColor={colors.brand} />
      </Card>

      <View style={{ flexDirection: "row", gap: 10 }}>
        <View style={{ flex: 1, padding: 14, borderRadius: 13, backgroundColor: colors.brand }}>
          <Text style={{ fontSize: 11, color: "rgba(255,255,255,.75)" }}>{t("simulator.corpus")}</Text>
          <Text style={{ fontFamily: fonts.mono, fontSize: 18, fontWeight: "600", color: colors.pink }}>{inrShort(corpus)}</Text>
        </View>
        <View style={{ flex: 1, padding: 14, borderRadius: 13, borderWidth: 1.5, borderColor: colors.border }}>
          <Muted style={{ fontSize: 11 }}>{t("simulator.gains")}</Muted>
          <Text style={{ fontFamily: fonts.mono, fontSize: 18, fontWeight: "600", color: colors.up }}>{inrShort(gains)}</Text>
        </View>
      </View>

      <Card>
        <Svg viewBox="0 0 340 130" style={{ width: "100%", height: 130 }}>
          <Defs>
            <SvgGradient id="simg" x1="0" y1="0" x2="0" y2="1">
              <Stop offset="0%" stopColor={colors.brand} stopOpacity={0.28} />
              <Stop offset="100%" stopColor={colors.brand} stopOpacity={0} />
            </SvgGradient>
          </Defs>
          <Polygon points={chart.area} fill="url(#simg)" />
          <Polyline points={chart.line} fill="none" stroke={colors.brand} strokeWidth={2.5} strokeLinejoin="round" strokeLinecap="round" />
        </Svg>
      </Card>

      <Muted style={{ fontSize: 11, textAlign: "center" }}>
        {t("simulator.footer", { amount: (EXISTING_CORPUS / 100000).toFixed(1) })}
      </Muted>
    </AppShell>
  );
}
