import React from "react";
import { SafeAreaView, ScrollView, StyleSheet, View, ViewStyle } from "react-native";
import { colors, spacing } from "../theme/tokens";
export function Screen({ children, scroll = true, contentStyle }: { children: React.ReactNode; scroll?: boolean; contentStyle?: ViewStyle }) {
  const body = <View style={[styles.content, contentStyle]}>{children}</View>;
  return <SafeAreaView style={styles.safe}>{scroll ? <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">{body}</ScrollView> : body}</SafeAreaView>;
}
const styles = StyleSheet.create({ safe: { flex: 1, backgroundColor: colors.canvas }, scroll: { flexGrow: 1 }, content: { flex: 1, paddingHorizontal: spacing.lg, paddingBottom: 28 } });
