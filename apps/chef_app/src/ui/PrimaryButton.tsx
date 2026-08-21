import React from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text } from "react-native";
import { colors, radius } from "../theme/tokens";

export function PrimaryButton({
  label,
  onPress,
  disabled,
  loading,
  tone = "primary",
}: {
  label: string;
  onPress(): void;
  disabled?: boolean;
  loading?: boolean;
  tone?: "primary" | "danger" | "success";
}) {
  return (
    <Pressable
      disabled={disabled || loading}
      onPress={onPress}
      style={({pressed})=>[
        s.button,
        tone==="danger" && s.danger,
        tone==="success" && s.success,
        (disabled||loading)&&s.disabled,
        pressed&&s.pressed,
      ]}
    >
      {loading ? <ActivityIndicator color="#fff"/> : <Text style={s.text}>{label}</Text>}
    </Pressable>
  );
}
const s=StyleSheet.create({
  button:{minHeight:50,borderRadius:radius.md,backgroundColor:colors.orange,alignItems:"center",justifyContent:"center",paddingHorizontal:16},
  danger:{backgroundColor:colors.danger},
  success:{backgroundColor:colors.greenDark},
  text:{color:"#fff",fontWeight:"900",fontSize:14,writingDirection:"rtl"},
  disabled:{opacity:.45},
  pressed:{opacity:.8},
});
