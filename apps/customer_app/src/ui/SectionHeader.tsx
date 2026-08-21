import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { colors, spacing } from "../theme/tokens";
export function SectionHeader({ title, action, onAction }: { title: string; action?: string; onAction?: () => void }) { return <View style={s.row}><Text style={s.title}>{title}</Text>{action && onAction ? <Pressable onPress={onAction}><Text style={s.action}>{action}</Text></Pressable> : null}</View>; }
const s = StyleSheet.create({ row: { flexDirection: "row-reverse", justifyContent: "space-between", alignItems: "center", marginTop: spacing.xl, marginBottom: spacing.sm }, title: { fontSize: 18, fontWeight: "900", color: colors.ink, writingDirection: "rtl" }, action: { color: colors.orangeDark, fontWeight: "800", writingDirection: "rtl" } });
