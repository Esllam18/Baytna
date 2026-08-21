import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { colors, radius, spacing } from "../theme/tokens";

export function OrderStatusCard({ title, detail, active = true }: { title: string; detail?: string | null; active?: boolean }) {
  return <View style={[s.card,!active&&s.inactive]}>
    <View style={[s.dot,active&&s.dotActive]}/>
    <View style={s.body}><Text style={s.title}>{title}</Text>{detail?<Text style={s.detail}>{detail}</Text>:null}</View>
  </View>;
}
const s=StyleSheet.create({card:{flexDirection:"row-reverse",alignItems:"center",gap:12,borderWidth:1,borderColor:colors.border,borderRadius:radius.md,backgroundColor:colors.surface,padding:14},inactive:{opacity:.55},dot:{width:12,height:12,borderRadius:6,backgroundColor:colors.border},dotActive:{backgroundColor:colors.orange},body:{flex:1},title:{fontWeight:"900",fontSize:15,color:colors.ink,textAlign:"right",writingDirection:"rtl"},detail:{fontSize:12,color:colors.muted,textAlign:"right",writingDirection:"rtl",marginTop:4,lineHeight:18}});
