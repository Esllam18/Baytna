import { useQuery } from "@tanstack/react-query";
import { customerApi } from "../api";
import { queryKeys } from "../query/keys";

export function useCart() {
  return useQuery({ queryKey: queryKeys.cart, queryFn: () => customerApi.cart() });
}

export function useAddresses() {
  return useQuery({ queryKey: queryKeys.addresses, queryFn: () => customerApi.addresses() });
}

export function useLoyalty() {
  return useQuery({ queryKey: queryKeys.loyalty, queryFn: () => customerApi.loyalty() });
}

export function useOrders() {
  return useQuery({ queryKey: queryKeys.orders, queryFn: () => customerApi.orders() });
}

export function useOrder(orderId: string) {
  return useQuery({
    queryKey: queryKeys.order(orderId),
    queryFn: () => customerApi.order(orderId),
    enabled: Boolean(orderId),
  });
}

export function useLiveOrderTracking(orderId: string) {
  return useQuery({
    queryKey: queryKeys.tracking(orderId),
    queryFn: () => customerApi.liveTracking(orderId),
    enabled: Boolean(orderId),
    refetchInterval: (query) => {
      const status = query.state.data?.fulfillment.status;
      return status === "delivered" || status === "cancelled" || status === "expired" ? false : 10_000;
    },
  });
}
