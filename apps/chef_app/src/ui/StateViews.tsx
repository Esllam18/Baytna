import React from "react";
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";
import { colors } from "../theme/tokens";

export function LoadingState({label="جاري التحميل..."}:{label?:string}) {
  return <View style={s.wrap}><ActivityIndicator/><Text style={s.text}>{label}</Text></View>;
}
export function ErrorState({message="حصلت مشكلة. حاول مرة أخرى."}:{message?:string}) {
  return <View style={s.wrap}><Text style={s.error}>⚠</Text><Text style={s.title}>{message}</Text></View>;
}
export function EmptyState({title,body}:{title:string;body?:string}) {
  return <View style={s.wrap}><Text style={s.empty}>○</Text><Text style={s.title}>{title}</Text>{body?<Text style={s.text}>{body}</Text>:null}</View>;
}
const s=StyleSheet.create({
  wrap:{paddingVertical:40,alignItems:"center",gap:8},
  title:{fontWeight:"900",color:colors.ink,textAlign:"center",writingDirection:"rtl"},
  text:{color:colors.muted,fontSize:11,textAlign:"center",writingDirection:"rtl"},
  error:{fontSize:30,color:colors.danger},
  empty:{fontSize:34,color:colors.muted},
});
