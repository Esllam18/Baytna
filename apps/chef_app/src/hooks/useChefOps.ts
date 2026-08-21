import { useQuery } from "@tanstack/react-query";
import { chefApi } from "../api";
import { chefKeys } from "../query/keys";
import { localDateISO } from "../utils/date";

export function useChefProfile() {
  return useQuery({queryKey:chefKeys.profile,queryFn:()=>chefApi.profile()});
}
export function useChefDashboard(date=localDateISO()) {
  return useQuery({queryKey:chefKeys.dashboard(date),queryFn:()=>chefApi.dashboard(date),refetchInterval:20_000});
}
export function useSignatureMenu() {
  return useQuery({queryKey:chefKeys.signatureMenu,queryFn:()=>chefApi.signatureMenu(true)});
}
export function useTodayMenu(date=localDateISO()) {
  return useQuery({queryKey:chefKeys.todayMenu(date),queryFn:()=>chefApi.todayMenu(date)});
}
export function useChefOrders(stage?:string) {
  return useQuery({queryKey:chefKeys.orders(stage),queryFn:()=>chefApi.orders(stage),refetchInterval:15_000});
}
export function useChefOrder(id:string) {
  return useQuery({queryKey:chefKeys.order(id),queryFn:()=>chefApi.order(id),enabled:Boolean(id),refetchInterval:12_000});
}
export function useChefSpecialOrders(status?:string) {
  return useQuery({queryKey:chefKeys.specialOrders(status),queryFn:()=>chefApi.specialOrders(status),refetchInterval:20_000});
}
export function useChefSpecialOrder(id:string) {
  return useQuery({queryKey:chefKeys.specialOrder(id),queryFn:()=>chefApi.specialOrder(id),enabled:Boolean(id),refetchInterval:20_000});
}
export function useWeeklySchedule() {
  return useQuery({queryKey:chefKeys.schedule,queryFn:()=>chefApi.weeklySchedule()});
}
