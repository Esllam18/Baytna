import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { colors, spacing } from "../theme/tokens";

export function StarRating({
  label,
  value,
  onChange,
  optional = false,
}: {
  label: string;
  value: number | null;
  onChange(value: number | null): void;
  optional?: boolean;
}) {
  return (
    <View style={s.row}>
      <View style={s.labelWrap}>
        <Text style={s.label}>{label}</Text>
        {optional ? (
          <Text onPress={() => onChange(null)} style={s.optional}>
            {value === null ? "غير محدد" : "مسح"}
          </Text>
        ) : null}
      </View>
      <View style={s.stars}>
        {[1, 2, 3, 4, 5].map((star) => (
          <Pressable
            key={star}
            accessibilityRole="button"
            accessibilityLabel={`${label}: ${star} من 5`}
            onPress={() => onChange(star)}
            hitSlop={6}
          >
            <Text style={[s.star, (value ?? 0) >= star && s.active]}>
              ★
            </Text>
          </Pressable>
        ))}
      </View>
    </View>
  );
}

const s = StyleSheet.create({
  row: {
    gap: spacing.sm,
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  labelWrap: {
    flexDirection: "row-reverse",
    justifyContent: "space-between",
    alignItems: "center",
  },
  label: {
    fontWeight: "900",
    color: colors.ink,
    textAlign: "right",
    writingDirection: "rtl",
  },
  optional: {
    color: colors.muted,
    fontSize: 10,
    fontWeight: "700",
  },
  stars: {
    flexDirection: "row-reverse",
    justifyContent: "flex-start",
    gap: 7,
  },
  star: {
    fontSize: 31,
    color: "#D9D0C8",
  },
  active: {
    color: "#F4A340",
  },
});
