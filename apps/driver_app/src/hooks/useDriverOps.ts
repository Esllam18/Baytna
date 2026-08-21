import { useQuery } from "@tanstack/react-query";
import { driverApi } from "../api";
import { driverKeys } from "../query/keys";

export function useDriverProfile() {
  return useQuery({queryKey:driverKeys.profile,queryFn:()=>driverApi.profile()});
}

export function useDriverDashboard() {
  return useQuery({
    queryKey:driverKeys.dashboard,
    queryFn:()=>driverApi.dashboard(),
    refetchInterval:12_000,
  });
}

export function useAvailableMissions(enabled=true) {
  return useQuery({
    queryKey:driverKeys.availableMissions,
    queryFn:()=>driverApi.availableMissions(),
    enabled,
    refetchInterval:10_000,
  });
}

export function useAvailableMission(id:string, enabled=true) {
  return useQuery({
    queryKey:driverKeys.availableMission(id),
    queryFn:()=>driverApi.availableMission(id),
    enabled:Boolean(id) && enabled,
    refetchInterval:8_000,
  });
}

export function useMission(id:string, enabled=true) {
  return useQuery({
    queryKey:driverKeys.mission(id),
    queryFn:()=>driverApi.mission(id),
    enabled:Boolean(id) && enabled,
    refetchInterval:8_000,
  });
}

export function useMissionHistory() {
  return useQuery({
    queryKey:driverKeys.history,
    queryFn:()=>driverApi.history(),
  });
}
