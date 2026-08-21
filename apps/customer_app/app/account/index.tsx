import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { router } from "expo-router";
import { Screen } from "../../src/ui/Screen";
import { BottomNav } from "../../src/ui/BottomNav";
import { AccountMenuRow } from "../../src/ui/AccountMenuRow";
import { LoadingState } from "../../src/ui/StateViews";
import { useProfile, useNotificationSummary, useSupportTickets } from "../../src/hooks/useAccount";
import { useMyReviews, useSpecialOrders } from "../../src/hooks/usePostOrder";
import { useAddresses, useLoyalty } from "../../src/hooks/useCommerce";
import { customerApi } from "../../src/api";
import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "../../src/query/keys";
import { colors, radius, spacing } from "../../src/theme/tokens";

export default function AccountScreen() {
  const profile = useProfile();
  const addresses = useAddresses();
  const loyalty = useLoyalty();
  const notifications = useNotificationSummary();
  const support = useSupportTickets();
  const reviews = useMyReviews();
  const specialOrders = useSpecialOrders();
  const favorites = useQuery({
    queryKey: queryKeys.favorites,
    queryFn: () => customerApi.favorites(),
  });

  if (profile.isLoading) {
    return <Screen><LoadingState label="بنفتح حسابك..." /></Screen>;
  }

  const p = profile.data;

  return (
    <View style={s.page}>
      <Screen>
        <View style={s.header}>
          <View style={s.avatar}><Text style={s.avatarText}>👤</Text></View>
          <View style={s.headerBody}>
            <Text style={s.name}>{p?.display_name || "ضيف بيتنا"}</Text>
            <Text style={s.phone}>{p?.phone}</Text>
          </View>
        </View>

        <View style={s.stats}>
          <Stat value={loyalty.data?.balance_points ?? 0} label="نقطة" />
          <Stat value={(favorites.data?.chefs_count ?? 0) + (favorites.data?.dishes_count ?? 0)} label="مفضلة" />
          <Stat value={addresses.data?.length ?? 0} label="عنوان" />
        </View>

        <View style={s.card}>
          <AccountMenuRow icon="👤" title="بيانات الحساب" subtitle="الاسم واللغة" onPress={() => router.push("/account/profile")} />
          <AccountMenuRow icon="📍" title="عناويني" subtitle="إضافة وتعديل العناوين" badge={addresses.data?.length ?? 0} onPress={() => router.push("/account/addresses")} />
          <AccountMenuRow icon="♥" title="المفضلة" subtitle="الشيفات والأكلات اللي بتحبها" badge={(favorites.data?.chefs_count ?? 0) + (favorites.data?.dishes_count ?? 0)} onPress={() => router.push("/account/favorites")} />
          <AccountMenuRow icon="🔔" title="الإشعارات" subtitle="آخر تحديثات طلباتك" badge={notifications.data?.unread_count ?? 0} onPress={() => router.push("/account/notifications")} />
          <AccountMenuRow icon="★" title="نقاط بيتنا" subtitle="رصيدك وسجل النقاط" badge={loyalty.data?.balance_points ?? 0} onPress={() => router.push("/account/loyalty")} />
          <AccountMenuRow icon="📝" title="تقييماتي" subtitle="راجع أو عدّل تقييمات الطلبات" badge={reviews.data?.length ?? 0} onPress={() => router.push("/account/reviews")} />
          <AccountMenuRow icon="📅" title="الطلبات الخاصة" subtitle="طلبات المناسبات والحجز المسبق" badge={specialOrders.data?.filter(x => !["cancelled", "rejected", "expired"].includes(x.status)).length ?? 0} onPress={() => router.push("/special-orders")} />

          <AccountMenuRow icon="💬" title="الدعم والمساعدة" subtitle="الشكاوى والاستفسارات" badge={support.data?.filter(x => !["resolved", "closed"].includes(x.status)).length ?? 0} onPress={() => router.push("/account/support")} />
          <AccountMenuRow icon="⚙" title="الإعدادات" subtitle="الإشعارات والاشتراك وتسجيل الخروج" onPress={() => router.push("/account/settings")} />
        </View>
      </Screen>
      <BottomNav active="account" />
    </View>
  );
}

function Stat({ value, label }: { value: number; label: string }) {
  return (
    <View style={s.stat}>
      <Text style={s.statValue}>{value}</Text>
      <Text style={s.statLabel}>{label}</Text>
    </View>
  );
}

const s = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.canvas },
  header: {
    flexDirection: "row-reverse",
    alignItems: "center",
    gap: spacing.md,
    paddingTop: 18,
    paddingBottom: 18,
  },
  avatar: {
    width: 72,
    height: 72,
    borderRadius: 24,
    backgroundColor: colors.orangeSoft,
    alignItems: "center",
    justifyContent: "center",
  },
  avatarText: { fontSize: 34 },
  headerBody: { flex: 1 },
  name: {
    fontSize: 22,
    fontWeight: "900",
    color: colors.ink,
    textAlign: "right",
    writingDirection: "rtl",
  },
  phone: { color: colors.muted, marginTop: 4, textAlign: "right" },
  stats: {
    flexDirection: "row-reverse",
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    backgroundColor: colors.surface,
    overflow: "hidden",
    marginBottom: 18,
  },
  stat: { flex: 1, alignItems: "center", paddingVertical: 13 },
  statValue: { fontSize: 18, fontWeight: "900", color: colors.orangeDark },
  statLabel: { fontSize: 10, color: colors.muted, marginTop: 2 },
  card: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.card,
    paddingHorizontal: 14,
    overflow: "hidden",
  },
});
