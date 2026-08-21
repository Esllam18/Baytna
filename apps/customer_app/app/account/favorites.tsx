import React, { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { router } from "expo-router";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Screen } from "../../src/ui/Screen";
import { EmptyState, ErrorState, LoadingState } from "../../src/ui/StateViews";
import { useFavoriteChefs, useFavoriteDishes } from "../../src/hooks/useAccount";
import { customerApi } from "../../src/api";
import { queryKeys } from "../../src/query/keys";
import { egp } from "../../src/utils/format";
import { colors, radius, spacing } from "../../src/theme/tokens";

export default function FavoritesScreen() {
  const [tab, setTab] = useState<"chefs" | "dishes">("chefs");
  const chefs = useFavoriteChefs();
  const dishes = useFavoriteDishes();
  const qc = useQueryClient();

  const removeChef = useMutation({
    mutationFn: (id: string) => customerApi.removeFavoriteChef(id),
    onSuccess: () => Promise.all([
      qc.invalidateQueries({ queryKey: queryKeys.favoriteChefs }),
      qc.invalidateQueries({ queryKey: queryKeys.favorites }),
    ]),
  });
  const removeDish = useMutation({
    mutationFn: (id: string) => customerApi.removeFavoriteDish(id),
    onSuccess: () => Promise.all([
      qc.invalidateQueries({ queryKey: queryKeys.favoriteDishes }),
      qc.invalidateQueries({ queryKey: queryKeys.favorites }),
    ]),
  });

  const current = tab === "chefs" ? chefs : dishes;
  if (current.isLoading) return <Screen><LoadingState label="بنجيب المفضلة..." /></Screen>;
  if (current.isError) return <Screen><ErrorState message="تعذر تحميل المفضلة." /></Screen>;

  return (
    <Screen>
      <View style={s.header}><Text onPress={() => router.back()} style={s.back}>→</Text><Text style={s.title}>المفضلة</Text></View>
      <View style={s.tabs}>
        <Tab label={`الشيفات (${chefs.data?.length ?? 0})`} active={tab === "chefs"} onPress={() => setTab("chefs")} />
        <Tab label={`الأكلات (${dishes.data?.length ?? 0})`} active={tab === "dishes"} onPress={() => setTab("dishes")} />
      </View>

      {tab === "chefs" ? (
        chefs.data?.length ? chefs.data.map((chef) => (
          <Pressable key={chef.chef_id} onPress={() => router.push(`/chefs/${chef.chef_id}`)} style={s.card}>
            <View style={s.icon}><Text style={s.iconText}>👩‍🍳</Text></View>
            <View style={s.body}>
              <Text style={s.name}>{chef.display_name}</Text>
              <Text style={s.meta}>{chef.specialty} • {chef.area}</Text>
              <Text style={s.meta}>★ {chef.rating.toFixed(1)} {chef.is_verified ? "• موثّق" : ""}</Text>
            </View>
            <Text onPress={(e) => { e.stopPropagation(); removeChef.mutate(chef.chef_id); }} style={s.heart}>♥</Text>
          </Pressable>
        )) : <EmptyState title="مفيش شيفات في المفضلة" body="اضغط علامة القلب من صفحة أي شيف." />
      ) : (
        dishes.data?.length ? dishes.data.map((dish) => (
          <Pressable
            key={dish.dish_id}
            onPress={() => router.push({ pathname: "/chefs/[chefId]/dish/[dishId]", params: { chefId: dish.chef_id, dishId: dish.dish_id } })}
            style={s.card}
          >
            <View style={s.icon}><Text style={s.iconText}>🍲</Text></View>
            <View style={s.body}>
              <Text style={s.name}>{dish.name}</Text>
              <Text style={s.meta}>{dish.category}</Text>
              <Text style={s.price}>{egp(dish.base_price_minor)}</Text>
            </View>
            <Text onPress={(e) => { e.stopPropagation(); removeDish.mutate(dish.dish_id); }} style={s.heart}>♥</Text>
          </Pressable>
        )) : <EmptyState title="مفيش أكلات في المفضلة" body="احفظ الأكلات اللي نفسك ترجع لها بسرعة." />
      )}
    </Screen>
  );
}

function Tab({ label, active, onPress }: { label: string; active: boolean; onPress(): void }) {
  return <Pressable onPress={onPress} style={[s.tab, active && s.tabActive]}><Text style={[s.tabText, active && s.tabTextActive]}>{label}</Text></Pressable>;
}

const s = StyleSheet.create({
  header: { flexDirection: "row-reverse", alignItems: "center", gap: 12, paddingTop: 14, paddingBottom: 16 },
  back: { fontSize: 26 },
  title: { flex: 1, fontSize: 22, fontWeight: "900", textAlign: "right", color: colors.ink },
  tabs: { flexDirection: "row-reverse", gap: 8, marginBottom: 16 },
  tab: { flex: 1, borderRadius: radius.pill, backgroundColor: colors.soft, paddingVertical: 10, alignItems: "center" },
  tabActive: { backgroundColor: colors.orangeSoft },
  tabText: { color: colors.muted, fontSize: 12 },
  tabTextActive: { color: colors.orangeDark, fontWeight: "900" },
  card: { flexDirection: "row-reverse", alignItems: "center", gap: spacing.md, borderWidth: 1, borderColor: colors.border, borderRadius: radius.md, padding: 12, backgroundColor: colors.surface, marginBottom: 10 },
  icon: { width: 56, height: 56, borderRadius: 16, backgroundColor: colors.orangeSoft, alignItems: "center", justifyContent: "center" },
  iconText: { fontSize: 28 },
  body: { flex: 1 },
  name: { color: colors.ink, fontWeight: "900", textAlign: "right", writingDirection: "rtl" },
  meta: { color: colors.muted, fontSize: 11, marginTop: 3, textAlign: "right", writingDirection: "rtl" },
  price: { color: colors.orangeDark, fontWeight: "900", marginTop: 4, textAlign: "right" },
  heart: { fontSize: 24, color: colors.orange },
});
