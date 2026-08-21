import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { PricingQuote } from "../api/types";
import { colors, radius, spacing } from "../theme/tokens";
import { egp } from "../utils/format";

export function PriceSummary({ quote }: { quote: PricingQuote }) {
  return <View style={s.card}>
    <Row label="إجمالي الأكل" value={egp(quote.subtotal_minor)}/>
    <Row label="التوصيل" value={egp(quote.delivery_fee_minor)}/>
    {quote.coupon_discount_minor > 0 ? <Row label="خصم الكوبون" value={`− ${egp(quote.coupon_discount_minor)}`} discount/> : null}
    {quote.subscription_discount_minor > 0 ? <Row label="خصم الاشتراك" value={`− ${egp(quote.subscription_discount_minor)}`} discount/> : null}
    {quote.loyalty_discount_minor > 0 ? <Row label="نقاط بيتنا" value={`− ${egp(quote.loyalty_discount_minor)}`} discount/> : null}
    <View style={s.divider}/>
    <Row label="المطلوب دفعه" value={egp(quote.total_minor)} total/>
  </View>;
}
function Row({label,value,discount,total}:{label:string;value:string;discount?:boolean;total?:boolean}){return <View style={s.row}><Text style={[s.label,total&&s.totalLabel]}>{label}</Text><Text style={[s.value,discount&&s.discount,total&&s.totalValue]}>{value}</Text></View>}
const s=StyleSheet.create({card:{borderWidth:1,borderColor:colors.border,borderRadius:radius.md,backgroundColor:colors.surface,padding:spacing.md,gap:9},row:{flexDirection:"row-reverse",justifyContent:"space-between",alignItems:"center"},label:{color:colors.muted,textAlign:"right",writingDirection:"rtl"},value:{color:colors.ink,fontWeight:"700"},discount:{color:colors.greenDark},divider:{height:1,backgroundColor:colors.border,marginVertical:3},totalLabel:{fontSize:16,fontWeight:"900",color:colors.ink},totalValue:{fontSize:18,fontWeight:"900",color:colors.orangeDark}});
