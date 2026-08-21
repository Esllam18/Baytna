import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { router } from "expo-router";
import { Screen } from "../../src/ui/Screen";
import { EmptyState, ErrorState, LoadingState } from "../../src/ui/StateViews";
import { useSpecialOrders } from "../../src/hooks/usePostOrder";
import { egp } from "../../src/utils/format";
import { colors, radius } from "../../src/theme/tokens";

const LABELS: Record<string, string> = {
  chef_review: "بانتظار رد الشيف",
  counter_offer: "عرض بديل من الشيف",
  awaiting_payment: "جاهز للدفع",
  scheduled: "تم الجدولة",
  rejected: "اعتذرت الشيف",
  cancelled: "ملغي",
  expired: "انتهت المهلة",
};

export default function SpecialOrdersScreen() {
  const q = useSpecialOrders();
  if (q.isLoading) return <Screen><LoadingState label="بنجيب طلباتك الخاصة..." /></Screen>;
  if (q.isError) return <Screen><ErrorState message="تعذر تحميل الطلبات الخاصة." /></Screen>;

  return (
    <Screen>
      <View style={s.header}>
        <Text onPress={() => router.back()} style={s.back}>→</Text>
        <Text style={s.title}>الطلبات الخاصة</Text>
      </View>

      {q.data?.length ? q.data.map((item) => (
        <Pressable
          key={item.id}
          onPress={() => router.push(`/special-orders/${item.id}`)}
          style={s.card}
        >
          <View style={s.row}>
            <View style={{ flex: 1 }}>
              <Text style={s.name}>{item.dish_name}</Text>
              <Text style={s.meta}>
                {item.quantity} × {new Date(item.requested_service_date).toLocaleDateString("ar-EG")}
              </Text>
            </View>
            <View style={[s.status, item.status === "scheduled" && s.statusDone]}>
              <Text style={[s.statusText, item.status === "scheduled" && s.statusDoneText]}>
                {LABELS[item.status] ?? item.status}
              </Text>
            </View>
          </View>
          <View style={s.footer}>
            <Text style={s.type}>{item.request_type === "preorder" ? "طلب مسبق" : "طلب خاص"}</Text>
            <Text style={s.price}>
              {egp(item.final_total_minor ?? item.requested_unit_price_minor * item.quantity)}
            </Text>
          </View>
        </Pressable>
      )) : (
        <EmptyState
          title="لسه مفيش طلبات خاصة"
          body="من قائمة تخصص أي شيف، اختار طبق متاح للطلب الخاص وحدد الموعد."
        />
      )}
    </Screen>
  );
}

const s = StyleSheet.create({
  header: { flexDirection: "row-reverse", alignItems: "center", gap: 12, paddingTop: 14, paddingBottom: 18 },
  back: { fontSize: 26 },
  title: { flex: 1, fontSize: 22, fontWeight: "900", color: colors.ink, textAlign: "right" },
  card: { borderWidth: 1, borderColor: colors.border, borderRadius: radius.md, backgroundColor: colors.surface, padding: 14, marginBottom: 12 },
  row: { flexDirection: "row-reverse", alignItems: "center", gap: 10 },
  name: { fontWeight: "900", color: colors.ink, textAlign: "right", writingDirection: "rtl" },
  meta: { fontSize: 11, color: colors.muted, marginTop: 4, textAlign: "right", writingDirection: "rtl" },
  status: { borderRadius: radius.pill, backgroundColor: colors.orangeSoft, paddingHorizontal: 9, paddingVertical: 6 },
  statusText: { fontSize: 9, fontWeight: "800", color: colors.orangeDark },
  statusDone: { backgroundColor: colors.greenSoft },
  statusDoneText: { color: colors.greenDark },
  footer: { flexDirection: "row-reverse", justifyContent: "space-between", alignItems: "center", marginTop: 12, borderTopWidth: 1, borderTopColor: colors.border, paddingTop: 10 },
  type: { color: colors.muted, fontSize: 10 },
  price: { color: colors.orangeDark, fontWeight: "900" },
});
