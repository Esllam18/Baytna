import React,{useState} from "react";
import {Pressable,StyleSheet,Text,View} from "react-native";
import {router} from "expo-router";
import {Screen} from "../../src/ui/Screen";
import {BottomNav} from "../../src/ui/BottomNav";
import {EmptyState,ErrorState,LoadingState} from "../../src/ui/StateViews";
import {useChefSpecialOrders} from "../../src/hooks/useChefOps";
import {egp} from "../../src/utils/format";
import {colors,radius} from "../../src/theme/tokens";

const filters=[["all","الكل"],["chef_review","تحتاج رد"],["counter_offer","عرض بديل"],["awaiting_payment","انتظار الدفع"],["scheduled","مجدولة"]] as const;
const labels:Record<string,string>={chef_review:"تحتاج مراجعة",counter_offer:"بانتظار العميل",awaiting_payment:"بانتظار الدفع",scheduled:"مجدولة",rejected:"مرفوضة",cancelled:"ملغية",expired:"منتهية"};

export default function ChefSpecialOrdersScreen(){
  const [filter,setFilter]=useState("all");
  const q=useChefSpecialOrders(filter==="all"?undefined:filter);
  return <View style={s.page}>
    <Screen>
      <View style={s.header}><Text style={s.title}>الطلبات الخاصة</Text><Text onPress={()=>router.push("/schedule")} style={s.schedule}>الجدول الأسبوعي</Text></View>
      <View style={s.filters}>{filters.map(([key,label])=><Pressable key={key} onPress={()=>setFilter(key)} style={[s.filter,filter===key&&s.filterActive]}><Text style={[s.filterText,filter===key&&s.filterTextActive]}>{label}</Text></Pressable>)}</View>
      {q.isLoading?<LoadingState label="بنجيب الطلبات الخاصة..."/>:
       q.isError?<ErrorState message="تعذر تحميل الطلبات الخاصة."/>:
       q.data?.length?q.data.map(x=><Pressable key={x.id} onPress={()=>router.push(`/special-orders/${x.id}`)} style={s.card}>
        <View style={s.row}><View style={{flex:1}}><Text style={s.name}>{x.dish_name}</Text><Text style={s.meta}>{x.quantity} × {new Date(x.requested_service_date).toLocaleDateString("ar-EG")} • {x.request_type==="preorder"?"طلب مسبق":"طلب خاص"}</Text></View>
        <View style={[s.badge,x.status==="chef_review"&&s.badgeAction,x.status==="scheduled"&&s.badgeDone]}><Text style={s.badgeText}>{labels[x.status]??x.status}</Text></View></View>
        <View style={s.footer}><Text style={s.price}>{egp(x.final_total_minor??x.requested_unit_price_minor*x.quantity)}</Text>{x.customer_note?<Text numberOfLines={1} style={s.note}>{x.customer_note}</Text>:null}</View>
       </Pressable>):<EmptyState title="مفيش طلبات خاصة" body="الطلبات الجديدة هتظهر هنا فور إرسال العميل."/>}
    </Screen><BottomNav active="special"/>
  </View>;
}
const s=StyleSheet.create({
 page:{flex:1,backgroundColor:colors.canvas},header:{flexDirection:"row-reverse",alignItems:"center",paddingTop:10,paddingBottom:12},title:{flex:1,fontSize:23,fontWeight:"900",color:colors.ink,textAlign:"right"},schedule:{fontSize:10,fontWeight:"900",color:colors.orangeDark},
 filters:{flexDirection:"row-reverse",flexWrap:"wrap",gap:7,marginBottom:14},filter:{paddingHorizontal:11,paddingVertical:8,borderRadius:radius.pill,backgroundColor:colors.soft},filterActive:{backgroundColor:colors.orangeSoft},filterText:{fontSize:10,color:colors.muted},filterTextActive:{color:colors.orangeDark,fontWeight:"900"},
 card:{borderWidth:1,borderColor:colors.border,borderRadius:radius.md,backgroundColor:colors.surface,padding:14,marginBottom:10},row:{flexDirection:"row-reverse",alignItems:"center",gap:10},name:{fontWeight:"900",color:colors.ink,textAlign:"right",writingDirection:"rtl"},meta:{fontSize:10,color:colors.muted,textAlign:"right",marginTop:3},
 badge:{borderRadius:radius.pill,backgroundColor:colors.soft,paddingHorizontal:9,paddingVertical:6},badgeAction:{backgroundColor:colors.orangeSoft},badgeDone:{backgroundColor:colors.greenSoft},badgeText:{fontSize:9,fontWeight:"900",color:colors.ink},
 footer:{flexDirection:"row-reverse",justifyContent:"space-between",borderTopWidth:1,borderTopColor:colors.border,paddingTop:9,marginTop:10},price:{fontWeight:"900",color:colors.orangeDark},note:{flex:1,fontSize:9,color:colors.muted,textAlign:"left",marginLeft:8}
});
