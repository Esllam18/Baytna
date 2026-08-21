import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { colors, radius, spacing } from "../theme/tokens";

export function AccountMenuRow({
  icon,
  title,
  subtitle,
  badge,
  onPress,
}: {
  icon: string;
  title: string;
  subtitle?: string;
  badge?: string | number;
  onPress(): void;
}) {
  return (
    <Pressable onPress={onPress} style={({ pressed }) => [s.row, pressed && s.pressed]}>
      <View style={s.iconWrap}><Text style={s.icon}>{icon}</Text></View>
      <View style={s.body}>
        <Text style={s.title}>{title}</Text>
        {subtitle ? <Text style={s.subtitle}>{subtitle}</Text> : null}
      </View>
      {badge !== undefined ? (
        <View style={s.badge}><Text style={s.badgeText}>{badge}</Text></View>
      ) : null}
      <Text style={s.arrow}>‹</Text>
    </Pressable>
  );
}

const s = StyleSheet.create({
  row: {
    minHeight: 72,
    flexDirection: "row-reverse",
    alignItems: "center",
    gap: spacing.sm,
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  iconWrap: {
    width: 44,
    height: 44,
    borderRadius: 14,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.orangeSoft,
  },
  icon: { fontSize: 21 },
  body: { flex: 1 },
  title: {
    color: colors.ink,
    fontSize: 15,
    fontWeight: "900",
    textAlign: "right",
    writingDirection: "rtl",
  },
  subtitle: {
    color: colors.muted,
    fontSize: 11,
    marginTop: 3,
    textAlign: "right",
    writingDirection: "rtl",
  },
  badge: {
    minWidth: 26,
    height: 26,
    borderRadius: 13,
    paddingHorizontal: 7,
    backgroundColor: colors.orange,
    alignItems: "center",
    justifyContent: "center",
  },
  badgeText: { color: "#fff", fontSize: 11, fontWeight: "900" },
  arrow: { color: colors.muted, fontSize: 28 },
  pressed: { opacity: 0.7 },
});
