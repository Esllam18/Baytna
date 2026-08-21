import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { router } from "expo-router";
import { useOrders } from "../../src/hooks/useCommerce";
import { Screen } from "../../src/ui/Screen";
import { BottomNav } from "../../src/ui/BottomNav";
import { EmptyState, ErrorState, LoadingState } from "../../src/ui/StateViews";
import { colors, radius, spacing } from "../../src/theme/tokens";
import { egp } from "../../src/utils/format";

export default function OrdersScreen() {
  const q = useOrders();
  if (q.isLoading) return <Screen><LoadingState label="بنجيب طلباتك..."/></Screen>;
  if (q.isError) return <Screen><ErrorState message="تعذر تحميل الطلبات."/></Screen>;
  return <View style={s.page}><Screen><View style={s.header}><Text style={s.title}>طلباتي</Text></View>{q.data?.length ? q.data.map(order => <Pressable key={order.id} onPress={() => router.push(`/orders/${order.id}`)} style={s.card}><View style={s.row}><View><Text style={s.order}>طلب #{order.id.slice(0,8).toUpperCase()}</Text><Text style={s.date}>{new Date(order.created_at).toLocaleDateString('ar-EG')}</Text></View><Status status={order.status}/></View><View style={s.row}><Text style={s.meta}>تاريخ الخدمة {order.service_date}</Text><Text style={s.total}>{egp(order.total_minor)}</Text></View></Pressable>) : <EmptyState title="لسه مفيش طلبات" body="أول طلب من مطبخ بيتنا هيظهر هنا."/>}</Screen><BottomNav active="orders"/></View>;
}
function Status({status}:{status:string}){const labels:Record<string,string>={pending_payment:'بانتظار الدفع',confirmed:'تم التأكيد',accepted_by_chef:'الشيف قبلت',preparing:'جاري التجهيز',ready_for_pickup:'جاهز للاستلام',assigned_to_driver:'المندوب للشيف',picked_up:'المندوب استلم',out_for_delivery:'في الطريق',delivered:'تم التوصيل',cancelled:'ملغي',expired:'منتهي'};return <View style={s.status}><Text style={s.statusText}>{labels[status]??status}</Text></View>}
const s=StyleSheet.create({page:{flex:1,backgroundColor:colors.canvas},header:{paddingTop:14,paddingBottom:12},title:{fontSize:24,fontWeight:'900',color:colors.ink,textAlign:'right',writingDirection:'rtl'},card:{borderWidth:1,borderColor:colors.border,borderRadius:radius.md,backgroundColor:colors.surface,padding:14,marginBottom:12},row:{flexDirection:'row-reverse',justifyContent:'space-between',alignItems:'center',gap:12},order:{fontWeight:'900',color:colors.ink,textAlign:'right'},date:{fontSize:11,color:colors.muted,textAlign:'right',marginTop:3},status:{backgroundColor:colors.orangeSoft,borderRadius:radius.pill,paddingHorizontal:10,paddingVertical:6},statusText:{fontSize:10,fontWeight:'800',color:colors.orangeDark,writingDirection:'rtl'},meta:{fontSize:11,color:colors.muted,writingDirection:'rtl'},total:{fontWeight:'900',color:colors.orangeDark,marginTop:12}});
