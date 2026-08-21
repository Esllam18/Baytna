import React from "react";
import { StyleSheet, Switch, Text, View } from "react-native";
import { AddressCreate } from "../api/types";
import { colors, spacing } from "../theme/tokens";
import { FormField } from "./FormField";
import { PrimaryButton } from "./PrimaryButton";

export function AddressForm({
  value,
  onChange,
  onSubmit,
  loading,
  submitLabel,
}: {
  value: AddressCreate;
  onChange(value: AddressCreate): void;
  onSubmit(): void;
  loading?: boolean;
  submitLabel: string;
}) {
  const set = (key: keyof AddressCreate, next: string | boolean) =>
    onChange({ ...value, [key]: next });

  return (
    <View style={s.form}>
      <FormField label="اسم العنوان" value={value.label ?? ""} onChangeText={(x) => set("label", x)} placeholder="البيت، الشغل..." />
      <FormField label="المنطقة" value={value.area} onChangeText={(x) => set("area", x)} placeholder="6 أكتوبر" />
      <FormField label="الشارع" value={value.street ?? ""} onChangeText={(x) => set("street", x)} placeholder="اسم الشارع" />
      <View style={s.two}>
        <View style={s.half}><FormField label="المبنى" value={value.building ?? ""} onChangeText={(x) => set("building", x)} /></View>
        <View style={s.half}><FormField label="الدور" value={value.floor ?? ""} onChangeText={(x) => set("floor", x)} /></View>
      </View>
      <FormField label="الشقة" value={value.apartment ?? ""} onChangeText={(x) => set("apartment", x)} />
      <View style={s.switchRow}>
        <Switch
          value={value.is_default}
          onValueChange={(x) => set("is_default", x)}
          trackColor={{ false: "#DDD3C9", true: colors.orangeSoft }}
          thumbColor={value.is_default ? colors.orange : "#F7F2ED"}
        />
        <View style={{ flex: 1 }}>
          <Text style={s.switchTitle}>العنوان الافتراضي</Text>
          <Text style={s.switchText}>هيظهر أول اختيار في الـCheckout.</Text>
        </View>
      </View>
      <PrimaryButton
        label={submitLabel}
        onPress={onSubmit}
        loading={loading}
        disabled={!value.area.trim()}
      />
    </View>
  );
}

const s = StyleSheet.create({
  form: { gap: spacing.md },
  two: { flexDirection: "row-reverse", gap: spacing.sm },
  half: { flex: 1 },
  switchRow: {
    flexDirection: "row-reverse",
    alignItems: "center",
    gap: spacing.md,
    paddingVertical: 8,
  },
  switchTitle: {
    fontWeight: "900",
    color: colors.ink,
    textAlign: "right",
    writingDirection: "rtl",
  },
  switchText: {
    color: colors.muted,
    fontSize: 11,
    marginTop: 2,
    textAlign: "right",
    writingDirection: "rtl",
  },
});
