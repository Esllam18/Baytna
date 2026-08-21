import React, { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { router } from "expo-router";
import { Screen } from "../../src/ui/Screen";
import { BottomNav } from "../../src/ui/BottomNav";
import { EmptyState, ErrorState, LoadingState } from "../../src/ui/StateViews";
import { useChefOrders } from "../../src/hooks/useChefOps";
import { egp } from "../../src/utils/format";
import { colors, radius } from "../../src/theme/tokens";

const FILTERS = [
  {key:"all",label:"الكل"},
  {key:"new",label:"جديدة"},
  {key:"accepted",label:"مقبولة"},
  {key:"preparing",label:"طبخ"},
  {key:"packaging",label:"تغليف"},
  {key:"ready",label:"جاهزة"},
] as const;

const STAGE:Record<string,string>={
  new:"طلب جديد",accepted:"تم القبول",preparing:"جاري الطبخ",
  packaging:"جاري التغليف",ready:"جاهز للاستلام",rejected:"مرفوض",
};

export default function OrdersScreen() {
  const [filter,setFilter]=useState("all");
  const q=useChefOrders(filter==="all"?undefined:filter);

  return <View style={s.page}>
    <Screen>
      <View style={s.header}>
        <Text style={s.title}>طلبات التنفيذ</Text>
        <Text style={s.meta}>تتحدث تلقائيًا كل 15 ثانية</Text>
      </View>
      <View style={s.filters}>
        {FILTERS.map(x=><Pressable key={x.key} onPress={()=>setFilter(x.key)} style={[s.filter,filter===x.key&&s.filterActive]}>
          <Text style={[s.filterText,filter===x.key&&s.filterTextActive]}>{x.label}</Text>
        </Pressable>)}
      </View>

      {q.isLoading?<LoadingState label="بنجيب الطلبات..."/>:
       q.isError?<ErrorState message="تعذر تحميل الطلبات."/>:
       q.data?.length?q.data.map(order=><Pressable key={order.order_id} onPress={()=>router.push(`/orders/${order.order_id}`)} style={s.card}>
        <View style={s.row}>
          <View style={{flex:1}}>
            <Text style={s.orderNo}>طلب #{order.order_id.slice(0,8).toUpperCase()}</Text>
            <Text style={s.date}>{new Date(order.service_date).toLocaleDateString("ar-EG")} • {new Date(order.created_at).toLocaleTimeString("ar-EG",{hour:"2-digit",minute:"2-digit"})}</Text>
          </View>
          <View style={[s.stage,order.fulfillment_stage==="new"&&s.stageNew,order.fulfillment_stage==="ready"&&s.stageReady]}>
            <Text style={s.stageText}>{STAGE[order.fulfillment_stage]??order.fulfillment_stage}</Text>
          </View>
        </View>
        <View style={s.footer}>
          <Text style={s.price}>{egp(order.total_minor)}</Text>
          {order.acceptance_deadline_at&&order.fulfillment_stage==="new"?<Text style={s.deadline}>قبول قبل {new Date(order.acceptance_deadline_at).toLocaleTimeString("ar-EG",{hour:"2-digit",minute:"2-digit"})}</Text>:null}
        </View>
      </Pressable>):<EmptyState title="مفيش طلبات في الحالة دي" body="الطلبات الجديدة هتظهر هنا فور تأكيد الدفع."/>}
    </Screen>
    <BottomNav active="orders"/>
  </View>;
}

const s=StyleSheet.create({
  page:{flex:1,backgroundColor:colors.canvas},
  header:{paddingTop:10,paddingBottom:12},title:{fontSize:23,fontWeight:"900",color:colors.ink,textAlign:"right"},
  meta:{fontSize:10,color:colors.muted,textAlign:"right",marginTop:3},
  filters:{flexDirection:"row-reverse",flexWrap:"wrap",gap:7,marginBottom:14},
  filter:{paddingHorizontal:12,paddingVertical:8,borderRadius:radius.pill,backgroundColor:colors.soft},
  filterActive:{backgroundColor:colors.orangeSoft},filterText:{fontSize:10,color:colors.muted},
  filterTextActive:{color:colors.orangeDark,fontWeight:"900"},
  card:{borderWidth:1,borderColor:colors.border,borderRadius:radius.md,backgroundColor:colors.surface,padding:14,marginBottom:10},
  row:{flexDirection:"row-reverse",alignItems:"center",gap:10},orderNo:{fontWeight:"900",color:colors.ink,textAlign:"right"},
  date:{fontSize:10,color:colors.muted,textAlign:"right",marginTop:3},
  stage:{backgroundColor:colors.soft,borderRadius:radius.pill,paddingHorizontal:9,paddingVertical:6},
  stageNew:{backgroundColor:colors.orangeSoft},stageReady:{backgroundColor:colors.greenSoft},
  stageText:{fontSize:9,fontWeight:"900",color:colors.ink},
  footer:{flexDirection:"row-reverse",justifyContent:"space-between",alignItems:"center",marginTop:11,borderTopWidth:1,borderTopColor:colors.border,paddingTop:9},
  price:{fontWeight:"900",color:colors.orangeDark},deadline:{fontSize:9,color:colors.danger,fontWeight:"800"},
});
