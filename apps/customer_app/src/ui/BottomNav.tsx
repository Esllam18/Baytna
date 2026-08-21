import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { router } from "expo-router";
import { colors } from "../theme/tokens";

type ActiveTab = "home" | "chefs" | "orders" | "account";

export function BottomNav({ active }: { active: ActiveTab }) {
  return <View style={s.bar}>
    <Item label="الرئيسية" icon="⌂" active={active === "home"} onPress={() => router.replace('/home')} />
    <Item label="الشيفات" icon="♨" active={active === "chefs"} onPress={() => router.push('/chefs')} />
    <Item label="الطلبات" icon="▣" active={active === "orders"} onPress={() => router.push('/orders')} />
    <Item label="حسابي" icon="◯" active={active === "account"} onPress={() => router.push("/account")} />
  </View>;
}
function Item({ label, icon, active = false, onPress }: { label: string; icon: string; active?: boolean; onPress(): void }) {
  return <Pressable onPress={onPress} style={s.item}><Text style={[s.icon, active && s.active]}>{icon}</Text><Text style={[s.label, active && s.active]}>{label}</Text></Pressable>;
}
const s = StyleSheet.create({bar:{height:68,borderTopWidth:1,borderColor:colors.border,backgroundColor:colors.surface,flexDirection:"row-reverse",justifyContent:"space-around",paddingTop:6},item:{flex:1,alignItems:"center",justifyContent:"center"},icon:{fontSize:20,color:"#95887E"},label:{fontSize:10,color:"#95887E",marginTop:2},active:{color:colors.orange,fontWeight:"900"}});
