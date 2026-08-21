import React, { useEffect, useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Screen } from "../../../src/ui/Screen";
import { AddressForm } from "../../../src/ui/AddressForm";
import { LoadingState, ErrorState } from "../../../src/ui/StateViews";
import { useAddresses } from "../../../src/hooks/useCommerce";
import { customerApi } from "../../../src/api";
import { AddressCreate } from "../../../src/api/types";
import { queryKeys } from "../../../src/query/keys";
import { colors } from "../../../src/theme/tokens";

export default function EditAddressScreen() {
  const { addressId } = useLocalSearchParams<{ addressId: string }>();
  const id = String(addressId ?? "");
  const addresses = useAddresses();
  const source = addresses.data?.find((x) => x.id === id);
  const [value, setValue] = useState<AddressCreate>({
    label: "", area: "6 أكتوبر", street: "", building: "", floor: "",
    apartment: "", latitude: null, longitude: null, is_default: false,
  });
  const qc = useQueryClient();

  useEffect(() => {
    if (source) {
      setValue({
        label: source.label, area: source.area, street: source.street,
        building: source.building, floor: source.floor, apartment: source.apartment,
        latitude: source.latitude, longitude: source.longitude, is_default: source.is_default,
      });
    }
  }, [source]);

  const save = useMutation({
    mutationFn: () => customerApi.updateAddress(id, value),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: queryKeys.addresses });
      router.back();
    },
  });

  if (addresses.isLoading) return <Screen><LoadingState /></Screen>;
  if (addresses.isError || !source) return <Screen><ErrorState message="العنوان غير موجود." /></Screen>;

  return (
    <Screen>
      <View style={s.header}><Text onPress={() => router.back()} style={s.back}>→</Text><Text style={s.title}>تعديل العنوان</Text></View>
      <AddressForm value={value} onChange={setValue} onSubmit={() => save.mutate()} loading={save.isPending} submitLabel="حفظ التعديلات" />
      {save.isError ? <Text style={s.error}>تعذر تعديل العنوان.</Text> : null}
    </Screen>
  );
}
const s=StyleSheet.create({header:{flexDirection:"row-reverse",alignItems:"center",gap:12,paddingTop:14,paddingBottom:18},back:{fontSize:26},title:{flex:1,fontSize:22,fontWeight:"900",color:colors.ink,textAlign:"right"},error:{color:colors.danger,textAlign:"right",marginTop:10}});
