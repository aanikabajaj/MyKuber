import axios from "axios";
import Constants from "expo-constants";
import { Platform } from "react-native";

/**
 * Resolve the backend base URL.
 * On a physical device (Expo Go) `localhost` is the phone itself, so we derive
 * the dev machine's LAN IP from Expo's hostUri and target :8000 there.
 * Override with EXPO_PUBLIC_API_URL if needed.
 */
function resolveBaseUrl(): string {
  const override = process.env.EXPO_PUBLIC_API_URL;
  if (override) return override;
  const hostUri =
    (Constants.expoConfig as any)?.hostUri ||
    (Constants as any)?.manifest?.debuggerHost ||
    (Constants as any)?.manifest2?.extra?.expoGo?.debuggerHost;
  const host = hostUri ? String(hostUri).split(":")[0] : "localhost";
  if (Platform.OS === "web") return "http://localhost:8000";
  return `http://${host}:8000`;
}

export const API_URL = resolveBaseUrl();

/**
 * AI gateway runs on port 8001.
 * Override independently with EXPO_PUBLIC_AI_URL if needed.
 */
function resolveAiBaseUrl(): string {
  const override = process.env.EXPO_PUBLIC_AI_URL;
  if (override) return override;
  return API_URL.replace(/:8000$/, ":8001");
}

export const AI_URL = resolveAiBaseUrl();

// ─── Axios instances ──────────────────────────────────────────────────────────
export const api = axios.create({ baseURL: API_URL, timeout: 20000 });
export const aiApi = axios.create({ baseURL: AI_URL, timeout: 35000 });

// ─── Shared auth token ────────────────────────────────────────────────────────
let authToken: string | null = null;

/** Set the JWT on both the backend and AI gateway clients simultaneously. */
export function setAuthToken(token: string | null) {
  authToken = token;
  const header = token ? `Bearer ${token}` : "";
  aiApi.defaults.headers.common["Authorization"] = header;
}

api.interceptors.request.use((config) => {
  if (authToken) config.headers.Authorization = `Bearer ${authToken}`;
  return config;
});

// ─── Error helper ─────────────────────────────────────────────────────────────
export function apiError(e: any): string {
  const d = e?.response?.data?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d) && d[0]?.msg) return d[0].msg.replace(/^Value error, /, "");
  if (e?.message === "Network Error") return `Cannot reach server at ${API_URL}`;
  return e?.message || "Something went wrong.";
}

export function aiApiError(e: any): string {
  const d = e?.response?.data?.detail;
  if (typeof d === "string") return d;
  if (d?.message) return d.message;
  if (e?.code === "ECONNABORTED") return "AI service timed out — please try again.";
  if (e?.message === "Network Error") return `Cannot reach AI service at ${AI_URL}`;
  return e?.message || "AI service unavailable.";
}

// ─── Types ────────────────────────────────────────────────────────────────────
export interface RiskFactor { name: string; points: number; detail: string; }
export interface LoginSession {
  session_id: string | null;
  status: string;
  risk: { score: number; band: string; decision: string; factors: RiskFactor[]; geo?: any };
  required_steps: string[];
  completed_steps: string[];
  next_step: string | null;
  second_factor: string | null;
  user_display?: string;
  message?: string;
  tokens?: { access_token: string; refresh_token: string; user: any } | null;
}

// ─── Backend endpoints ────────────────────────────────────────────────────────
export const authApi = {
  health: () => api.get("/api/health").then((r) => r.data),
  me: () => api.get("/api/user/me").then((r) => r.data),
  refresh: (refresh_token: string) =>
    api.post("/api/auth/refresh", { refresh_token }).then((r) => r.data),
};

export const captchaApi = {
  get: () => api.get<{ captcha_id: string; image: string }>("/api/captcha").then((r) => r.data),
  math: () => api.get<{ captcha_id: string; question: string }>("/api/captcha/math").then((r) => r.data),
};

export const loginApi = {
  password: (payload: any) => api.post<LoginSession>("/api/login/password", payload).then((r) => r.data),
  mpin: (session_id: string, mpin: string) =>
    api.post<LoginSession>("/api/login/step/mpin", { session_id, mpin }).then((r) => r.data),
  face: (session_id: string, embedding: number[]) =>
    api.post<LoginSession>("/api/login/step/face", { session_id, embedding }).then((r) => r.data),
  faceImage: (session_id: string, image: string) =>
    api.post<LoginSession>("/api/login/step/face-image", { session_id, image }).then((r) => r.data),
  emailOtpSend: (session_id: string) =>
    api.post("/api/login/step/email-otp/send", { session_id }).then((r) => r.data),
  emailOtpVerify: (session_id: string, code: string) =>
    api.post<LoginSession>("/api/login/step/email-otp/verify", { session_id, code }).then((r) => r.data),
  smsOtpSend: (session_id: string) =>
    api.post("/api/login/step/sms-otp/send", { session_id }).then((r) => r.data),
  smsOtpVerify: (session_id: string, code: string) =>
    api.post<LoginSession>("/api/login/step/sms-otp/verify", { session_id, code }).then((r) => r.data),
  biometric: (session_id: string) =>
    api.post<LoginSession>("/api/login/step/biometric", { session_id }).then((r) => r.data),
  totp: (session_id: string, token: string) =>
    api.post<LoginSession>("/api/login/step/totp", { session_id, token }).then((r) => r.data),
  // SIM binding verification during login
  simVerify: (session_id: string, sim_fingerprint: string) =>
    api.post<LoginSession>("/api/login/step/sim-verify", { session_id, sim_fingerprint }).then((r) => r.data),
  simEnroll: (sim_fingerprint: string) =>
    api.post("/api/login/sim/enroll", { sim_fingerprint }).then((r) => r.data),
};

const rh = (t: string) => ({ headers: { Authorization: `Bearer ${t}` } });
export const registerApi = {
  details: (payload: any) => api.post("/api/register/details", payload).then((r) => r.data),
  mobileSend: (t: string) => api.post("/api/register/mobile/send-otp", {}, rh(t)).then((r) => r.data),
  mobileVerify: (t: string, code: string) => api.post("/api/register/mobile/verify-otp", { code }, rh(t)).then((r) => r.data),
  emailSend: (t: string) => api.post("/api/register/email/send-otp", {}, rh(t)).then((r) => r.data),
  emailVerify: (t: string, code: string) => api.post("/api/register/email/verify-otp", { code }, rh(t)).then((r) => r.data),
  authSetup: (t: string) => api.post("/api/register/authenticator/setup", {}, rh(t)).then((r) => r.data),
  authVerify: (t: string, code: string) => api.post("/api/register/authenticator/verify", { code }, rh(t)).then((r) => r.data),
  setMpin: (t: string, mpin: string) => api.post("/api/register/mpin", { mpin }, rh(t)).then((r) => r.data),
  enrollBiometric: (t: string) => api.post("/api/register/second-factor/biometric", {}, rh(t)).then((r) => r.data),
  enrollFaceImages: (t: string, images: string[]) => api.post("/api/register/second-factor/face-images", { images }, rh(t)).then((r) => r.data),
  registerDevice: (t: string, device: any) => api.post("/api/register/device", device, rh(t)).then((r) => r.data),
  // SIM verification during registration
  simVerifySend: (t: string) => api.post("/api/register/sim-verify/send-otp", {}, rh(t)).then((r) => r.data),
  simVerifyConfirm: (t: string, code: string, sim_fingerprint?: string) =>
    api.post("/api/register/sim-verify/confirm", { code, sim_fingerprint }, rh(t)).then((r) => r.data),
  simEnroll: (t: string, sim_fingerprint: string) =>
    api.post("/api/register/sim/enroll", { sim_fingerprint }, rh(t)).then((r) => r.data),
};

export const userApi = {
  me: () => api.get("/api/user/me").then((r) => r.data),
  prefs: () => api.get("/api/user/security-prefs").then((r) => r.data),
  updatePrefs: (payload: any) => api.put("/api/user/security-prefs", payload).then((r) => r.data),
  reenrollFace: (embeddings: number[][]) =>
    api.post("/api/user/face/re-enroll", { embeddings }).then((r) => r.data),
};

export const txnApi = {
  balance: () => api.get("/api/txn/balance").then((r) => r.data),
  transfer: (payload: any) => api.post("/api/txn/transfer", payload).then((r) => r.data),
  verifyFace: (reference: string, embedding: number[]) =>
    api.post("/api/txn/verify-face", { reference, embedding }).then((r) => r.data),
  verifyBiometric: (reference: string) =>
    api.post("/api/txn/verify-biometric", { reference }).then((r) => r.data),
  verifyFaceImage: (reference: string, image: string) =>
    api.post("/api/txn/verify-face-image", { reference, image }).then((r) => r.data),
  history: () => api.get("/api/txn/history").then((r) => r.data),
};

// ─── AI Gateway types ─────────────────────────────────────────────────────────

export interface ChatResponse {
  response: string;
  intent?: string;
  confidence?: number;
  session_id?: string;
  citations?: Array<{ collection: string; document_title: string; text: string }>;
}

export interface FinancialProfile {
  risk_profile: string | null;
  investment_goals: string[];
  holdings: string[];
  sip_details: any[];
  investment_horizon_years: number | null;
  preferred_asset_classes: string[];
}

export interface MonthlyCashflow {
  month: string;
  total_debit: number;
  total_credit: number;
}

export interface AnomalySpike {
  date: string;
  amount: number;
  beneficiary_name: string;
  note: string;
  z_score: number;
}

export interface TransactionAnalysis {
  monthly_cashflow: MonthlyCashflow[];
  category_breakdown: Record<string, number>;
  recurring_transactions: any[];
  anomaly_spikes: AnomalySpike[];
  income_trend: any;
}

// ─── AI Gateway endpoints (port 8001) ─────────────────────────────────────────

export const aiChatApi = {
  send: (message: string, session_id?: string): Promise<ChatResponse> =>
    aiApi.post("/ai/chat", { message, session_id }).then((r) => r.data),
};

export const aiProfileApi = {
  get: (): Promise<FinancialProfile> =>
    aiApi.get("/ai/profile").then((r) => r.data),
  update: (payload: Partial<FinancialProfile>): Promise<FinancialProfile> =>
    aiApi.post("/ai/memory/update", payload).then((r) => r.data),
};

export const aiTxnApi = {
  analyze: (): Promise<TransactionAnalysis> =>
    aiApi.post("/ai/transactions/analyze", {}).then((r) => r.data),
};

export const aiHealthApi = {
  check: () => aiApi.get("/ai/health").then((r) => r.data),
};
