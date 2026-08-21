import React from "react";
import { Alert, Pressable, StyleSheet, Text, View } from "react-native";
import { router } from "expo-router";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Screen } from "../../../src/ui/Screen";
import { PrimaryButton } from "../../../src/ui/PrimaryButton";
import { EmptyState, ErrorState, LoadingState } from "../../../src/ui/StateViews";
import { useAddresses } from "../../../src/hooks/useCommerce";
import { customerApi } from "../../../src/api";
import { queryKeys } from "../../../src/query/keys";
import { colors, radius, spacing } from "../../../src/theme/tokens";

export default function AddressesScreen() {
  const q = useAddresses();
  const qc = useQueryClient();

  const setDefault = useMutation({
    mutationFn: (id: string) => customerApi.setDefaultAddress(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.addresses }),
  });
  const remove = useMutation({
    mutationFn: (id: string) => customerApi.deleteAddress(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.addresses }),
  });

  if (q.isLoading) return <Screen><LoadingState label="بنجيب عناوينك..." /></Screen>;
  if (q.isError) return <Screen><ErrorState message="تعذر تحميل العناوين." /></Screen>;

  return (
    <Screen>
      <View style={s.header}><Text onPress={() => router.back()} style={s.back}>→</Text><Text style={s.title}>عناويني</Text></View>
      <PrimaryButton label="+ أضف عنوان جديد" onPress={() => router.push("/account/addresses/new")} />
      <View style={s.list}>
        {q.data?.length ? q.data.map((a) => (
          <View key={a.id} style={s.card}>
            <View style={s.row}>
              <View style={{ flex: 1 }}>
                <Text style={s.name}>{a.label || "عنوان"}</Text>
                <Text style={s.address}>{[a.area, a.street, a.building && `مبنى ${a.building}`, a.apartment && `شقة ${a.apartment}`].filter(Boolean).join("، ")}</Text>
              </View>
              {a.is_default ? <View style={s.default}><Text style={s.defaultText}>افتراضي</Text></View> : null}
            </View>
            <View style={s.actions}>
              <Pressable onPress={() => router.push(`/account/addresses/${a.id}`)}><Text style={s.action}>تعديل</Text></Pressable>
              {!a.is_default ? <Pressable onPress={() => setDefault.mutate(a.id)}><Text style={s.action}>اجعله افتراضي</Text></Pressable> : null}
              <Pressable onPress={() => Alert.alert("حذف العنوان", "متأكد إنك عايز تحذف العنوان؟", [
                { text: "إلغاء", style: "cancel" },
                { text: "حذف", style: "destructive", onPress: () => remove.mutate(a.id) },
              ])}><Text style={s.delete}>حذف</Text></Pressable>
            </View>
          </View>
        )) : <EmptyState title="مفيش عناوين محفوظة" body="أضف عنوان علشان الـCheckout يبقى أسرع." />}
      </View>
    </Screen>
  );
}

const s = StyleSheet.create({
  header: { flexDirection: "row-reverse", gap: 12, alignItems: "center", paddingTop: 14, paddingBottom: 18 },
  back: { fontSize: 26 },
  title: { flex: 1, fontSize: 22, fontWeight: "900", textAlign: "right", color: colors.ink },
  list: { gap: 12, marginTop: 18 },
  card: { borderWidth: 1, borderColor: colors.border, borderRadius: radius.md, backgroundColor: colors.surface, padding: 14 },
  row: { flexDirection: "row-reverse", gap: 10, alignItems: "flex-start" },
  name: { fontWeight: "900", color: colors.ink, textAlign: "right", writingDirection: "rtl" },
  address: { color: colors.muted, fontSize: 12, lineHeight: 18, marginTop: 4, textAlign: "right", writingDirection: "rtl" },
  default: { backgroundColor: colors.greenSoft, borderRadius: radius.pill, paddingHorizontal: 9, paddingVertical: 5 },
  defaultText: { color: colors.greenDark, fontSize: 10, fontWeight: "800" },
  actions: { flexDirection: "row-reverse", flexWrap: "wrap", gap: 14, marginTop: 12, paddingTop: 10, borderTopWidth: 1, borderTopColor: colors.border },
  action: { color: colors.orangeDark, fontSize: 12, fontWeight: "800" },
  delete: { color: colors.danger, fontSize: 12, fontWeight: "800" },
});
