import React, { useRef, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  Text,
  TextInput,
  View,
} from "react-native";
import { AppShell } from "../components/AppShell";
import { aiChatApi, aiApiError, ChatResponse } from "../lib/api";
import { colors, fonts, radius } from "../theme";

// ─── Suggested starter questions ─────────────────────────────────────────────
const SUGGESTIONS = [
  "What is my spending pattern this month?",
  "How should I invest based on my risk profile?",
  "Explain ELSS tax saving mutual funds",
  "What is the SEBI rule on mutual fund NAV?",
  "How do SIPs work for long-term wealth building?",
];

interface Message {
  id: string;
  role: "user" | "assistant" | "error";
  text: string;
  citations?: ChatResponse["citations"];
  timestamp: Date;
}

function MessageBubble({ msg }: { msg: Message }) {
  const isUser = msg.role === "user";
  const isError = msg.role === "error";

  const bubbleColor = isUser ? colors.brand : isError ? "#fbeceb" : colors.card;
  const textColor = isUser ? "#fff" : isError ? colors.down : colors.ink;

  return (
    <View style={{ alignSelf: isUser ? "flex-end" : "flex-start", maxWidth: "88%", marginVertical: 4, marginHorizontal: 12 }}>
      <View
        style={{
          backgroundColor: bubbleColor,
          borderRadius: 15,
          borderBottomRightRadius: isUser ? 4 : 15,
          borderBottomLeftRadius: isUser ? 15 : 4,
          borderWidth: isUser ? 0 : 1.5,
          borderColor: colors.border,
          padding: isUser ? 12 : 13,
          paddingHorizontal: 15,
        }}
      >
        <Text style={{ color: textColor, fontSize: 13.5, lineHeight: 20, fontFamily: fonts.body }}>{msg.text}</Text>

        {/* RAG citations, framed as "Why I'm saying this" */}
        {msg.citations && msg.citations.length > 0 && (
          <View style={{ marginTop: 11, padding: 11, backgroundColor: colors.pinkTint, borderRadius: 10, borderWidth: 1, borderColor: colors.pinkSoft }}>
            <Text style={{ fontSize: 10, fontFamily: fonts.bodyBold, letterSpacing: 0.5, color: colors.brand, marginBottom: 7 }}>
              WHY I'M SAYING THIS
            </Text>
            {msg.citations.map((c, i) => (
              <View key={i} style={{ flexDirection: "row", gap: 7, marginBottom: 4 }}>
                <Text style={{ color: colors.brand, fontSize: 11.5 }}>·</Text>
                <Text style={{ flex: 1, fontSize: 11.5, color: "#5a4650", lineHeight: 16 }}>
                  [{c.collection}] {c.document_title}
                </Text>
              </View>
            ))}
          </View>
        )}
      </View>

      <Text style={{ color: colors.muted, fontSize: 10, marginTop: 2, alignSelf: isUser ? "flex-end" : "flex-start", marginHorizontal: 4 }}>
        {msg.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
      </Text>
    </View>
  );
}

function TypingIndicator() {
  return (
    <View style={{ alignSelf: "flex-start", marginHorizontal: 12, marginVertical: 4 }}>
      <View style={{ backgroundColor: colors.card, borderRadius: 15, borderBottomLeftRadius: 4, borderWidth: 1.5, borderColor: colors.border, padding: 12, flexDirection: "row", gap: 6, alignItems: "center" }}>
        <ActivityIndicator size="small" color={colors.brand} />
        <Text style={{ color: colors.muted, fontSize: 13 }}>Twin is thinking…</Text>
      </View>
    </View>
  );
}

export default function AIChatScreen() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      text: "Hi — I'm your My Kuber twin. Ask me about savings, SIPs, goals, tax, or anything about your money.",
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | undefined>(undefined);
  const listRef = useRef<FlatList>(null);

  function scrollToBottom() {
    setTimeout(() => listRef.current?.scrollToEnd({ animated: true }), 100);
  }

  async function sendMessage(text: string) {
    const trimmed = text.trim();
    if (!trimmed || loading) return;

    const userMsg: Message = { id: Date.now().toString(), role: "user", text: trimmed, timestamp: new Date() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);
    scrollToBottom();

    try {
      const res = await aiChatApi.send(trimmed, sessionId);
      const responseText =
        typeof res === "string" ? res
          : (res as any).response || (res as any).llm_response || (res as any).formatted_response?.response
            || "I couldn't generate a response. Please try again.";
      const citations = (res as any).citations || (res as any).formatted_response?.citations || undefined;
      const sid = (res as any).session_id || (res as any).formatted_response?.session_id || undefined;
      if (sid && !sessionId) setSessionId(sid);

      setMessages((prev) => [...prev, { id: (Date.now() + 1).toString(), role: "assistant", text: responseText, citations, timestamp: new Date() }]);
    } catch (e) {
      setMessages((prev) => [...prev, { id: (Date.now() + 1).toString(), role: "error", text: aiApiError(e), timestamp: new Date() }]);
    } finally {
      setLoading(false);
      scrollToBottom();
    }
  }

  function clearChat() {
    setMessages([{ id: "welcome", role: "assistant", text: "Chat cleared. How can I help you?", timestamp: new Date() }]);
    setSessionId(undefined);
  }

  return (
    <AppShell title="AI Advisor" mode="back" hideFab scroll={false} noPadding>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : "height"} keyboardVerticalOffset={Platform.OS === "ios" ? 90 : 0}>
        <FlatList
          ref={listRef}
          data={messages}
          keyExtractor={(m) => m.id}
          renderItem={({ item }) => <MessageBubble msg={item} />}
          ListFooterComponent={loading ? <TypingIndicator /> : null}
          onContentSizeChange={scrollToBottom}
          style={{ flex: 1 }}
          contentContainerStyle={{ paddingTop: 12, paddingBottom: 8 }}
        />

        {messages.length <= 1 && (
          <View style={{ paddingHorizontal: 12, paddingBottom: 8, gap: 6 }}>
            <Text style={{ color: colors.muted, fontSize: 12, fontFamily: fonts.bodySemi, paddingHorizontal: 4 }}>Try asking:</Text>
            <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 6 }}>
              {SUGGESTIONS.map((s) => (
                <Pressable
                  key={s}
                  onPress={() => sendMessage(s)}
                  style={{ backgroundColor: colors.pinkTint, borderWidth: 1, borderColor: colors.pinkSoft, borderRadius: radius.pill, paddingHorizontal: 12, paddingVertical: 6 }}
                >
                  <Text style={{ color: colors.brand, fontSize: 12 }}>{s}</Text>
                </Pressable>
              ))}
            </View>
          </View>
        )}

        <View style={{ flexDirection: "row", alignItems: "flex-end", paddingHorizontal: 14, paddingVertical: 10, gap: 8, borderTopWidth: 1, borderTopColor: colors.line, backgroundColor: "#fff" }}>
          <TextInput
            value={input}
            onChangeText={setInput}
            placeholder="Ask about savings, SIPs…"
            placeholderTextColor={colors.grey}
            multiline
            maxLength={2000}
            style={{ flex: 1, minHeight: 44, maxHeight: 120, borderWidth: 1.5, borderColor: colors.border, borderRadius: radius.md, paddingHorizontal: 14, paddingVertical: 10, color: colors.ink, backgroundColor: "#fbf7f9", fontSize: 13.5, fontFamily: fonts.body }}
            onSubmitEditing={() => sendMessage(input)}
            returnKeyType="send"
            blurOnSubmit={false}
          />
          {messages.length > 1 && (
            <Pressable onPress={clearChat} style={{ width: 44, height: 44, borderRadius: radius.md, borderWidth: 1.5, borderColor: colors.border, alignItems: "center", justifyContent: "center", backgroundColor: "#fff" }}>
              <Text style={{ color: colors.muted, fontSize: 18 }}>🗑</Text>
            </Pressable>
          )}
          <Pressable
            onPress={() => sendMessage(input)}
            disabled={!input.trim() || loading}
            style={({ pressed }) => ({
              paddingHorizontal: 16, height: 44, borderRadius: radius.md,
              backgroundColor: !input.trim() || loading ? colors.border : colors.brand,
              alignItems: "center", justifyContent: "center", opacity: pressed ? 0.85 : 1,
            })}
          >
            <Text style={{ color: "#fff", fontFamily: fonts.bodyBold, fontSize: 13.5 }}>Send</Text>
          </Pressable>
        </View>
      </KeyboardAvoidingView>
    </AppShell>
  );
}
