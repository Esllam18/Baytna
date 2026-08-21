import { useQuery } from "@tanstack/react-query";
import { customerApi } from "../api";
import { queryKeys } from "../query/keys";
export function useCustomerHome(){return useQuery({queryKey:queryKeys.home,queryFn:()=>customerApi.home()});}
export function useChefs(area?:string,openToday?:boolean){return useQuery({queryKey:queryKeys.chefs(area,openToday),queryFn:()=>customerApi.chefs(area,openToday)});}
export function useChef(chefId:string){return useQuery({queryKey:queryKeys.chef(chefId),queryFn:()=>customerApi.chef(chefId),enabled:Boolean(chefId)});}
export function useTodayMenu(chefId:string){return useQuery({queryKey:queryKeys.todayMenu(chefId),queryFn:()=>customerApi.todayMenu(chefId),enabled:Boolean(chefId)});}
export function useSignatureMenu(chefId:string){return useQuery({queryKey:queryKeys.signatureMenu(chefId),queryFn:()=>customerApi.signatureMenu(chefId),enabled:Boolean(chefId)});}
