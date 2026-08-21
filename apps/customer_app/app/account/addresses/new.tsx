import React, { useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import { router } from "expo-router";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Screen } from "../../../src/ui/Screen";
import { AddressForm } from "../../../src/ui/AddressForm";
import { customerApi } from "../../../src/api";
import { AddressCreate } from "../../../src/api/types";
import { queryKeys } from "../../../src/query/keys";
import { colors } from "../../../src/theme/tokens";

export default function NewAddressScreen() {
  const [value, setValue] = useState<AddressCreate>({ label: "", area: "6 أكتوبر", street: "", building: "", floor: "", apartment: "", latitude: null, longitude: null, is_default: false });
  const qc = useQueryClient();
  const mutation = useMutation({
    mutationFn: () => customerApi.createAddress(value),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: queryKeys.addresses });
      router.back();
    },
  });
  return <Screen><View style={s.header}><Text onPress={() => router.back()} style={s.back}>→</Text><Text style={s.title}>عنوان جديد</Text></View><AddressForm value={value} onChange={setValue} onSubmit={() => mutation.mutate()} loading={mutation.isPending} submitLabel="حفظ العنوان"/>{mutation.isError ? <Text style={s.error}>تعذر حفظ العنوان.</Text> : null}</Screen>;
}
const s = StyleSheet.create({header:{flexDirection:"row-reverse",alignItems:"center",gap:12,paddingTop:14,paddingBottom:18},back:{fontSize:26},title:{flex:1,fontSize:22,fontWeight:"900",color:colors.ink,textAlign:"right"},error:{color:colors.danger,textAlign:"right",marginTop:10}});
