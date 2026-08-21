import React, { useEffect, useMemo, useState } from "react";
import { Pressable, StyleSheet, Text, TextInput, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Screen } from "../../src/ui/Screen";
import { PrimaryButton } from "../../src/ui/PrimaryButton";
import { ErrorState, LoadingState } from "../../src/ui/StateViews";
import { useChef, useSignatureMenu } from "../../src/hooks/useCustomerHome";
import { useChefAvailability } from "../../src/hooks/usePostOrder";
import { customerApi } from "../../src/api";
import { queryKeys } from "../../src/query/keys";
import { egp } from "../../src/utils/format";
import { colors, radius, spacing } from "../../src/theme/tokens";

export default function NewSpecialOrderScreen() {
  const params = useLocalSearchParams<{ chefId: string; dishId: string }>();
  const chefId = String(params.chefId ?? "");
  const dishId = String(params.dishId ?? "");

  const chef = useChef(chefId);
  const menu = useSignatureMenu(chefId);
  const availability = useChefAvailability(chefId);
  const dish = menu.data?.find((x) => x.id === dishId);
  const qc = useQueryClient();

  const earliestServiceDate = useMemo(() => {
    const days = Math.ceil((dish?.prep_notice_hours ?? 0) / 24);
    const d = new Date();
    d.setHours(12, 0, 0, 0);
    d.setDate(d.getDate() + days);
    return d.toISOString().slice(0, 10);
  }, [dish?.prep_notice_hours]);

  const availableDays = useMemo(
    () => availability.data?.filter((x) => x.is_available && x.service_date >= earliestServiceDate) ?? [],
    [availability.data, earliestServiceDate],
  );

  const [selectedDate, setSelectedDate] = useState("");
  const [quantity, setQuantity] = useState(1);
  const [requestType, setRequestType] = useState<"special" | "preorder">("special");
  const [note, setNote] = useState("");

  useEffect(() => {
    if (!selectedDate && availableDays[0]) {
      setSelectedDate(availableDays[0].service_date);
    }
  }, [availableDays, selectedDate]);

  const selected = availableDays.find((x) => x.service_date === selectedDate);

  const create = useMutation({
    mutationFn: () => customerApi.createSpecialOrder({
      dish_id: dishId,
      request_type: requestType,
      quantity,
      requested_service_date: selectedDate,
      requested_window_start: selected?.delivery_window_start ?? null,
      requested_window_end: selected?.delivery_window_end ?? null,
      customer_note: note.trim() || null,
    }),
    onSuccess: async (specialOrder) => {
      await qc.invalidateQueries({ queryKey: queryKeys.specialOrders });
      router.replace(`/special-orders/${specialOrder.id}`);
    },
  });

  if (chef.isLoading || menu.isLoading || availability.isLoading) {
    return <Screen><LoadingState label="بنراجع مواعيد الشيف..." /></Screen>;
  }
  if (chef.isError || menu.isError || availability.isError || !dish) {
    return <Screen><ErrorState message="تعذر تجهيز الطلب الخاص." /></Screen>;
  }
  if (!dish.is_special_order_available) {
    return <Screen><ErrorState message="هذا الطبق غير متاح كطلب خاص." /></Screen>;
  }

  return (
    <Screen>
      <View style={s.header}>
        <Text onPress={() => router.back()} style={s.back}>→</Text>
        <Text style={s.title}>طلب خاص</Text>
      </View>

      <View style={s.dish}>
        <View style={s.icon}><Text style={s.iconText}>🥘</Text></View>
        <View style={{ flex: 1 }}>
          <Text style={s.name}>{dish.name}</Text>
          <Text style={s.meta}>من {chef.data?.display_name}</Text>
          <Text style={s.meta}>يحتاج تحضير مسبق {dish.prep_notice_hours} ساعة</Text>
        </View>
        <Text style={s.price}>{egp(dish.base_price_minor)}</Text>
      </View>

      <Text style={s.section}>نوع الطلب</Text>
      <View style={s.choiceRow}>
        <Choice label="طلب خاص" active={requestType === "special"} onPress={() => setRequestType("special")} />
        <Choice label="طلب مسبق" active={requestType === "preorder"} onPress={() => setRequestType("preorder")} />
      </View>

      <Text style={s.section}>اختار يوم متاح</Text>
      {availableDays.length ? (
        <View style={s.days}>
          {availableDays.slice(0, 14).map((day) => (
            <Pressable
              key={day.service_date}
              onPress={() => setSelectedDate(day.service_date)}
              style={[s.day, selectedDate === day.service_date && s.dayActive]}
            >
              <Text style={[s.dayText, selectedDate === day.service_date && s.dayTextActive]}>
                {new Date(day.service_date).toLocaleDateString("ar-EG", {
                  weekday: "short",
                  day: "numeric",
                  month: "short",
                })}
              </Text>
              <Text style={s.capacity}>{day.capacity_remaining} متاح</Text>
            </Pressable>
          ))}
        </View>
      ) : (
        <View style={s.warning}>
          <Text style={s.warningTitle}>مفيش مواعيد منشورة حاليًا</Text>
          <Text style={s.warningText}>ارجع لاحقًا أو اختار طبق تاني من الشيف.</Text>
        </View>
      )}

      {selected ? (
        <View style={s.window}>
          <Text style={s.windowTitle}>نافذة التوصيل</Text>
          <Text style={s.windowText}>
            {selected.delivery_window_start && selected.delivery_window_end
              ? `${selected.delivery_window_start} – ${selected.delivery_window_end}`
              : "سيتم تحديدها مع الشيف"}
          </Text>
        </View>
      ) : null}

      <Text style={s.section}>الكمية</Text>
      <View style={s.qty}>
        <Pressable onPress={() => setQuantity(Math.max(1, quantity - 1))} style={s.qtyBtn}><Text style={s.qtyBtnText}>−</Text></Pressable>
        <Text style={s.qtyValue}>{quantity}</Text>
        <Pressable onPress={() => setQuantity(Math.min(100, quantity + 1))} style={s.qtyBtn}><Text style={s.qtyBtnText}>+</Text></Pressable>
      </View>

      <Text style={s.section}>ملاحظة للشيف</Text>
      <TextInput
        value={note}
        onChangeText={setNote}
        placeholder="مثال: بدون فلفل حار..."
        placeholderTextColor="#A2968C"
        multiline
        maxLength={2000}
        style={s.input}
        textAlign="right"
      />

      <View style={s.summary}>
        <Text style={s.summaryLabel}>السعر المبدئي</Text>
        <Text style={s.summaryValue}>{egp(dish.base_price_minor * quantity)}</Text>
        <Text style={s.summaryNote}>
          الشيف ممكن توافق بنفس السعر أو تبعت عرض بديل بموعد/سعر جديد قبل الدفع.
        </Text>
      </View>

      {create.isError ? <Text style={s.error}>{create.error instanceof Error ? create.error.message : "تعذر إرسال الطلب الخاص."}</Text> : null}
      <PrimaryButton
        label="إرسال الطلب للشيف"
        onPress={() => create.mutate()}
        loading={create.isPending}
        disabled={!selectedDate}
      />
    </Screen>
  );
}

function Choice({ label, active, onPress }: { label: string; active: boolean; onPress(): void }) {
  return (
    <Pressable onPress={onPress} style={[s.choice, active && s.choiceActive]}>
      <Text style={[s.choiceText, active && s.choiceTextActive]}>{label}</Text>
    </Pressable>
  );
}

const s = StyleSheet.create({
  header: { flexDirection: "row-reverse", alignItems: "center", gap: 12, paddingTop: 14, paddingBottom: 18 },
  back: { fontSize: 26 },
  title: { flex: 1, fontSize: 22, fontWeight: "900", color: colors.ink, textAlign: "right" },
  dish: { flexDirection: "row-reverse", gap: 12, alignItems: "center", borderWidth: 1, borderColor: colors.border, borderRadius: radius.md, padding: 13, backgroundColor: colors.surface },
  icon: { width: 58, height: 58, borderRadius: 17, backgroundColor: colors.orangeSoft, alignItems: "center", justifyContent: "center" },
  iconText: { fontSize: 29 },
  name: { fontWeight: "900", color: colors.ink, textAlign: "right", writingDirection: "rtl" },
  meta: { color: colors.muted, fontSize: 10, marginTop: 3, textAlign: "right", writingDirection: "rtl" },
  price: { color: colors.orangeDark, fontWeight: "900" },
  section: { fontSize: 15, fontWeight: "900", color: colors.ink, textAlign: "right", writingDirection: "rtl", marginTop: 19, marginBottom: 8 },
  choiceRow: { flexDirection: "row-reverse", gap: 8 },
  choice: { flex: 1, alignItems: "center", borderWidth: 1, borderColor: colors.border, borderRadius: radius.md, paddingVertical: 11 },
  choiceActive: { backgroundColor: colors.orangeSoft, borderColor: colors.orange },
  choiceText: { color: colors.muted, fontSize: 11 },
  choiceTextActive: { color: colors.orangeDark, fontWeight: "900" },
  days: { flexDirection: "row-reverse", flexWrap: "wrap", gap: 7 },
  day: { minWidth: "30%", borderWidth: 1, borderColor: colors.border, borderRadius: 13, padding: 9, backgroundColor: colors.surface, alignItems: "center" },
  dayActive: { borderColor: colors.orange, backgroundColor: colors.orangeSoft },
  dayText: { fontSize: 10, color: colors.ink },
  dayTextActive: { color: colors.orangeDark, fontWeight: "900" },
  capacity: { fontSize: 8, color: colors.muted, marginTop: 3 },
  window: { marginTop: 10, backgroundColor: colors.greenSoft, borderRadius: radius.md, padding: 12 },
  windowTitle: { color: colors.greenDark, fontWeight: "900", textAlign: "right" },
  windowText: { color: colors.muted, fontSize: 11, marginTop: 3, textAlign: "right" },
  warning: { backgroundColor: colors.orangeSoft, borderRadius: radius.md, padding: 14 },
  warningTitle: { fontWeight: "900", color: colors.orangeDark, textAlign: "right" },
  warningText: { fontSize: 11, color: colors.muted, marginTop: 4, textAlign: "right", writingDirection: "rtl" },
  qty: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 20 },
  qtyBtn: { width: 40, height: 40, borderRadius: 12, borderWidth: 1, borderColor: colors.border, alignItems: "center", justifyContent: "center", backgroundColor: colors.surface },
  qtyBtnText: { fontSize: 23, color: colors.ink },
  qtyValue: { fontSize: 21, fontWeight: "900", minWidth: 30, textAlign: "center" },
  input: { minHeight: 90, borderWidth: 1, borderColor: colors.border, borderRadius: radius.md, backgroundColor: colors.surface, padding: 12, textAlignVertical: "top", writingDirection: "rtl" },
  summary: { marginVertical: 16, borderRadius: radius.md, backgroundColor: colors.soft, padding: 14 },
  summaryLabel: { fontSize: 10, color: colors.muted, textAlign: "right" },
  summaryValue: { fontSize: 20, fontWeight: "900", color: colors.orangeDark, textAlign: "right", marginTop: 3 },
  summaryNote: { fontSize: 10, color: colors.muted, lineHeight: 17, textAlign: "right", writingDirection: "rtl", marginTop: 5 },
  error: { color: colors.danger, textAlign: "center", marginBottom: 8 },
});
