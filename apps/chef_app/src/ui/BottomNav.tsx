import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { router } from "expo-router";
import { colors } from "../theme/tokens";

const items = [
  {key:"home",label:"الرئيسية",icon:"⌂",href:"/home"},
  {key:"kitchen",label:"مطبخ اليوم",icon:"☕",href:"/kitchen"},
  {key:"orders",label:"الطلبات",icon:"▤",href:"/orders"},
  {key:"special",label:"الطلبات الخاصة",icon:"★",href:"/special-orders"},
] as const;

export function BottomNav({active}:{active:string}) {
  return <View style={s.nav}>
    {items.map(item=><Pressable key={item.key} onPress={()=>router.push(item.href as never)} style={s.item}>
      <Text style={[s.icon,active===item.key&&s.active]}>{item.icon}</Text>
      <Text style={[s.label,active===item.key&&s.active]}>{item.label}</Text>
    </Pressable>)}
  </View>;
}
const s=StyleSheet.create({
  nav:{position:"absolute",left:0,right:0,bottom:0,height:78,backgroundColor:"#fff",borderTopWidth:1,borderTopColor:colors.border,flexDirection:"row-reverse",justifyContent:"space-around",paddingTop:9},
  item:{alignItems:"center",flex:1},
  icon:{fontSize:20,color:colors.muted},
  label:{fontSize:9,color:colors.muted,marginTop:4},
  active:{color:colors.orangeDark,fontWeight:"900"},
});
