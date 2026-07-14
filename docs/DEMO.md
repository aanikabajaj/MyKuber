# Demo Script & Credentials

## Demo accounts
| Username | Password | MPIN | Role |
|---|---|---|---|
| `admin` | `Admin@1234` | `123456` | Admin |
| `rahul` | `Rahul@1234` | `654321` | Customer |
| `priya` | `Priya@1234` | `112233` | Customer |

> Seeded accounts use **Face** as their strong factor and **auto-pass the biometric step in demo
> mode** — click **“Simulate capture (demo accounts)”** on the face step, so you can log them in on
> any machine. Newly registered accounts use **genuine** face matching / real passkeys.

## Suggested 5-minute flow

### 1 · Registration (the full enrollment journey)
1. Landing → **Open an Account**.
2. Fill the form (strong password enforced) → **Create Account**.
3. **Mobile OTP** — code shows in the amber demo banner; click it to autofill → **Verify**.
4. **Email OTP** — same.
5. **Authenticator** — scan the QR with Google Authenticator (or read the manual key), enter the 6-digit code.
6. **MPIN** — set a 6-digit PIN.
7. **Choose your strong factor** — **Face** (camera enroll) *or* **Passkey** (Windows Hello / Touch ID).
8. 🎉 Registration complete.

### 2 · Adaptive login — SAFE
- Log in as the account you just created from the **same browser**.
- The device is trusted → **SAFE** band → MPIN → Face/Passkey → dashboard.
- Point out the **risk gauge** and the **factor breakdown** showing *why* it was SAFE.

### 3 · Watch the engine adapt (Demo Console on the login page)
Arm a scenario, then log in:
| Scenario | Result |
|---|---|
| **MEDIUM** | adds **Email OTP** |
| **HIGH** | adds **SMS OTP + Authenticator** |
| **CRITICAL** | **login blocked** + user-notified screen |
| Toggle **VPN / New device / Foreign country / failed attempts** | score climbs, factors are added live |

### 4 · Admin Command Center
- Log in as **admin** → `/admin`.
- Show: headline stats, **Risk Distribution** donut, **Authentication Factors** bar, **7-day** login/blocked trend, **Global Login Activity** map, and the **login + audit** tables updating with every attempt you made.

## Talking points
- **Transparent risk** — every score comes with an explainable factor list (no black box).
- **Right-sized friction** — trusted users breeze in; risky attempts are challenged or blocked.
- **Real crypto** — bcrypt password/MPIN hashing, Fernet-encrypted TOTP secrets & face embeddings, JWT sessions, real FIDO2/WebAuthn passkeys.
- **Provider-ready** — SMS/Email sit behind one interface; add credentials to go live.
