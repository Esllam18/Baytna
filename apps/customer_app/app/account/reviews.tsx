import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { router } from "expo-router";
import { Screen } from "../../src/ui/Screen";
import { EmptyState, ErrorState, LoadingState } from "../../src/ui/StateViews";
import { useMyReviews } from "../../src/hooks/usePostOrder";
import { colors, radius } from "../../src/theme/tokens";

export default function MyReviewsScreen() {
  const q = useMyReviews();

  if (q.isLoading) return <Screen><LoadingState label="بنجيب تقييماتك..." /></Screen>;
  if (q.isError) return <Screen><ErrorState message="تعذر تحميل التقييمات." /></Screen>;

  return (
    <Screen>
      <View style={s.header}>
        <Text onPress={() => router.back()} style={s.back}>→</Text>
        <Text style={s.title}>تقييماتي</Text>
      </View>

      {q.data?.length ? q.data.map((review) => (
        <Pressable
          key={review.id}
          onPress={() => router.push(`/orders/${review.order_id}/review`)}
          style={s.card}
        >
          <View style={s.row}>
            <View style={{ flex: 1 }}>
              <Text style={s.order}>طلب #{review.order_id.slice(0, 8).toUpperCase()}</Text>
              <Text style={s.date}>{new Date(review.updated_at).toLocaleDateString("ar-EG")}</Text>
            </View>
            <Text style={s.rating}>★ {review.chef_overall}/5</Text>
          </View>
          <View style={s.metrics}>
            <Metric label="الأكل" value={review.food_quality} />
            <Metric label="التغليف" value={review.packaging} />
            <Metric label="الدقة" value={review.order_accuracy} />
            <Metric label="القيمة" value={review.value_for_money} />
          </View>
          {review.comment ? <Text style={s.comment}>{review.comment}</Text> : null}
          <Text style={s.edit}>تعديل التقييم</Text>
        </Pressable>
      )) : (
        <EmptyState
          title="لسه مفيش تقييمات"
          body="بعد أول طلب يتم توصيله تقدر تقيّم تجربتك من تفاصيل الطلب."
        />
      )}
    </Screen>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <View style={s.metric}>
      <Text style={s.metricValue}>{value}</Text>
      <Text style={s.metricLabel}>{label}</Text>
    </View>
  );
}

const s = StyleSheet.create({
  header: {
    flexDirection: "row-reverse",
    alignItems: "center",
    gap: 12,
    paddingTop: 14,
    paddingBottom: 18,
  },
  back: { fontSize: 26 },
  title: {
    flex: 1,
    fontSize: 22,
    fontWeight: "900",
    color: colors.ink,
    textAlign: "right",
  },
  card: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    backgroundColor: colors.surface,
    padding: 14,
    marginBottom: 12,
  },
  row: {
    flexDirection: "row-reverse",
    alignItems: "center",
    gap: 12,
  },
  order: {
    fontWeight: "900",
    color: colors.ink,
    textAlign: "right",
  },
  date: {
    fontSize: 10,
    color: colors.muted,
    textAlign: "right",
    marginTop: 3,
  },
  rating: {
    color: "#D78C20",
    fontSize: 16,
    fontWeight: "900",
  },
  metrics: {
    flexDirection: "row-reverse",
    gap: 6,
    marginTop: 12,
  },
  metric: {
    flex: 1,
    alignItems: "center",
    backgroundColor: colors.soft,
    borderRadius: 12,
    paddingVertical: 8,
  },
  metricValue: {
    fontWeight: "900",
    color: colors.orangeDark,
  },
  metricLabel: {
    fontSize: 9,
    color: colors.muted,
    marginTop: 2,
  },
  comment: {
    color: colors.muted,
    fontSize: 12,
    lineHeight: 19,
    textAlign: "right",
    writingDirection: "rtl",
    marginTop: 12,
  },
  edit: {
    color: colors.orangeDark,
    fontWeight: "800",
    fontSize: 11,
    textAlign: "right",
    marginTop: 10,
  },
});
