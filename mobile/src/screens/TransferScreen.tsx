import React, { useState } from "react";
import { Pressable, Text, View } from "react-native";
import { useTranslation } from "react-i18next";
import { AppShell } from "../components/AppShell";
import { Card, H2, Muted, AppButton, TextField, Badge } from "../components/ui";
import { colors, fonts } from "../theme";
import { txnApi, apiError } from "../lib/api";
import { verifyBiometric } from "../lib/biometric";
import { FaceScanner } from "../components/FaceScanner";

const fmt = (n: number) => "₹" + Number(n || 0).toLocaleString("en-IN");

const TYPES = [
  { key: "Transfer", note: "" },
  { key: "SIP", note: "SIP contribution" },
  { key: "Invest", note: "Investment" },
];

export default function TransferScreen({ navigation }: any) {
  const { t } = useTranslation();
  const [type, setType] = useState("Transfer");
  const [name, setName] = useState("");
  const [account, setAccount] = useState("");
  const [amount, setAmount] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [pending, setPending] = useState<{ reference: string; threshold: number; requires: string } | null>(null);
  const [done, setDone] = useState<{ balance: number } | null>(null);

  function pickType(k: string) {
    setType(k);
    const t = TYPES.find((x) => x.key === k);
    if (t) setNote(t.note);
  }

  async function submit() {
    setError(""); setBusy(true);
    try {
      const r = await txnApi.transfer({
        beneficiary_name: name, beneficiary_account: account,
        amount: Number(amount), note,
      });
      if (r.status === "completed") setDone({ balance: r.balance });
      else if (r.status === "step_up_required") setPending({ reference: r.reference, threshold: r.threshold, requires: r.requires });
      else setError(r.message || t("transfer.insufficient"));
    } catch (e) { setError(apiError(e)); }
    finally { setBusy(false); }
  }

  function finishResult(r: any) {
    if (r.status === "completed") { setDone({ balance: r.balance }); setPending(null); }
    else setError(r.message || "Verification failed.");
  }

  async function completeBiometric() {
    if (!pending) return;
    setError(""); setBusy(true);
    try {
      const ok = await verifyBiometric("Verify to authorise transfer");
      if (!ok) { setError("Biometric verification failed."); setBusy(false); return; }
      finishResult(await txnApi.verifyBiometric(pending.reference));
    } catch (e) { setError(apiError(e)); }
    finally { setBusy(false); }
  }

  async function completeFace(images: string[]) {
    if (!pending || !images.length) return;
    setError(""); setBusy(true);
    try { finishResult(await txnApi.verifyFaceImage(pending.reference, images[0])); }
    catch (e) { setError(apiError(e)); }
    finally { setBusy(false); }
  }

  if (done) {
    return (
      <AppShell title="New Transaction" mode="back">
        <Card style={{ borderColor: colors.up, alignItems: "center", gap: 12, marginTop: 20 }}>
          <View style={{ width: 52, height: 52, borderRadius: 26, backgroundColor: "#fff", borderWidth: 3, borderColor: colors.upBg, alignItems: "center", justifyContent: "center" }}>
            <Text style={{ fontSize: 22, color: colors.up }}>✔</Text>
          </View>
          <Text style={{ fontSize: 10, fontFamily: fonts.bodyBold, letterSpacing: 0.8, color: colors.up }}>RISK · LOW</Text>
          <H2>{t("transfer.success")}</H2>
          <Muted style={{ textAlign: "center" }}>{fmt(Number(amount))} → {name}</Muted>
          <Muted>{t("dashboard.availableBalance")}: {fmt(done.balance)}</Muted>
          <AppButton title="Start another action" onPress={() => { setDone(null); setName(""); setAccount(""); setAmount(""); setNote(""); }} />
        </Card>
      </AppShell>
    );
  }

  return (
    <AppShell title="New Transaction" mode="back">
      {!pending ? (
        <Card style={{ borderWidth: 0, padding: 0, backgroundColor: "transparent", gap: 14 }}>
          <Text style={{ fontSize: 12, fontFamily: fonts.bodyBold, color: colors.ink, marginBottom: 2 }}>Action type</Text>
          <View style={{ flexDirection: "row", gap: 8 }}>
            {TYPES.map((tItem) => {
              const active = type === tItem.key;
              return (
                <Pressable
                  key={tItem.key}
                  onPress={() => pickType(tItem.key)}
                  style={{
                    flex: 1, padding: 12, borderRadius: 10, alignItems: "center",
                    borderWidth: 1.5, borderColor: active ? colors.brand : colors.border,
                    backgroundColor: active ? colors.pinkTint : "#fff",
                  }}
                >
                  <Text style={{ fontSize: 12.5, fontFamily: fonts.bodyBold, color: active ? colors.brand : colors.muted }}>{tItem.key}</Text>
                </Pressable>
              );
            })}
          </View>

          <TextField label={t("transfer.toName")} value={name} onChangeText={setName} placeholder="Ravi Kumar" />
          <TextField label={t("transfer.toAccount")} value={account} onChangeText={setAccount} keyboardType="number-pad" placeholder="123456789012" />
          <TextField label={`${t("transfer.amount")} (₹)`} value={amount} onChangeText={setAmount} keyboardType="number-pad" placeholder="25000" />
          <Muted style={{ fontSize: 11 }}>Try ₹25,000 (low) vs ₹2,50,000 (high risk).</Muted>
          <TextField label={t("transfer.note")} value={note} onChangeText={setNote} placeholder="—" />

          {error ? <Text style={{ color: colors.down }}>{error}</Text> : null}
          <AppButton title="Run protection check" onPress={submit} loading={busy} disabled={!name || !account || !amount} />
        </Card>
      ) : (
        <Card>
          <Badge label={`⚠ Step-up required`} color={colors.warn} />
          <H2>{pending.requires === "face" ? "Face verification needed" : "Biometric verification needed"}</H2>
          <Muted>{t("settings.threshold")}: {fmt(pending.threshold)}</Muted>
          {error ? <Text style={{ color: colors.down }}>{error}</Text> : null}
          {pending.requires === "face" ? (
            <FaceScanner mode="verify" onDone={completeFace} busy={busy} />
          ) : (
            <AppButton title={t("login.faceVerify")} variant="accent" onPress={completeBiometric} loading={busy} />
          )}
          <AppButton title={t("common.cancel")} variant="ghost" onPress={() => setPending(null)} />
        </Card>
      )}

      <Muted style={{ fontSize: 12 }}>
        Tip: transfers at or above your Face-ID threshold trigger biometric step-up. Adjust it in Wealth Protection.
      </Muted>
    </AppShell>
  );
}
