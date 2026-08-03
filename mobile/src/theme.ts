/** My Kuber mobile design tokens — light banking/wealth theme, powered by Punjab & Sind Bank. */
export const colors = {
  brand: "#970747",
  brandDeep: "#6d0834",
  brand2: "#c01463",
  pink: "#FFB6C1",
  pinkSoft: "#ffe4ea",
  pinkTint: "#fff4f7",

  page: "#faf6f7",
  card: "#ffffff",
  ink: "#2b1a21",
  muted: "#8b7a81",
  grey: "#b5b5b5",
  border: "#ece0e5",
  line: "#f4edf0",

  up: "#1f9d6b",
  down: "#c0453f",
  warn: "#c07d16",
  warnBg: "#fdf3e5",
  warnBorder: "#f2d9a8",
  upBg: "#e7f7f0",
  downBg: "#fbeceb",

  // Legacy aliases used by existing screens — mapped onto the new palette so
  // components can be migrated incrementally without touching every prop.
  bg: "#faf6f7",
  bgElevated: "#ffffff",
  cardBorder: "#ece0e5",
  text: "#2b1a21",
  textMuted: "#8b7a81",
  primary: "#970747",
  primaryDark: "#6d0834",
  accent: "#c01463",
  white: "#ffffff",
  safe: "#1f9d6b",
  medium: "#c07d16",
  high: "#c0453f",
  critical: "#c0453f",
};

export const bandColor = (band: string): string =>
  ({
    SAFE: colors.safe,
    MEDIUM: colors.medium,
    HIGH: colors.high,
    CRITICAL: colors.critical,
  } as Record<string, string>)[band] || colors.textMuted;

export const spacing = { xs: 4, sm: 8, md: 16, lg: 24, xl: 32 };
export const radius = { sm: 8, md: 12, lg: 16, xl: 24, pill: 999 };

/** Font families — loaded via @expo-google-fonts/* in App.tsx (useFonts). */
export const fonts = {
  heading: "Sora_700Bold",
  headingXBold: "Sora_800ExtraBold",
  headingSemi: "Sora_600SemiBold",
  body: "Manrope_400Regular",
  bodyMedium: "Manrope_500Medium",
  bodySemi: "Manrope_600SemiBold",
  bodyBold: "Manrope_700Bold",
  mono: "IBMPlexMono_500Medium",
  monoSemi: "IBMPlexMono_600SemiBold",
};
