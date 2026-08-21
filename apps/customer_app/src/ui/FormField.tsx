import React from "react";
import { StyleSheet, Text, TextInput, TextInputProps, View } from "react-native";
import { colors, radius, spacing } from "../theme/tokens";

export function FormField({
  label,
  ...props
}: TextInputProps & { label: string }) {
  return (
    <View style={s.wrap}>
      <Text style={s.label}>{label}</Text>
      <TextInput
        {...props}
        style={[s.input, props.multiline && s.multiline]}
        placeholderTextColor="#A2968C"
        textAlign="right"
      />
    </View>
  );
}

const s = StyleSheet.create({
  wrap: { gap: spacing.xs },
  label: {
    color: colors.ink,
    fontWeight: "800",
    fontSize: 12,
    textAlign: "right",
    writingDirection: "rtl",
  },
  input: {
    minHeight: 48,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    backgroundColor: colors.surface,
    color: colors.ink,
    paddingHorizontal: 13,
    paddingVertical: 11,
    writingDirection: "rtl",
  },
  multiline: { minHeight: 110, textAlignVertical: "top" },
});
