import React from "react";
import { Alert, Linking, Pressable, StyleSheet, Text, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Screen } from "../../src/ui/Screen";
import { PrimaryButton } from "../../src/ui/PrimaryButton";
import { ErrorState, LoadingState } from "../../src/ui/StateViews";
import { useSpecialOrder } from "../../src/hooks/usePostOrder";
import { customerApi } from "../../src/api";
import { queryKeys } from "../../src/query/keys";
import { setPendingPaymentOrder } from "../../src/payment/pendingPayment";
import { egp } from "../../src/utils/format";
import { colors, radius } from "../../src/theme/tokens";

const STATUS: Record<string, string> = {
  chef_review: "بانتظار مراجعة الشيف",
  counter_offer: "الشيف أرسلت عرض بديل",
  awaiting_payment: "العرض جاهز للدفع",
  scheduled: "تم تأكيد وجدولة الطلب",
  rejected: "تعذر تنفيذ الطلب",
  cancelled: "الطلب ملغي",
  expired: "انتهت مهلة العرض",
};

export default function SpecialOrderDetailScreen() {
  const { specialOrderId } = useLocalSearchParams<{ specialOrderId: string }>();
  const id = String(specialOrderId ?? "");
  const q = useSpecialOrder(id);
  const qc = useQueryClient();

  const refresh = () => Promise.all([
    qc.invalidateQueries({ queryKey: queryKeys.specialOrder(id) }),
    qc.invalidateQueries({ queryKey: queryKeys.specialOrders }),
  ]);

  const accept = useMutation({
    mutationFn: () => customerApi.acceptSpecialOrderCounter(id),
    onSuccess: refresh,
  });

  const cancel = useMutation({
    mutationFn: () => customerApi.cancelSpecialOrder(id),
    onSuccess: refresh,
  });

  const checkout = useMutation({
    mutationFn: () => customerApi.checkoutSpecialOrder(
      id,
      `mobile-special-${id}-${Date.now()}`,
    ),
    onSuccess: async (result) => {
      await refresh();
      await setPendingPaymentOrder(result.order.id);
      if (result.payment.checkout_url) {
        await Linking.openURL(result.payment.checkout_url);
      }
      router.push({
        pathname: "/payment/result",
        params: { orderId: result.order.id },
      });
    },
  });

  if (q.isLoading) return <Screen><LoadingState label="بنفتح الطلب الخاص..." /></Screen>;
  if (q.isError || !q.data) return <Screen><ErrorState message="تعذر تحميل الطلب الخاص." /></Screen>;

  const item = q.data;
  const canCancel = ["chef_review", "counter_offer", "awaiting_payment"].includes(item.status);

  return (
    <Screen>
      <View style={s.header}>
        <Text onPress={() => router.back()} style={s.back}>→</Text>
        <Text style={s.title}>تفاصيل الطلب الخاص</Text>
      </View>

      <View style={s.hero}>
        <Text style={s.name}>{item.dish_name}</Text>
        <Text style={s.status}>{STATUS[item.status] ?? item.status}</Text>
        <Text style={s.meta}>الكمية: {item.quantity}</Text>
      </View>

      <Text style={s.section}>طلبك الأصلي</Text>
      <View style={s.card}>
        <Row label="التاريخ" value={new Date(item.requested_service_date).toLocaleDateString("ar-EG")} />
        <Row label="التوصيل" value={windowLabel(item.requested_window_start, item.requested_window_end)} />
        <Row label="السعر للوحدة" value={egp(item.requested_unit_price_minor)} />
        {item.customer_note ? <Text style={s.note}>{item.customer_note}</Text> : null}
      </View>

      {item.status === "counter_offer" ? (
        <>
          <Text style={s.section}>العرض البديل من الشيف</Text>
          <View style={s.offer}>
            <Row label="الموعد الجديد" value={item.proposed_service_date ? new Date(item.proposed_service_date).toLocaleDateString("ar-EG") : "—"} />
            <Row label="التوصيل" value={windowLabel(item.proposed_window_start, item.proposed_window_end)} />
            <Row label="سعر الوحدة" value={item.proposed_unit_price_minor ? egp(item.proposed_unit_price_minor) : "—"} />
            <Row label="الإجمالي" value={item.proposed_unit_price_minor ? egp(item.proposed_unit_price_minor * item.quantity) : "—"} strong />
            {item.chef_note ? <Text style={s.note}>{item.chef_note}</Text> : null}
          </View>
          <PrimaryButton
            label="موافق على العرض"
            onPress={() => accept.mutate()}
            loading={accept.isPending}
          />
        </>
      ) : null}

      {item.status === "awaiting_payment" ? (
        <>
          <Text style={s.section}>العرض النهائي</Text>
          <View style={s.offer}>
            <Row label="التاريخ" value={item.final_service_date ? new Date(item.final_service_date).toLocaleDateString("ar-EG") : "—"} />
            <Row label="التوصيل" value={windowLabel(item.final_window_start, item.final_window_end)} />
            <Row label="الإجمالي" value={item.final_total_minor ? egp(item.final_total_minor) : "—"} strong />
            {item.offer_expires_at ? (
              <Text style={s.expiry}>مهلة الدفع حتى {new Date(item.offer_expires_at).toLocaleString("ar-EG")}</Text>
            ) : null}
          </View>
          <PrimaryButton
            label="ادفع وثبّت الموعد"
            onPress={() => checkout.mutate()}
            loading={checkout.isPending}
          />
        </>
      ) : null}

      {item.status === "scheduled" ? (
        <View style={s.done}>
          <Text style={s.doneTitle}>تم تأكيد الطلب 🎉</Text>
          <Text style={s.doneText}>الشيف وافقت والدفع تم. الطلب دلوقتي داخل مسار التنفيذ العادي.</Text>
          {item.order_id ? (
            <PrimaryButton label="افتح الطلب وتتبع التنفيذ" onPress={() => router.push(`/orders/${item.order_id}`)} />
          ) : null}
        </View>
      ) : null}

      {item.status === "rejected" ? (
        <View style={s.rejected}>
          <Text style={s.rejectedTitle}>الشيف اعتذرت عن الطلب</Text>
          <Text style={s.rejectedText}>{item.rejection_reason || "تعذر تنفيذ الطلب في الموعد الحالي."}</Text>
        </View>
      ) : null}

      <Text style={s.section}>سجل الحالة</Text>
      <View style={s.timeline}>
        {item.events.map((event, index) => (
          <View key={`${event.created_at}-${index}`} style={s.event}>
            <View style={s.dot} />
            <View style={{ flex: 1 }}>
              <Text style={s.eventTitle}>{STATUS[event.to_status] ?? event.to_status}</Text>
              <Text style={s.eventTime}>{new Date(event.created_at).toLocaleString("ar-EG")}</Text>
              {event.reason ? <Text style={s.eventReason}>{event.reason}</Text> : null}
            </View>
          </View>
        ))}
      </View>

      {(accept.isError || checkout.isError || cancel.isError) ? (
        <Text style={s.error}>تعذر تنفيذ العملية. حدّث الصفحة وحاول مرة أخرى.</Text>
      ) : null}

      {canCancel ? (
        <Pressable
          onPress={() => Alert.alert(
            "إلغاء الطلب الخاص",
            "هل تريد إلغاء هذا الطلب قبل الجدولة؟",
            [
              { text: "رجوع", style: "cancel" },
              { text: "إلغاء الطلب", style: "destructive", onPress: () => cancel.mutate() },
            ],
          )}
        >
          <Text style={s.cancel}>إلغاء الطلب الخاص</Text>
        </Pressable>
      ) : null}
    </Screen>
  );
}

function Row({ label, value, strong }: { label: string; value: string; strong?: boolean }) {
  return (
    <View style={s.row}>
      <Text style={[s.rowLabel, strong && s.strong]}>{label}</Text>
      <Text style={[s.rowValue, strong && s.strong]}>{value}</Text>
    </View>
  );
}

function windowLabel(start: string | null, end: string | null) {
  return start && end ? `${start} – ${end}` : "يحددها الشيف";
}

const s = StyleSheet.create({
  header: { flexDirection: "row-reverse", alignItems: "center", gap: 12, paddingTop: 14, paddingBottom: 18 },
  back: { fontSize: 26 },
  title: { flex: 1, fontSize: 22, fontWeight: "900", color: colors.ink, textAlign: "right" },
  hero: { backgroundColor: colors.orangeSoft, borderRadius: radius.card, padding: 17 },
  name: { fontSize: 21, fontWeight: "900", color: colors.ink, textAlign: "right", writingDirection: "rtl" },
  status: { color: colors.orangeDark, fontWeight: "900", textAlign: "right", marginTop: 5, writingDirection: "rtl" },
  meta: { color: colors.muted, fontSize: 11, textAlign: "right", marginTop: 4 },
  section: { fontSize: 16, fontWeight: "900", color: colors.ink, textAlign: "right", writingDirection: "rtl", marginTop: 20, marginBottom: 8 },
  card: { borderWidth: 1, borderColor: colors.border, borderRadius: radius.md, backgroundColor: colors.surface, padding: 14, gap: 9 },
  offer: { borderWidth: 1, borderColor: "#F2BE81", borderRadius: radius.md, backgroundColor: "#FFF5E9", padding: 14, gap: 9, marginBottom: 12 },
  row: { flexDirection: "row-reverse", justifyContent: "space-between", gap: 12 },
  rowLabel: { color: colors.muted, writingDirection: "rtl" },
  rowValue: { color: colors.ink, fontWeight: "800", textAlign: "left" },
  strong: { fontSize: 16, fontWeight: "900", color: colors.orangeDark },
  note: { color: colors.muted, fontSize: 11, lineHeight: 18, textAlign: "right", writingDirection: "rtl", borderTopWidth: 1, borderTopColor: colors.border, paddingTop: 9, marginTop: 3 },
  expiry: { color: colors.danger, fontSize: 10, fontWeight: "800", textAlign: "right", marginTop: 4 },
  done: { marginTop: 18, borderRadius: radius.md, backgroundColor: colors.greenSoft, padding: 15, gap: 9 },
  doneTitle: { color: colors.greenDark, fontWeight: "900", fontSize: 17, textAlign: "right", writingDirection: "rtl" },
  doneText: { color: colors.muted, fontSize: 11, lineHeight: 18, textAlign: "right", writingDirection: "rtl" },
  rejected: { marginTop: 18, borderRadius: radius.md, backgroundColor: colors.dangerSoft, padding: 15 },
  rejectedTitle: { color: colors.danger, fontWeight: "900", textAlign: "right", writingDirection: "rtl" },
  rejectedText: { color: colors.muted, fontSize: 11, lineHeight: 18, textAlign: "right", writingDirection: "rtl", marginTop: 5 },
  timeline: { borderWidth: 1, borderColor: colors.border, borderRadius: radius.md, backgroundColor: colors.surface, padding: 13 },
  event: { flexDirection: "row-reverse", gap: 10, paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: colors.border },
  dot: { width: 10, height: 10, borderRadius: 5, backgroundColor: colors.orange, marginTop: 4 },
  eventTitle: { color: colors.ink, fontWeight: "800", textAlign: "right", writingDirection: "rtl" },
  eventTime: { fontSize: 9, color: colors.muted, textAlign: "right", marginTop: 2 },
  eventReason: { fontSize: 10, color: colors.muted, textAlign: "right", writingDirection: "rtl", marginTop: 3 },
  cancel: { color: colors.danger, fontWeight: "900", textAlign: "center", marginTop: 18, writingDirection: "rtl" },
  error: { color: colors.danger, textAlign: "center", marginTop: 12, writingDirection: "rtl" },
});
