# IAARE REST API Reference

Base URL: `http://localhost:8000` · Interactive docs (Swagger): `http://localhost:8000/docs`

All request/response bodies are JSON. Authenticated endpoints expect `Authorization: Bearer <token>`.

## Health
| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Service health & demo-mode flag |
| GET | `/` | Service metadata |

## CAPTCHA
| Method | Path | Description |
|---|---|---|
| GET | `/api/captcha` | Returns `{ captcha_id, image }` (image is a data-URI PNG) |

## Registration (`Authorization: Bearer <registration_token>` after step 1)
| Method | Path | Body | Description |
|---|---|---|---|
| POST | `/api/register/details` | account details + password | Creates the account, returns `registration_token` |
| POST | `/api/register/mobile/send-otp` | — | Sends SMS OTP (dev code returned in demo mode) |
| POST | `/api/register/mobile/verify-otp` | `{ code }` | Verifies mobile |
| POST | `/api/register/email/send-otp` | — | Sends Email OTP |
| POST | `/api/register/email/verify-otp` | `{ code }` | Verifies email |
| POST | `/api/register/authenticator/setup` | — | Returns TOTP `secret`, `otpauth_uri`, `qr_data_uri` |
| POST | `/api/register/authenticator/verify` | `{ code }` | Verifies first TOTP token |
| POST | `/api/register/mpin` | `{ mpin }` | Sets 6-digit MPIN |
| POST | `/api/register/second-factor/face` | `{ embedding[] }` | Enrolls face embedding |
| POST | `/api/register/second-factor/passkey/options` | — | WebAuthn registration options |
| POST | `/api/register/second-factor/passkey/verify` | `{ handle, credential }` | Completes passkey registration |
| POST | `/api/register/device` | device info | Registers the browser as a trusted device |
| GET | `/api/register/status` | — | Current registration stage |

## Login (adaptive)
| Method | Path | Body | Description |
|---|---|---|---|
| POST | `/api/login/password` | `{ username, password, captcha_id, captcha_answer, device, simulate? }` | Verifies password + CAPTCHA, runs the risk engine, returns a login session |
| POST | `/api/login/step/mpin` | `{ session_id, mpin }` | MPIN factor |
| POST | `/api/login/step/face` | `{ session_id, embedding[] }` | Face factor |
| POST | `/api/login/step/passkey/options` | `{ session_id }` | Passkey auth options |
| POST | `/api/login/step/passkey/verify` | `{ session_id, handle, credential }` | Passkey factor |
| POST | `/api/login/step/email-otp/send` · `/verify` | `{ session_id }` · `{ session_id, code }` | Email OTP factor |
| POST | `/api/login/step/sms-otp/send` · `/verify` | `{ session_id }` · `{ session_id, code }` | SMS OTP factor |
| POST | `/api/login/step/totp` | `{ session_id, token }` | Authenticator factor |
| GET | `/api/login/session/{id}` | — | Current session state |

**Login session object**
```json
{
  "session_id": "…",
  "status": "pending | approved | blocked | expired",
  "risk": { "score": 45, "band": "MEDIUM", "decision": "STEP_UP", "factors": [...], "geo": {...} },
  "required_steps": ["mpin", "second_factor", "email_otp"],
  "completed_steps": ["mpin"],
  "next_step": "second_factor",
  "second_factor": "face | passkey",
  "tokens": { "access_token": "…", "refresh_token": "…", "user": {...} }  // on approval
}
```

**`simulate` (demo only)** — force any scenario:
`{ enabled, force_band: "SAFE|MEDIUM|HIGH|CRITICAL", is_vpn, new_device, country, city, latitude, longitude, failed_attempts }`

## Auth / User
| Method | Path | Description |
|---|---|---|
| POST | `/api/auth/refresh` | Exchange refresh token for a new access token |
| GET | `/api/auth/me` | Current user |
| POST | `/api/auth/logout` | Client-side token discard |
| GET | `/api/user/me` | Profile |
| GET/DELETE | `/api/user/devices` · `/devices/{id}` | Trusted devices |
| GET | `/api/user/login-history` | Recent logins |
| GET/DELETE | `/api/user/passkeys` · `/passkeys/{id}` | Passkeys |
| POST | `/api/user/mpin/reset` | `{ current_password, new_mpin }` |
| POST | `/api/user/face/re-enroll` | `{ embedding[] }` |
| POST | `/api/user/passkey/add/options` · `/verify` | Add a passkey |

## Admin (`Authorization: Bearer <admin access token>`)
| Method | Path | Description |
|---|---|---|
| GET | `/api/admin/stats` | Headline counters |
| GET | `/api/admin/risk-distribution` | Login counts per risk band |
| GET | `/api/admin/auth-stats` | Factor adoption counts |
| GET | `/api/admin/login-attempts` | Recent attempts |
| GET | `/api/admin/audit-logs` | Audit trail |
| GET | `/api/admin/users` | All users |
| GET | `/api/admin/map` | Aggregated geo login points |
