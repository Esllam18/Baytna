import React from "react";
import { Alert, Linking, Pressable, StyleSheet, Text, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { customerApi } from "../../src/api";
import { ApiClientError } from "../../src/api/http";
import { useOrder } from "../../src/hooks/useCommerce";
import { useReviewEligibility } from "../../src/hooks/usePostOrder";
import { queryKeys } from "../../src/query/keys";
import { Screen } from "../../src/ui/Screen";
import { PrimaryButton } from "../../src/ui/PrimaryButton";
import { ErrorState, LoadingState } from "../../src/ui/StateViews";
import { colors, radius } from "../../src/theme/tokens";
import { egp } from "../../src/utils/format";
import { setPendingPaymentOrder } from "../../src/payment/pendingPayment";

const STATUS_LABELS: Record<string, string> = {
  pending_payment: "بانتظار الدفع",
  confirmed: "تم التأكيد",
  accepted_by_chef: "الشيف بدأت تجهيز أكلك",
  preparing: "جاري الطبخ",
  packaging: "جاري التغليف",
  ready_for_pickup: "جاهز للاستلام",
  assigned_to_driver: "المندوب متجه للشيف",
  picked_up: "المندوب استلم الطلب",
  out_for_delivery: "طلبك في الطريق",
  delivered: "تم التوصيل",
  cancelled: "ملغي",
  expired: "منتهي",
};

export default function OrderDetailScreen() {
  const { orderId } = useLocalSearchParams<{ orderId: string }>();
  const id = String(orderId ?? "");
  const q = useOrder(id);
  const review = useReviewEligibility(id);
  const qc = useQueryClient();

  const cancel = useMutation({
    mutationFn: () => customerApi.cancelOrder(id),
    onSuccess: async () => {
      await Promise.all([
        qc.invalidateQueries({ queryKey: queryKeys.order(id) }),
        qc.invalidateQueries({ queryKey: queryKeys.orders }),
      ]);
    },
  });

  const pay = useMutation({
    mutationFn: async () => {
      let payment;
      try {
        payment = await customerApi.payment(id);
      } catch (error) {
        if (!(error instanceof ApiClientError) || error.status !== 404) throw error;
      }

      if (!payment || payment.status !== "pending" || !payment.checkout_url) {
        payment = await customerApi.createPaymentIntent(
          id,
          `mobile-retry-${id}-${Date.now()}`,
        );
      }

      await setPendingPaymentOrder(id);
      return payment;
    },
    onSuccess: async (payment) => {
      if (payment.checkout_url) await Linking.openURL(payment.checkout_url);
      router.push({ pathname: "/payment/result", params: { orderId: id } });
    },
  });

  if (q.isLoading) {
    return <Screen><LoadingState label="بنفتح تفاصيل الطلب..." /></Screen>;
  }
  if (q.isError || !q.data) {
    return <Screen><ErrorState message="تعذر تحميل الطلب." /></Screen>;
  }

  const o = q.data;
  const canCancel = o.status === "pending_payment";
  const delivered = o.status === "delivered";
  const reviewExists = review.data?.reason === "review_exists";

  return (
    <Screen>
      <View style={s.header}>
        <Pressable onPress={() => router.back()} style={s.back}>
          <Text style={s.backText}>→</Text>
        </Pressable>
        <Text style={s.title}>تفاصيل الطلب</Text>
        <View style={{ width: 42 }} />
      </View>

      <View style={s.hero}>
        <Text style={s.heroTitle}>طلب #{o.id.slice(0, 8).toUpperCase()}</Text>
        <Text style={s.heroStatus}>{STATUS_LABELS[o.status] ?? o.status}</Text>
        <Text style={s.heroDate}>
          الخدمة: {new Date(o.service_date).toLocaleDateString("ar-EG")}
        </Text>
        {o.order_type === "special" ? (
          <View style={s.specialBadge}>
            <Text style={s.specialBadgeText}>طلب خاص</Text>
          </View>
        ) : null}
      </View>

      <Text style={s.section}>الوجبات</Text>
      {o.items.map((item) => (
        <View key={item.id} style={s.item}>
          <Text style={s.itemName}>{item.dish_name} × {item.quantity}</Text>
          <Text style={s.itemPrice}>{egp(item.line_total_minor)}</Text>
        </View>
      ))}

      <Text style={s.section}>الحساب</Text>
      <View style={s.summary}>
        <Row label="الأكل" value={egp(o.subtotal_minor)} />
        <Row label="التوصيل" value={egp(o.delivery_fee_minor)} />
        {o.discount_minor > 0 ? (
          <Row label="الخصم" value={`− ${egp(o.discount_minor)}`} />
        ) : null}
        <View style={s.divider} />
        <Row label="الإجمالي" value={egp(o.total_minor)} strong />
      </View>

      {o.status === "pending_payment" ? (
        <PrimaryButton
          label="كمّل الدفع"
          loading={pay.isPending}
          onPress={() => pay.mutate()}
        />
      ) : !["cancelled", "expired", "delivered"].includes(o.status) ? (
        <PrimaryButton
          label="تتبع الطلب لحظة بلحظة"
          onPress={() => router.push(`/orders/${o.id}/tracking`)}
        />
      ) : null}

      {delivered ? (
        <View style={s.postOrder}>
          <Text style={s.postTitle}>بعد ما استلمت طلبك</Text>
          <Text style={s.postText}>
            رأيك بيساعد الشيف وبيساعد بيتنا يحافظ على الجودة.
          </Text>
          <PrimaryButton
            label={reviewExists ? "عدّل تقييمك" : "قيّم الطلب"}
            onPress={() => router.push(`/orders/${o.id}/review`)}
          />
          <Pressable
            onPress={() =>
              router.push({
                pathname: "/account/support/new",
                params: { orderId: o.id },
              })
            }
          >
            <Text style={s.help}>في مشكلة في الطلب؟ افتح طلب دعم</Text>
          </Pressable>
        </View>
      ) : null}

      <Pressable onPress={() => router.push(`/chefs/${o.chef_id}`)}>
        <Text style={s.chefLink}>اطلب من نفس الشيف مرة تانية</Text>
      </Pressable>

      {pay.isError ? (
        <Text style={s.error}>تعذر بدء الدفع. حاول مرة أخرى.</Text>
      ) : null}

      {canCancel ? (
        <Pressable
          onPress={() =>
            Alert.alert(
              "إلغاء الطلب",
              "سيتم إلغاء الطلب قبل إتمام الدفع وإرجاع حجز المخزون.",
              [
                { text: "رجوع", style: "cancel" },
                {
                  text: "إلغاء الطلب",
                  style: "destructive",
                  onPress: () => cancel.mutate(),
                },
              ],
            )
          }
        >
          <Text style={s.cancel}>إلغاء الطلب</Text>
        </Pressable>
      ) : null}

      {cancel.isError ? (
        <Text style={s.error}>تعذر إلغاء الطلب.</Text>
      ) : null}
    </Screen>
  );
}

function Row({
  label,
  value,
  strong,
}: {
  label: string;
  value: string;
  strong?: boolean;
}) {
  return (
    <View style={s.row}>
      <Text style={[s.label, strong && s.strong]}>{label}</Text>
      <Text style={[s.value, strong && s.strong]}>{value}</Text>
    </View>
  );
}

const s = StyleSheet.create({
  header: {
    flexDirection: "row-reverse",
    justifyContent: "space-between",
    alignItems: "center",
    paddingTop: 12,
  },
  back: {
    width: 42,
    height: 42,
    borderRadius: 21,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.surface,
  },
  backText: { fontSize: 24 },
  title: {
    fontSize: 22,
    fontWeight: "900",
    color: colors.ink,
    writingDirection: "rtl",
  },
  hero: {
    marginTop: 18,
    padding: 16,
    borderRadius: radius.md,
    backgroundColor: colors.orangeSoft,
  },
  heroTitle: {
    fontSize: 18,
    fontWeight: "900",
    color: colors.ink,
    textAlign: "right",
  },
  heroStatus: {
    fontWeight: "800",
    color: colors.orangeDark,
    textAlign: "right",
    marginTop: 5,
    writingDirection: "rtl",
  },
  heroDate: {
    fontSize: 11,
    color: colors.muted,
    textAlign: "right",
    marginTop: 4,
  },
  specialBadge: {
    alignSelf: "flex-end",
    marginTop: 9,
    borderRadius: radius.pill,
    backgroundColor: "#FFF",
    paddingHorizontal: 9,
    paddingVertical: 5,
  },
  specialBadgeText: {
    color: colors.orangeDark,
    fontSize: 9,
    fontWeight: "900",
  },
  section: {
    fontSize: 17,
    fontWeight: "900",
    color: colors.ink,
    textAlign: "right",
    writingDirection: "rtl",
    marginTop: 22,
    marginBottom: 10,
  },
  item: {
    flexDirection: "row-reverse",
    justifyContent: "space-between",
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    paddingVertical: 10,
  },
  itemName: { color: colors.ink, writingDirection: "rtl" },
  itemPrice: { fontWeight: "800", color: colors.orangeDark },
  summary: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    backgroundColor: colors.surface,
    padding: 14,
    gap: 9,
    marginBottom: 18,
  },
  row: {
    flexDirection: "row-reverse",
    justifyContent: "space-between",
  },
  label: { color: colors.muted, writingDirection: "rtl" },
  value: { color: colors.ink, fontWeight: "700" },
  strong: { fontSize: 16, fontWeight: "900", color: colors.ink },
  divider: { height: 1, backgroundColor: colors.border },
  postOrder: {
    marginTop: 14,
    borderRadius: radius.card,
    backgroundColor: colors.greenSoft,
    padding: 15,
    gap: 8,
  },
  postTitle: {
    color: colors.greenDark,
    fontWeight: "900",
    fontSize: 16,
    textAlign: "right",
    writingDirection: "rtl",
  },
  postText: {
    color: colors.muted,
    fontSize: 11,
    lineHeight: 18,
    textAlign: "right",
    writingDirection: "rtl",
  },
  help: {
    color: colors.orangeDark,
    fontWeight: "900",
    fontSize: 11,
    textAlign: "center",
    marginTop: 4,
    writingDirection: "rtl",
  },
  chefLink: {
    color: colors.orangeDark,
    fontWeight: "900",
    textAlign: "center",
    marginTop: 16,
    writingDirection: "rtl",
  },
  cancel: {
    color: colors.danger,
    fontWeight: "900",
    textAlign: "center",
    writingDirection: "rtl",
    marginTop: 16,
  },
  error: {
    color: colors.danger,
    textAlign: "center",
    marginTop: 8,
  },
});
