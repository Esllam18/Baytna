import React from "react";
import { SafeAreaView, ScrollView, StyleSheet, ViewStyle } from "react-native";
import { colors, spacing } from "../theme/tokens";

export function Screen({children,contentStyle}:{children:React.ReactNode;contentStyle?:ViewStyle}) {
  return <SafeAreaView style={s.safe}>
    <ScrollView contentContainerStyle={[s.content,contentStyle]} keyboardShouldPersistTaps="handled">
      {children}
    </ScrollView>
  </SafeAreaView>;
}
const s=StyleSheet.create({
  safe:{flex:1,backgroundColor:colors.canvas},
  content:{padding:spacing.lg,paddingBottom:110},
});
