import "react-native-gesture-handler";
import React from "react";
import { View } from "react-native";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { NavigationContainer, DefaultTheme } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { createDrawerNavigator } from "@react-navigation/drawer";
import { StatusBar } from "expo-status-bar";
import { useFonts as useSora, Sora_600SemiBold, Sora_700Bold, Sora_800ExtraBold } from "@expo-google-fonts/sora";
import { useFonts as useManrope, Manrope_400Regular, Manrope_500Medium, Manrope_600SemiBold, Manrope_700Bold } from "@expo-google-fonts/manrope";
import { useFonts as useMono, IBMPlexMono_500Medium, IBMPlexMono_600SemiBold } from "@expo-google-fonts/ibm-plex-mono";

import { AuthProvider, useAuth } from "./src/context/AuthContext";
import { colors } from "./src/theme";
import AppDrawerContent from "./src/components/AppDrawerContent";

// ── Screens ──────────────────────────────────────────────────────────────────
import SplashScreen from "./src/screens/SplashScreen";
import LoginScreen from "./src/screens/LoginScreen";
import RegisterScreen from "./src/screens/RegisterScreen";
import DashboardScreen from "./src/screens/DashboardScreen";
import AIChatScreen from "./src/screens/AIChatScreen";
import SimulatorScreen from "./src/screens/SimulatorScreen";
import GoalsScreen from "./src/screens/GoalsScreen";
import TransferScreen from "./src/screens/TransferScreen";
import ProtectionScreen from "./src/screens/ProtectionScreen";
import LedgerScreen from "./src/screens/LedgerScreen";
import ArchitectureScreen from "./src/screens/ArchitectureScreen";
import InsightsScreen from "./src/screens/InsightsScreen";

const Stack = createNativeStackNavigator();
const Drawer = createDrawerNavigator();

const navTheme = {
  ...DefaultTheme,
  colors: {
    ...DefaultTheme.colors,
    background: colors.page,
    card: colors.card,
    text: colors.ink,
    primary: colors.brand,
    border: colors.border,
    notification: colors.brand2,
  },
};

function AuthStack() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false, contentStyle: { backgroundColor: colors.page } }}>
      <Stack.Screen name="Login" component={LoginScreen} />
      <Stack.Screen name="Register" component={RegisterScreen} />
    </Stack.Navigator>
  );
}

function AppDrawer() {
  return (
    <Drawer.Navigator
      drawerContent={(props) => <AppDrawerContent {...props} />}
      screenOptions={{ headerShown: false, drawerType: "front", overlayColor: "rgba(43,10,25,.45)", drawerStyle: { width: 300 } }}
    >
      <Drawer.Screen name="Dashboard" component={DashboardScreen} />
      <Drawer.Screen name="AIChat" component={AIChatScreen} />
      <Drawer.Screen name="Simulator" component={SimulatorScreen} />
      <Drawer.Screen name="Goals" component={GoalsScreen} />
      <Drawer.Screen name="Transfer" component={TransferScreen} />
      <Drawer.Screen name="Protection" component={ProtectionScreen} />
      <Drawer.Screen name="Ledger" component={LedgerScreen} />
      <Drawer.Screen name="Architecture" component={ArchitectureScreen} />
      {/* Reachable via links (Dashboard → Insights) but not a primary drawer entry */}
      <Drawer.Screen name="Insights" component={InsightsScreen} />
    </Drawer.Navigator>
  );
}

function Routes() {
  const { isAuthenticated, booting } = useAuth();
  if (booting) return <SplashScreen />;
  return isAuthenticated ? <AppDrawer /> : <AuthStack />;
}

export default function App() {
  const [soraLoaded] = useSora({ Sora_600SemiBold, Sora_700Bold, Sora_800ExtraBold });
  const [manropeLoaded] = useManrope({ Manrope_400Regular, Manrope_500Medium, Manrope_600SemiBold, Manrope_700Bold });
  const [monoLoaded] = useMono({ IBMPlexMono_500Medium, IBMPlexMono_600SemiBold });

  if (!soraLoaded || !manropeLoaded || !monoLoaded) {
    return <View style={{ flex: 1, backgroundColor: colors.brand }} />;
  }

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <AuthProvider>
          <StatusBar style="dark" />
          <NavigationContainer theme={navTheme}>
            <Routes />
          </NavigationContainer>
        </AuthProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}
