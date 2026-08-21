import { useQuery } from "@tanstack/react-query";
import { customerApi } from "../api";
import { queryKeys } from "../query/keys";

export function useReviewEligibility(orderId: string) {
  return useQuery({
    queryKey: queryKeys.reviewEligibility(orderId),
    queryFn: () => customerApi.reviewEligibility(orderId),
    enabled: Boolean(orderId),
  });
}

export function useMyReviews() {
  return useQuery({
    queryKey: queryKeys.myReviews,
    queryFn: () => customerApi.myReviews(),
  });
}

export function useChefReviews(chefId: string) {
  return useQuery({
    queryKey: queryKeys.chefReviews(chefId),
    queryFn: () => customerApi.chefReviews(chefId),
    enabled: Boolean(chefId),
  });
}

export function useChefRatingSummary(chefId: string) {
  return useQuery({
    queryKey: queryKeys.chefRatingSummary(chefId),
    queryFn: () => customerApi.chefRatingSummary(chefId),
    enabled: Boolean(chefId),
  });
}

export function useChefAvailability(chefId: string) {
  return useQuery({
    queryKey: queryKeys.chefAvailability(chefId),
    queryFn: () => customerApi.chefAvailability(chefId, 30),
    enabled: Boolean(chefId),
  });
}

export function useSpecialOrders() {
  return useQuery({
    queryKey: queryKeys.specialOrders,
    queryFn: () => customerApi.specialOrders(),
  });
}

export function useSpecialOrder(specialOrderId: string) {
  return useQuery({
    queryKey: queryKeys.specialOrder(specialOrderId),
    queryFn: () => customerApi.specialOrder(specialOrderId),
    enabled: Boolean(specialOrderId),
    refetchInterval: 20_000,
  });
}
