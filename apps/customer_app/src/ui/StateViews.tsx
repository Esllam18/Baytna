import React from "react";
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";
import { colors, spacing } from "../theme/tokens";
export function LoadingState({ label = "جاري التحميل..." }: { label?: string }) { return <View style={s.wrap}><ActivityIndicator color={colors.orange} /><Text style={s.text}>{label}</Text></View>; }
export function ErrorState({ message = "حصلت مشكلة. حاول مرة أخرى." }: { message?: string }) { return <View style={s.wrap}><Text style={s.error}>!</Text><Text style={s.text}>{message}</Text></View>; }
export function EmptyState({ title, body }: { title: string; body?: string }) { return <View style={s.wrap}><Text style={s.title}>{title}</Text>{body ? <Text style={s.text}>{body}</Text> : null}</View>; }
const s = StyleSheet.create({ wrap: { paddingVertical: 36, alignItems: "center", gap: spacing.sm }, title: { color: colors.ink, fontWeight: "800", fontSize: 16, textAlign: "center", writingDirection: "rtl" }, text: { color: colors.muted, textAlign: "center", writingDirection: "rtl" }, error: { width: 38, height: 38, textAlign: "center", lineHeight: 38, borderRadius: 19, backgroundColor: colors.dangerSoft, color: colors.danger, fontWeight: "900" } });
