import React from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from "react-native";
import { CartLine } from "../api/types";
import { colors, radius, spacing } from "../theme/tokens";
import { egp } from "../utils/format";

export function CartLineItem({ item, busy, onQuantity, onRemove }: {
  item: CartLine;
  busy?: boolean;
  onQuantity(quantity: number): void;
  onRemove(): void;
}) {
  return <View style={s.card}>
    <View style={s.icon}><Text style={s.emoji}>🍲</Text></View>
    <View style={s.body}>
      <Text style={s.name}>{item.dish_name}</Text>
      <Text style={s.price}>{egp(item.unit_price_minor)} × {item.quantity}</Text>
      <View style={s.actions}>
        <Pressable disabled={busy || item.quantity <= 1} onPress={() => onQuantity(item.quantity - 1)} style={s.qty}><Text style={s.qtyText}>−</Text></Pressable>
        <Text style={s.count}>{item.quantity}</Text>
        <Pressable disabled={busy} onPress={() => onQuantity(item.quantity + 1)} style={s.qty}><Text style={s.qtyText}>+</Text></Pressable>
        <Pressable disabled={busy} onPress={onRemove} style={s.remove}><Text style={s.removeText}>حذف</Text></Pressable>
      </View>
    </View>
    <View style={s.totalWrap}>{busy ? <ActivityIndicator color={colors.orange}/> : <Text style={s.total}>{egp(item.line_total_minor)}</Text>}</View>
  </View>;
}
const s=StyleSheet.create({card:{minHeight:112,borderWidth:1,borderColor:colors.border,borderRadius:radius.md,backgroundColor:colors.surface,padding:12,flexDirection:"row-reverse",gap:12,alignItems:"center",marginBottom:12},icon:{width:64,height:64,borderRadius:16,backgroundColor:colors.orangeSoft,alignItems:"center",justifyContent:"center"},emoji:{fontSize:32},body:{flex:1},name:{fontSize:15,fontWeight:"900",color:colors.ink,textAlign:"right",writingDirection:"rtl"},price:{fontSize:11,color:colors.muted,textAlign:"right",marginTop:4},actions:{flexDirection:"row-reverse",alignItems:"center",gap:8,marginTop:10},qty:{width:30,height:30,borderRadius:9,borderWidth:1,borderColor:colors.border,alignItems:"center",justifyContent:"center"},qtyText:{fontSize:18,color:colors.ink},count:{fontWeight:"900",minWidth:20,textAlign:"center"},remove:{marginRight:8,paddingHorizontal:8,paddingVertical:5},removeText:{fontSize:11,color:colors.danger,fontWeight:"800"},totalWrap:{minWidth:72,alignItems:"flex-start"},total:{fontSize:14,fontWeight:"900",color:colors.orangeDark}});
