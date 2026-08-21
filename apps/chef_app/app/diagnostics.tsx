import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import * as Sentry from "@sentry/react-native";

const enabled = process.env.EXPO_PUBLIC_BAYTNA_ENABLE_DIAGNOSTICS === "true";

export default function DiagnosticsScreen() {
  if (!enabled) {
    return (
      <SafeAreaView style={s.page}>
        <View style={s.card}>
          <Text style={s.title}>Diagnostics disabled</Text>
          <Text style={s.body}>
            This route is disabled in normal pilot and production builds.
          </Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={s.page}>
      <View style={s.card}>
        <Text style={s.title}>Baytna Chef Diagnostics</Text>
        <Text style={s.body}>
          Release 0.50.0. Use only on a controlled diagnostic build.
        </Text>
        <Pressable
          style={s.safeButton}
          onPress={() => {
            Sentry.captureMessage("Baytna chef diagnostic event", "info");
          }}
        >
          <Text style={s.buttonText}>Send non-fatal Sentry event</Text>
        </Pressable>
        <Pressable
          style={s.dangerButton}
          onPress={() => {
            throw new Error("Baytna chef controlled crash probe");
          }}
        >
          <Text style={s.buttonText}>Trigger controlled JS crash</Text>
        </Pressable>
      </View>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  page: {
    flex: 1,
    backgroundColor: "#FFF9F4",
    justifyContent: "center",
    padding: 20,
  },
  card: { backgroundColor: "#fff", borderRadius: 20, padding: 20, gap: 14 },
  title: { fontSize: 20, fontWeight: "900", textAlign: "center" },
  body: { fontSize: 12, color: "#75675E", textAlign: "center" },
  safeButton: { backgroundColor: "#32734B", padding: 14, borderRadius: 12 },
  dangerButton: { backgroundColor: "#B64040", padding: 14, borderRadius: 12 },
  buttonText: { color: "#fff", fontWeight: "900", textAlign: "center" },
});
