import React, { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { Screen } from "../../src/ui/Screen";
import { useChef, useSignatureMenu, useTodayMenu } from "../../src/hooks/useCustomerHome";
import { useChefRatingSummary, useChefReviews } from "../../src/hooks/usePostOrder";
import { LoadingState, ErrorState, EmptyState } from "../../src/ui/StateViews";
import { FavoriteButton } from "../../src/ui/FavoriteButton";
import { colors, radius, spacing } from "../../src/theme/tokens";
import { egp } from "../../src/utils/format";

export default function ChefScreen() {
  const { chefId } = useLocalSearchParams<{ chefId: string }>();
  const id = String(chefId ?? "");
  const chef = useChef(id);
  const today = useTodayMenu(id);
  const signature = useSignatureMenu(id);
  const reviews = useChefReviews(id);
  const rating = useChefRatingSummary(id);
  const [tab, setTab] = useState<"today" | "signature" | "reviews">("today");

  if (chef.isLoading) {
    return <Screen><LoadingState label="بنفتح مطبخ الشيف..." /></Screen>;
  }
  if (chef.isError || !chef.data) {
    return <Screen><ErrorState message="تعذر فتح صفحة الشيف" /></Screen>;
  }

  const c = chef.data;
  const ratingValue = rating.data?.rating ?? c.rating;
  const reviewCount = rating.data?.review_count ?? 0;

  return (
    <Screen contentStyle={{ paddingHorizontal: 0 }}>
      <View style={s.cover}>
        <Text style={s.coverEmoji}>👩‍🍳</Text>
        <Pressable style={s.back} onPress={() => router.back()}>
          <Text style={s.backText}>→</Text>
        </Pressable>
        <FavoriteButton kind="chef" id={id} />
      </View>

      <View style={s.info}>
        <Text style={s.name}>{c.display_name}</Text>
        <Text style={s.specialty}>{c.specialty} • {c.area}</Text>

        <View style={s.stats}>
          <Stat value={ratingValue.toFixed(1)} label={`${reviewCount} تقييم`} />
          <Stat value={c.is_verified ? "موثّق" : "—"} label="الحساب" />
          <Stat value={c.is_open_today ? "مفتوح" : "مغلق"} label="اليوم" />
        </View>

        <View style={s.tabs}>
          <Tab label="مطبخ اليوم" active={tab === "today"} onPress={() => setTab("today")} />
          <Tab label="قائمة التخصص" active={tab === "signature"} onPress={() => setTab("signature")} />
          <Tab label="التقييمات" active={tab === "reviews"} onPress={() => setTab("reviews")} />
        </View>

        {tab === "today" ? (
          today.isLoading ? <LoadingState /> :
          today.isError ? <ErrorState /> :
          today.data?.items.length ? today.data.items.map((item) => (
            <Pressable
              key={item.id}
              onPress={() => router.push({
                pathname: "/chefs/[chefId]/dish/[dishId]",
                params: {
                  chefId: id,
                  dishId: item.dish_id,
                  dailyMenuItemId: item.id,
                },
              })}
              style={s.row}
            >
              <View style={s.dishIcon}><Text style={{ fontSize: 28 }}>🍲</Text></View>
              <View style={s.rowInfo}>
                <Text style={s.dishName}>{item.name}</Text>
                <Text style={item.quantity_available > 0 ? s.available : s.sold}>
                  {item.quantity_available > 0 ? item.availability_label : "نفدت الكمية اليوم"}
                </Text>
              </View>
              <Text style={s.price}>{egp(item.price_minor)}</Text>
            </Pressable>
          )) : (
            <EmptyState
              title="المطبخ مش مفتوح بأكلات اليوم"
              body="تقدر تشوف قائمة التخصص وتطلب الطلبات المتاحة لاحقًا."
            />
          )
        ) : tab === "signature" ? (
          signature.isLoading ? <LoadingState /> :
          signature.isError ? <ErrorState /> :
          signature.data?.length ? signature.data.map((dish) => (
            <Pressable
              key={dish.id}
              onPress={() => router.push({
                pathname: "/chefs/[chefId]/dish/[dishId]",
                params: { chefId: id, dishId: dish.id },
              })}
              style={s.row}
            >
              <View style={s.dishIcon}><Text style={{ fontSize: 28 }}>🥘</Text></View>
              <View style={s.rowInfo}>
                <Text style={s.dishName}>{dish.name}</Text>
                <Text style={s.meta}>
                  {dish.category}
                  {dish.is_special_order_available ? ` • طلب خاص ${dish.prep_notice_hours} س` : ""}
                </Text>
              </View>
              <Text style={s.price}>{egp(dish.base_price_minor)}</Text>
            </Pressable>
          )) : <EmptyState title="قائمة التخصص فارغة" />
        ) : (
          reviews.isLoading || rating.isLoading ? <LoadingState label="بنجيب التقييمات..." /> :
          reviews.isError || rating.isError ? <ErrorState message="تعذر تحميل التقييمات." /> :
          <>
            <View style={s.ratingCard}>
              <Text style={s.ratingBig}>★ {(rating.data?.rating ?? 0).toFixed(1)}</Text>
              <Text style={s.ratingCount}>{rating.data?.review_count ?? 0} تقييم ظاهر</Text>
              <View style={s.ratingMetrics}>
                <RatingMetric label="جودة الأكل" value={rating.data?.food_quality ?? 0} />
                <RatingMetric label="التغليف" value={rating.data?.packaging ?? 0} />
                <RatingMetric label="الدقة" value={rating.data?.order_accuracy ?? 0} />
                <RatingMetric label="القيمة" value={rating.data?.value_for_money ?? 0} />
              </View>
            </View>
            {reviews.data?.length ? reviews.data.map((review) => (
              <View key={review.id} style={s.review}>
                <View style={s.reviewTop}>
                  <Text style={s.reviewStars}>★ {review.chef_overall}/5</Text>
                  <Text style={s.reviewDate}>
                    {new Date(review.created_at).toLocaleDateString("ar-EG")}
                  </Text>
                </View>
                {review.comment ? <Text style={s.reviewComment}>{review.comment}</Text> : null}
                <Text style={s.reviewMeta}>
                  الأكل {review.food_quality}/5 • التغليف {review.packaging}/5 • الدقة {review.order_accuracy}/5
                </Text>
              </View>
            )) : (
              <EmptyState title="لسه مفيش تقييمات ظاهرة" body="أول تقييمات العملاء هتظهر هنا بعد التوصيل." />
            )}
          </>
        )}
      </View>
    </Screen>
  );
}

function Stat({ value, label }: { value: string; label: string }) {
  return (
    <View style={s.stat}>
      <Text style={s.statValue}>{value}</Text>
      <Text style={s.statLabel}>{label}</Text>
    </View>
  );
}

function Tab({ label, active, onPress }: { label: string; active: boolean; onPress(): void }) {
  return (
    <Pressable onPress={onPress} style={[s.tab, active && s.tabActive]}>
      <Text style={[s.tabText, active && s.tabTextActive]}>{label}</Text>
    </Pressable>
  );
}

function RatingMetric({ label, value }: { label: string; value: number }) {
  return (
    <View style={s.ratingMetric}>
      <Text style={s.ratingMetricValue}>{value.toFixed(1)}</Text>
      <Text style={s.ratingMetricLabel}>{label}</Text>
    </View>
  );
}

const s = StyleSheet.create({
  cover: {
    height: 220,
    backgroundColor: colors.orangeSoft,
    alignItems: "center",
    justifyContent: "center",
    position: "relative",
  },
  coverEmoji: { fontSize: 92 },
  back: {
    position: "absolute",
    top: 14,
    right: 18,
    width: 42,
    height: 42,
    borderRadius: 21,
    backgroundColor: "rgba(255,255,255,.92)",
    alignItems: "center",
    justifyContent: "center",
  },
  backText: { fontSize: 25 },
  info: { paddingHorizontal: spacing.lg, paddingTop: 18 },
  name: {
    fontSize: 25,
    fontWeight: "900",
    color: colors.ink,
    textAlign: "right",
    writingDirection: "rtl",
  },
  specialty: {
    fontSize: 14,
    color: colors.muted,
    textAlign: "right",
    writingDirection: "rtl",
    marginTop: 5,
  },
  stats: {
    flexDirection: "row-reverse",
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 17,
    marginTop: 16,
    overflow: "hidden",
  },
  stat: {
    flex: 1,
    paddingVertical: 12,
    alignItems: "center",
    borderLeftWidth: 1,
    borderLeftColor: colors.border,
  },
  statValue: { fontWeight: "900", color: colors.ink },
  statLabel: { fontSize: 10, color: colors.muted, marginTop: 2 },
  tabs: { flexDirection: "row-reverse", flexWrap: "wrap", gap: 8, marginVertical: 16 },
  tab: { paddingVertical: 8, paddingHorizontal: 13, borderRadius: radius.pill, backgroundColor: colors.soft },
  tabActive: { backgroundColor: colors.orangeSoft },
  tabText: { color: colors.muted, fontSize: 12 },
  tabTextActive: { color: colors.orangeDark, fontWeight: "900" },
  row: { minHeight: 78, flexDirection: "row-reverse", alignItems: "center", gap: 11, borderBottomWidth: 1, borderBottomColor: colors.border, paddingVertical: 11 },
  dishIcon: { width: 56, height: 56, borderRadius: 15, backgroundColor: "#FFEAD6", alignItems: "center", justifyContent: "center" },
  rowInfo: { flex: 1 },
  dishName: { fontWeight: "900", color: colors.ink, textAlign: "right", writingDirection: "rtl" },
  meta: { fontSize: 11, color: colors.muted, textAlign: "right", writingDirection: "rtl", marginTop: 3 },
  available: { fontSize: 11, color: colors.greenDark, textAlign: "right", marginTop: 3 },
  sold: { fontSize: 11, color: colors.danger, textAlign: "right", marginTop: 3 },
  price: { color: colors.orangeDark, fontWeight: "900" },
  ratingCard: { backgroundColor: colors.orangeSoft, borderRadius: radius.card, padding: 16, alignItems: "center", marginBottom: 12 },
  ratingBig: { color: "#C47B17", fontSize: 30, fontWeight: "900" },
  ratingCount: { color: colors.muted, fontSize: 10, marginTop: 2 },
  ratingMetrics: { flexDirection: "row-reverse", gap: 6, marginTop: 13 },
  ratingMetric: { flex: 1, alignItems: "center", backgroundColor: "rgba(255,255,255,.72)", borderRadius: 11, paddingVertical: 8 },
  ratingMetricValue: { color: colors.orangeDark, fontWeight: "900" },
  ratingMetricLabel: { color: colors.muted, fontSize: 8, marginTop: 2 },
  review: { borderWidth: 1, borderColor: colors.border, borderRadius: radius.md, backgroundColor: colors.surface, padding: 13, marginBottom: 10 },
  reviewTop: { flexDirection: "row-reverse", justifyContent: "space-between" },
  reviewStars: { color: "#C47B17", fontWeight: "900" },
  reviewDate: { color: colors.muted, fontSize: 9 },
  reviewComment: { color: colors.ink, lineHeight: 19, fontSize: 12, textAlign: "right", writingDirection: "rtl", marginTop: 8 },
  reviewMeta: { color: colors.muted, fontSize: 9, textAlign: "right", writingDirection: "rtl", marginTop: 8 },
});
