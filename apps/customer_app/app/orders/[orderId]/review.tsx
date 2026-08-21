import React, { useEffect, useState } from "react";
import { StyleSheet, Text, TextInput, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Screen } from "../../../src/ui/Screen";
import { PrimaryButton } from "../../../src/ui/PrimaryButton";
import { ErrorState, LoadingState } from "../../../src/ui/StateViews";
import { StarRating } from "../../../src/ui/StarRating";
import { customerApi } from "../../../src/api";
import { ReviewInput } from "../../../src/api/types";
import { useReviewEligibility } from "../../../src/hooks/usePostOrder";
import { queryKeys } from "../../../src/query/keys";
import { colors, radius, spacing } from "../../../src/theme/tokens";

const INITIAL: ReviewInput = {
  food_quality: 5,
  packaging: 5,
  order_accuracy: 5,
  value_for_money: 5,
  chef_overall: 5,
  delivery_overall: 5,
  comment: null,
};

export default function ReviewOrderScreen() {
  const { orderId } = useLocalSearchParams<{ orderId: string }>();
  const id = String(orderId ?? "");
  const eligibility = useReviewEligibility(id);
  const qc = useQueryClient();
  const [form, setForm] = useState<ReviewInput>(INITIAL);
  const [comment, setComment] = useState("");

  useEffect(() => {
    const existing = eligibility.data?.review;
    if (existing) {
      setForm({
        food_quality: existing.food_quality,
        packaging: existing.packaging,
        order_accuracy: existing.order_accuracy,
        value_for_money: existing.value_for_money,
        chef_overall: existing.chef_overall,
        delivery_overall: existing.delivery_overall,
        comment: existing.comment,
      });
      setComment(existing.comment ?? "");
    }
  }, [eligibility.data?.review]);

  const save = useMutation({
    mutationFn: async () => {
      const payload: ReviewInput = {
        ...form,
        comment: comment.trim() || null,
      };
      const existing = eligibility.data?.review;
      return existing
        ? customerApi.updateReview(existing.id, payload)
        : customerApi.createReview(id, payload);
    },
    onSuccess: async () => {
      await Promise.all([
        qc.invalidateQueries({ queryKey: queryKeys.reviewEligibility(id) }),
        qc.invalidateQueries({ queryKey: queryKeys.myReviews }),
        qc.invalidateQueries({ queryKey: queryKeys.order(id) }),
      ]);
      router.back();
    },
  });

  if (eligibility.isLoading) {
    return <Screen><LoadingState label="بنجهز التقييم..." /></Screen>;
  }
  if (eligibility.isError || !eligibility.data) {
    return <Screen><ErrorState message="تعذر تحميل حالة التقييم." /></Screen>;
  }
  if (!eligibility.data.can_review) {
    return (
      <Screen>
        <Header title="تقييم الطلب" />
        <ErrorState message="يمكن تقييم الطلب بعد اكتمال التوصيل فقط." />
      </Screen>
    );
  }

  const existing = eligibility.data.review;

  return (
    <Screen>
      <Header title={existing ? "تعديل التقييم" : "قيّم تجربتك"} />

      <View style={s.hero}>
        <Text style={s.heroEmoji}>⭐</Text>
        <Text style={s.heroTitle}>
          {existing ? "تقدر تعدّل تقييمك" : "رأيك بيساعدنا نحسّن التجربة"}
        </Text>
        <Text style={s.heroText}>
          قيّم كل جزء لوحده علشان الشيف وفريق بيتنا يعرفوا إيه اللي ممتاز وإيه اللي محتاج يتحسن.
        </Text>
      </View>

      <View style={s.card}>
        <StarRating label="جودة الأكل" value={form.food_quality} onChange={(v) => v && setForm({ ...form, food_quality: v })} />
        <StarRating label="التغليف" value={form.packaging} onChange={(v) => v && setForm({ ...form, packaging: v })} />
        <StarRating label="دقة الطلب" value={form.order_accuracy} onChange={(v) => v && setForm({ ...form, order_accuracy: v })} />
        <StarRating label="القيمة مقابل السعر" value={form.value_for_money} onChange={(v) => v && setForm({ ...form, value_for_money: v })} />
        <StarRating label="التقييم العام للشيف" value={form.chef_overall} onChange={(v) => v && setForm({ ...form, chef_overall: v })} />
        <StarRating label="التوصيل" value={form.delivery_overall} optional onChange={(v) => setForm({ ...form, delivery_overall: v })} />
      </View>

      <Text style={s.label}>تعليقك</Text>
      <TextInput
        value={comment}
        onChangeText={setComment}
        placeholder="اكتب تعليق مختصر يساعدنا..."
        placeholderTextColor="#A2968C"
        multiline
        maxLength={1500}
        style={s.input}
        textAlign="right"
      />

      {save.isError ? (
        <Text style={s.error}>تعذر حفظ التقييم. حاول مرة أخرى.</Text>
      ) : null}

      <PrimaryButton
        label={existing ? "حفظ التعديلات" : "إرسال التقييم"}
        onPress={() => save.mutate()}
        loading={save.isPending}
      />
    </Screen>
  );
}

function Header({ title }: { title: string }) {
  return (
    <View style={s.header}>
      <Text onPress={() => router.back()} style={s.back}>→</Text>
      <Text style={s.title}>{title}</Text>
    </View>
  );
}

const s = StyleSheet.create({
  header: {
    flexDirection: "row-reverse",
    alignItems: "center",
    gap: 12,
    paddingTop: 14,
    paddingBottom: 16,
  },
  back: { fontSize: 26 },
  title: {
    flex: 1,
    fontSize: 22,
    fontWeight: "900",
    color: colors.ink,
    textAlign: "right",
    writingDirection: "rtl",
  },
  hero: {
    backgroundColor: colors.orangeSoft,
    borderRadius: radius.card,
    padding: 18,
    alignItems: "center",
    marginBottom: 14,
  },
  heroEmoji: { fontSize: 40 },
  heroTitle: {
    fontSize: 17,
    fontWeight: "900",
    color: colors.ink,
    marginTop: 5,
    textAlign: "center",
    writingDirection: "rtl",
  },
  heroText: {
    fontSize: 11,
    color: colors.muted,
    lineHeight: 18,
    textAlign: "center",
    writingDirection: "rtl",
    marginTop: 5,
  },
  card: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    backgroundColor: colors.surface,
    paddingHorizontal: 14,
  },
  label: {
    marginTop: 18,
    marginBottom: 7,
    fontWeight: "900",
    color: colors.ink,
    textAlign: "right",
    writingDirection: "rtl",
  },
  input: {
    minHeight: 110,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    backgroundColor: colors.surface,
    padding: 13,
    textAlignVertical: "top",
    writingDirection: "rtl",
    marginBottom: 14,
  },
  error: {
    color: colors.danger,
    textAlign: "center",
    marginBottom: 10,
    writingDirection: "rtl",
  },
});
