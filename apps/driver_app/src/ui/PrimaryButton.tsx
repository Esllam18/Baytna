import React from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text } from "react-native";
import { colors, radius } from "../theme/tokens";

export function PrimaryButton({
  label,onPress,disabled,loading,tone="primary",
}:{
  label:string;onPress():void;disabled?:boolean;loading?:boolean;
  tone?:"primary"|"success"|"danger"|"secondary";
}) {
  return <Pressable
    disabled={disabled||loading}
    onPress={onPress}
    style={({pressed})=>[
      s.button,
      tone==="success"&&s.success,
      tone==="danger"&&s.danger,
      tone==="secondary"&&s.secondary,
      (disabled||loading)&&s.disabled,
      pressed&&s.pressed,
    ]}
  >
    {loading?<ActivityIndicator color={tone==="secondary"?colors.orangeDark:"#fff"}/>:<Text style={[s.text,tone==="secondary"&&s.secondaryText]}>{label}</Text>}
  </Pressable>;
}
const s=StyleSheet.create({
  button:{minHeight:50,borderRadius:radius.md,backgroundColor:colors.orange,alignItems:"center",justifyContent:"center",paddingHorizontal:16},
  success:{backgroundColor:colors.greenDark},
  danger:{backgroundColor:colors.danger},
  secondary:{backgroundColor:colors.orangeSoft,borderWidth:1,borderColor:"#F0B878"},
  text:{color:"#fff",fontWeight:"900",fontSize:14,writingDirection:"rtl"},
  secondaryText:{color:colors.orangeDark},
  disabled:{opacity:.45},pressed:{opacity:.82},
});
