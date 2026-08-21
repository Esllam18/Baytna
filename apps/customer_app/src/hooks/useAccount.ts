import { useQuery } from "@tanstack/react-query";
import { customerApi } from "../api";
import { queryKeys } from "../query/keys";

export function useProfile() {
  return useQuery({ queryKey: queryKeys.profile, queryFn: () => customerApi.profile() });
}
export function useFavoriteChefs() {
  return useQuery({ queryKey: queryKeys.favoriteChefs, queryFn: () => customerApi.favoriteChefs() });
}
export function useFavoriteDishes() {
  return useQuery({ queryKey: queryKeys.favoriteDishes, queryFn: () => customerApi.favoriteDishes() });
}
export function useNotifications(unreadOnly = false) {
  return useQuery({
    queryKey: [...queryKeys.notifications, unreadOnly],
    queryFn: () => customerApi.notifications(unreadOnly),
  });
}
export function useNotificationSummary() {
  return useQuery({
    queryKey: queryKeys.notificationSummary,
    queryFn: () => customerApi.notificationSummary(),
  });
}
export function useNotificationPreferences() {
  return useQuery({
    queryKey: queryKeys.notificationPreferences,
    queryFn: () => customerApi.notificationPreferences(),
  });
}
export function useSupportTickets() {
  return useQuery({
    queryKey: queryKeys.supportTickets,
    queryFn: () => customerApi.supportTickets(),
  });
}
export function useSupportTicket(ticketId: string) {
  return useQuery({
    queryKey: queryKeys.supportTicket(ticketId),
    queryFn: () => customerApi.supportTicket(ticketId),
    enabled: Boolean(ticketId),
    refetchInterval: 20_000,
  });
}
export function useSubscriptionPlans() {
  return useQuery({
    queryKey: queryKeys.subscriptionPlans,
    queryFn: () => customerApi.subscriptionPlans(),
  });
}
export function useCurrentSubscription() {
  return useQuery({
    queryKey: queryKeys.currentSubscription,
    queryFn: () => customerApi.currentSubscription(),
  });
}
