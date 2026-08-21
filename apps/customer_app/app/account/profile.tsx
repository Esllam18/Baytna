import React, { useEffect, useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import { router } from "expo-router";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Screen } from "../../src/ui/Screen";
import { FormField } from "../../src/ui/FormField";
import { PrimaryButton } from "../../src/ui/PrimaryButton";
import { LoadingState, ErrorState } from "../../src/ui/StateViews";
import { useProfile } from "../../src/hooks/useAccount";
import { customerApi } from "../../src/api";
import { queryKeys } from "../../src/query/keys";
import { colors, radius, spacing } from "../../src/theme/tokens";

export default function ProfileScreen() {
  const profile = useProfile();
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [language, setLanguage] = useState<"ar" | "en">("ar");

  useEffect(() => {
    if (profile.data) {
      setName(profile.data.display_name ?? "");
      setLanguage(profile.data.preferred_language);
    }
  }, [profile.data]);

  const save = useMutation({
    mutationFn: () => customerApi.updateProfile({
      display_name: name.trim() || null,
      preferred_language: language,
    }),
    onSuccess: async () => {
      await Promise.all([
        qc.invalidateQueries({ queryKey: queryKeys.profile }),
        qc.invalidateQueries({ queryKey: queryKeys.home }),
      ]);
      router.back();
    },
  });

  if (profile.isLoading) return <Screen><LoadingState /></Screen>;
  if (profile.isError || !profile.data) return <Screen><ErrorState /></Screen>;

  return (
    <Screen>
      <Header title="بيانات الحساب" />
      <View style={s.form}>
        <FormField label="الاسم" value={name} onChangeText={setName} placeholder="اسمك اللي يظهر في بيتنا" />
        <View>
          <Text style={s.label}>رقم الهاتف</Text>
          <View style={s.readonly}><Text style={s.readonlyText}>{profile.data.phone}</Text></View>
          <Text style={s.note}>رقم الهاتف هو وسيلة تسجيل الدخول الحالية.</Text>
        </View>
        <View>
          <Text style={s.label}>لغة التطبيق</Text>
          <View style={s.langRow}>
            <LanguageChip label="العربية" active={language === "ar"} onPress={() => setLanguage("ar")} />
            <LanguageChip label="English" active={language === "en"} onPress={() => setLanguage("en")} />
          </View>
        </View>
        {save.isError ? <Text style={s.error}>تعذر حفظ البيانات. حاول مرة أخرى.</Text> : null}
        <PrimaryButton label="حفظ التغييرات" onPress={() => save.mutate()} loading={save.isPending} />
      </View>
    </Screen>
  );
}

function Header({ title }: { title: string }) {
  return <View style={s.header}><Text onPress={() => router.back()} style={s.back}>→</Text><Text style={s.title}>{title}</Text></View>;
}
function LanguageChip({ label, active, onPress }: { label: string; active: boolean; onPress(): void }) {
  return <Text onPress={onPress} style={[s.chip, active && s.chipActive]}>{label}</Text>;
}
const s = StyleSheet.create({
  header: { flexDirection: "row-reverse", alignItems: "center", gap: 12, paddingTop: 14, paddingBottom: 20 },
  back: { fontSize: 26, color: colors.ink },
  title: { flex: 1, fontSize: 22, fontWeight: "900", color: colors.ink, textAlign: "right", writingDirection: "rtl" },
  form: { gap: spacing.lg },
  label: { fontSize: 12, fontWeight: "800", color: colors.ink, textAlign: "right", marginBottom: 6 },
  readonly: { minHeight: 48, borderRadius: radius.md, backgroundColor: colors.soft, padding: 13 },
  readonlyText: { color: colors.muted, textAlign: "right" },
  note: { color: colors.muted, fontSize: 10, marginTop: 5, textAlign: "right", writingDirection: "rtl" },
  langRow: { flexDirection: "row-reverse", gap: 8 },
  chip: { borderWidth: 1, borderColor: colors.border, borderRadius: radius.pill, paddingHorizontal: 14, paddingVertical: 9, color: colors.muted },
  chipActive: { backgroundColor: colors.orangeSoft, borderColor: colors.orange, color: colors.orangeDark, fontWeight: "900" },
  error: { color: colors.danger, textAlign: "right", writingDirection: "rtl" },
});
