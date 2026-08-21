import React from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text } from "react-native";
import { colors, radius } from "../theme/tokens";
export function PrimaryButton({ label, onPress, loading = false, disabled = false }: { label: string; onPress(): void; loading?: boolean; disabled?: boolean }) {
  const off = disabled || loading;
  return <Pressable accessibilityRole="button" disabled={off} onPress={onPress} style={({ pressed }) => [styles.button, off && styles.disabled, pressed && !off && styles.pressed]}>{loading ? <ActivityIndicator color="#fff" /> : <Text style={styles.label}>{label}</Text>}</Pressable>;
}
const styles = StyleSheet.create({ button: { minHeight: 50, borderRadius: radius.md, backgroundColor: colors.orange, alignItems: "center", justifyContent: "center", paddingHorizontal: 18 }, label: { color: "#fff", fontSize: 16, fontWeight: "900" }, disabled: { opacity: 0.45 }, pressed: { opacity: 0.82 } });
