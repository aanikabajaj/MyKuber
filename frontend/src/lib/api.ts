import axios from "axios";

export const TOKEN_KEY = "iaare_access";
export const REFRESH_KEY = "iaare_refresh";

export const api = axios.create({ baseURL: "" });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

let refreshing = false;
api.interceptors.response.use(
  (r) => r,
  async (error) => {
    const original = error.config;
    if (
      error.response?.status === 401 &&
      !original._retry &&
      localStorage.getItem(REFRESH_KEY) &&
      !original.url?.includes("/api/auth/refresh")
    ) {
      original._retry = true;
      if (!refreshing) {
        refreshing = true;
        try {
          const { data } = await axios.post("/api/auth/refresh", {
            refresh_token: localStorage.getItem(REFRESH_KEY),
          });
          localStorage.setItem(TOKEN_KEY, data.access_token);
        } catch {
          localStorage.removeItem(TOKEN_KEY);
          localStorage.removeItem(REFRESH_KEY);
        } finally {
          refreshing = false;
        }
      }
      const token = localStorage.getItem(TOKEN_KEY);
      if (token) {
        original.headers.Authorization = `Bearer ${token}`;
        return api(original);
      }
    }
    return Promise.reject(error);
  }
);

export function apiError(e: any): string {
  const d = e?.response?.data?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d) && d[0]?.msg) return d[0].msg.replace(/^Value error, /, "");
  return e?.message || "Something went wrong.";
}

// ---------------- Types ----------------
export interface RiskFactor { name: string; points: number; detail: string; }
export interface RiskInfo {
  score: number; band: string; decision: string;
  factors: RiskFactor[]; geo?: any;
}
export interface LoginSession {
  session_id: string | null;
  status: string;
  risk: RiskInfo;
  required_steps: string[];
  completed_steps: string[];
  next_step: string | null;
  second_factor: string | null;
  user_display?: string;
  message?: string;
  tokens?: { access_token: string; refresh_token: string; user: any } | null;
}
export interface UserProfile {
  id: number; first_name: string; last_name: string; full_name: string;
  email: string; mobile: string; city?: string; state?: string; country?: string;
  username: string; is_admin: boolean; second_factor?: string;
  totp_enabled: boolean; face_enabled: boolean;
  email_verified: boolean; mobile_verified: boolean;
  created_at?: string; last_login_at?: string;
}

// ---------------- Captcha ----------------
export const captchaApi = {
  get: () => api.get<{ captcha_id: string; image: string }>("/api/captcha").then((r) => r.data),
};

// ---------------- Registration ----------------
export const registerApi = {
  details: (payload: any) =>
    api.post("/api/register/details", payload).then((r) => r.data),
  authHeader: (token: string) => ({ headers: { Authorization: `Bearer ${token}` } }),
  mobileSend: (t: string) => api.post("/api/register/mobile/send-otp", {}, registerApi.authHeader(t)).then((r) => r.data),
  mobileVerify: (t: string, code: string) => api.post("/api/register/mobile/verify-otp", { code }, registerApi.authHeader(t)).then((r) => r.data),
  emailSend: (t: string) => api.post("/api/register/email/send-otp", {}, registerApi.authHeader(t)).then((r) => r.data),
  emailVerify: (t: string, code: string) => api.post("/api/register/email/verify-otp", { code }, registerApi.authHeader(t)).then((r) => r.data),
  authSetup: (t: string) => api.post("/api/register/authenticator/setup", {}, registerApi.authHeader(t)).then((r) => r.data),
  authVerify: (t: string, code: string) => api.post("/api/register/authenticator/verify", { code }, registerApi.authHeader(t)).then((r) => r.data),
  setMpin: (t: string, mpin: string) => api.post("/api/register/mpin", { mpin }, registerApi.authHeader(t)).then((r) => r.data),
  enrollFace: (t: string, embeddings: number[][]) => api.post("/api/register/second-factor/face", { embeddings }, registerApi.authHeader(t)).then((r) => r.data),
  passkeyOptions: (t: string) => api.post("/api/register/second-factor/passkey/options", {}, registerApi.authHeader(t)).then((r) => r.data),
  passkeyVerify: (t: string, handle: string, credential: any) => api.post("/api/register/second-factor/passkey/verify", { handle, credential }, registerApi.authHeader(t)).then((r) => r.data),
  registerDevice: (t: string, device: any) => api.post("/api/register/device", device, registerApi.authHeader(t)).then((r) => r.data),
};

// ---------------- Login ----------------
export const loginApi = {
  password: (payload: any) => api.post<LoginSession>("/api/login/password", payload).then((r) => r.data),
  mpin: (session_id: string, mpin: string) => api.post<LoginSession>("/api/login/step/mpin", { session_id, mpin }).then((r) => r.data),
  face: (session_id: string, embedding: number[]) => api.post<LoginSession>("/api/login/step/face", { session_id, embedding }).then((r) => r.data),
  passkeyOptions: (session_id: string) => api.post("/api/login/step/passkey/options", { session_id }).then((r) => r.data),
  passkeyVerify: (session_id: string, handle: string, credential: any) => api.post<LoginSession>("/api/login/step/passkey/verify", { session_id, handle, credential }).then((r) => r.data),
  emailOtpSend: (session_id: string) => api.post("/api/login/step/email-otp/send", { session_id }).then((r) => r.data),
  emailOtpVerify: (session_id: string, code: string) => api.post<LoginSession>("/api/login/step/email-otp/verify", { session_id, code }).then((r) => r.data),
  smsOtpSend: (session_id: string) => api.post("/api/login/step/sms-otp/send", { session_id }).then((r) => r.data),
  smsOtpVerify: (session_id: string, code: string) => api.post<LoginSession>("/api/login/step/sms-otp/verify", { session_id, code }).then((r) => r.data),
  totp: (session_id: string, token: string) => api.post<LoginSession>("/api/login/step/totp", { session_id, token }).then((r) => r.data),
};

// ---------------- User ----------------
export const userApi = {
  me: () => api.get<UserProfile>("/api/user/me").then((r) => r.data),
  devices: () => api.get("/api/user/devices").then((r) => r.data),
  removeDevice: (id: number) => api.delete(`/api/user/devices/${id}`).then((r) => r.data),
  loginHistory: () => api.get("/api/user/login-history").then((r) => r.data),
  passkeys: () => api.get("/api/user/passkeys").then((r) => r.data),
  removePasskey: (id: number) => api.delete(`/api/user/passkeys/${id}`).then((r) => r.data),
  resetMpin: (current_password: string, new_mpin: string) => api.post("/api/user/mpin/reset", { current_password, new_mpin }).then((r) => r.data),
  reenrollFace: (embeddings: number[][]) => api.post("/api/user/face/re-enroll", { embeddings }).then((r) => r.data),
  addPasskeyOptions: () => api.post("/api/user/passkey/add/options", {}).then((r) => r.data),
  addPasskeyVerify: (handle: string, credential: any) => api.post("/api/user/passkey/add/verify", { handle, credential }).then((r) => r.data),
};

// ---------------- Admin ----------------
export const adminApi = {
  stats: () => api.get("/api/admin/stats").then((r) => r.data),
  riskDistribution: () => api.get("/api/admin/risk-distribution").then((r) => r.data),
  authStats: () => api.get("/api/admin/auth-stats").then((r) => r.data),
  loginAttempts: () => api.get("/api/admin/login-attempts").then((r) => r.data),
  auditLogs: () => api.get("/api/admin/audit-logs").then((r) => r.data),
  users: () => api.get("/api/admin/users").then((r) => r.data),
  map: () => api.get("/api/admin/map").then((r) => r.data),
};
