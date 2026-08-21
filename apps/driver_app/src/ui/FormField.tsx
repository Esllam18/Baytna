import React from "react";
import { StyleSheet, Text, TextInput, TextInputProps, View } from "react-native";
import { colors, radius } from "../theme/tokens";

export function FormField({label,...props}:TextInputProps & {label:string}) {
  return <View style={s.wrap}>
    <Text style={s.label}>{label}</Text>
    <TextInput
      {...props}
      textAlign="right"
      placeholderTextColor="#A2968C"
      style={[s.input,props.multiline&&s.multi]}
    />
  </View>;
}
const s=StyleSheet.create({
  wrap:{gap:6},
  label:{fontSize:12,fontWeight:"900",color:colors.ink,textAlign:"right",writingDirection:"rtl"},
  input:{minHeight:48,borderWidth:1,borderColor:colors.border,borderRadius:radius.md,backgroundColor:colors.surface,paddingHorizontal:13,color:colors.ink,writingDirection:"rtl"},
  multi:{minHeight:100,textAlignVertical:"top",paddingTop:12},
});
