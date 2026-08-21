import React from "react";
import { Pressable, StyleSheet, Text } from "react-native";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { customerApi } from "../api";
import { useFavoriteChefs, useFavoriteDishes } from "../hooks/useAccount";
import { queryKeys } from "../query/keys";
import { colors } from "../theme/tokens";

export function FavoriteButton({
  kind,
  id,
}: {
  kind: "chef" | "dish";
  id: string;
}) {
  const chefs = useFavoriteChefs();
  const dishes = useFavoriteDishes();
  const qc = useQueryClient();

  const isFavorite =
    kind === "chef"
      ? Boolean(chefs.data?.some((x) => x.chef_id === id))
      : Boolean(dishes.data?.some((x) => x.dish_id === id));

  const mutation = useMutation({
    mutationFn: async () => {
      if (kind === "chef") {
        return isFavorite
          ? customerApi.removeFavoriteChef(id)
          : customerApi.addFavoriteChef(id);
      }
      return isFavorite
        ? customerApi.removeFavoriteDish(id)
        : customerApi.addFavoriteDish(id);
    },
    onSuccess: async () => {
      await Promise.all([
        qc.invalidateQueries({ queryKey: queryKeys.favorites }),
        qc.invalidateQueries({ queryKey: queryKeys.favoriteChefs }),
        qc.invalidateQueries({ queryKey: queryKeys.favoriteDishes }),
      ]);
    },
  });

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={isFavorite ? "إزالة من المفضلة" : "إضافة للمفضلة"}
      disabled={mutation.isPending}
      onPress={() => mutation.mutate()}
      style={({ pressed }) => [s.button, pressed && s.pressed]}
    >
      <Text style={[s.heart, isFavorite && s.active]}>
        {isFavorite ? "♥" : "♡"}
      </Text>
    </Pressable>
  );
}

const s = StyleSheet.create({
  button: {
    position: "absolute",
    top: 18,
    left: 18,
    width: 42,
    height: 42,
    borderRadius: 21,
    backgroundColor: "rgba(255,255,255,.94)",
    alignItems: "center",
    justifyContent: "center",
  },
  heart: { fontSize: 25, color: colors.muted },
  active: { color: colors.orange },
  pressed: { opacity: 0.72 },
});
