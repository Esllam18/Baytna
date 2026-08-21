import React, { useState } from "react";
import { Alert, StyleSheet, Text, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { chefApi } from "../../src/api";
import { chefKeys } from "../../src/query/keys";
import { useChefOrder } from "../../src/hooks/useChefOps";
import { Screen } from "../../src/ui/Screen";
import { PrimaryButton } from "../../src/ui/PrimaryButton";
import { FormField } from "../../src/ui/FormField";
import { ErrorState, LoadingState } from "../../src/ui/StateViews";
import { egp } from "../../src/utils/format";
import { colors, radius } from "../../src/theme/tokens";

const STAGE:Record<string,string>={
  new:"طلب جديد",accepted:"تم القبول",preparing:"جاري الطبخ",
  packaging:"جاري التغليف",ready:"جاهز للاستلام",rejected:"مرفوض",
};

export default function ChefOrderDetailScreen() {
  const {orderId}=useLocalSearchParams<{orderId:string}>();
  const id=String(orderId??"");
  const q=useChefOrder(id);
  const qc=useQueryClient();
  const [note,setNote]=useState("");
  const [reason,setReason]=useState("");

  const refresh=()=>Promise.all([
    qc.invalidateQueries({queryKey:chefKeys.order(id)}),
    qc.invalidateQueries({queryKey:["chef","orders"]}),
    qc.invalidateQueries({queryKey:["chef","dashboard"]}),
  ]);
  const action=useMutation({
    mutationFn:async(kind:"accept"|"prepare"|"package"|"ready")=>{
      if(kind==="accept") return chefApi.acceptOrder(id,note||null);
      if(kind==="prepare") return chefApi.startPreparing(id,note||null);
      if(kind==="package") return chefApi.startPackaging(id,note||null);
      return chefApi.readyForPickup(id,note||null);
    },
    onSuccess:refresh,
  });
  const reject=useMutation({
    mutationFn:()=>chefApi.rejectOrder(id,reason.trim()),
    onSuccess:refresh,
  });

  if(q.isLoading)return <Screen><LoadingState label="بنفتح الطلب..."/></Screen>;
  if(q.isError||!q.data)return <Screen><ErrorState message="تعذر فتح الطلب."/></Screen>;
  const o=q.data;

  return <Screen>
    <View style={s.header}><Text onPress={()=>router.back()} style={s.back}>→</Text><Text style={s.title}>طلب #{id.slice(0,8).toUpperCase()}</Text></View>
    <View style={s.hero}>
      <Text style={s.stage}>{STAGE[o.fulfillment_stage]??o.fulfillment_stage}</Text>
      <Text style={s.date}>موعد الخدمة: {new Date(o.service_date).toLocaleDateString("ar-EG")}</Text>
      {o.estimated_ready_at?<Text style={s.date}>جاهز تقريبًا: {new Date(o.estimated_ready_at).toLocaleTimeString("ar-EG",{hour:"2-digit",minute:"2-digit"})}</Text>:null}
    </View>

    <Text style={s.section}>الأكلات</Text>
    {o.items.map(item=><View key={item.dish_id} style={s.item}>
      <View style={{flex:1}}><Text style={s.itemName}>{item.dish_name}</Text><Text style={s.itemMeta}>{item.quantity} × {egp(item.unit_price_minor)}</Text></View>
      <Text style={s.itemPrice}>{egp(item.line_total_minor)}</Text>
    </View>)}
    <View style={s.total}><Text style={s.totalLabel}>الإجمالي</Text><Text style={s.totalValue}>{egp(o.total_minor)}</Text></View>

    {!["ready","rejected"].includes(o.fulfillment_stage)?<>
      <Text style={s.section}>ملاحظة داخلية للتنفيذ</Text>
      <FormField label="ملاحظة الشيف" value={note} onChangeText={setNote} multiline placeholder="مثال: يحتاج 35 دقيقة..."/>
    </>:null}

    {o.fulfillment_stage==="new"?<>
      <PrimaryButton label="قبول الطلب" onPress={()=>action.mutate("accept")} loading={action.isPending} tone="success"/>
      <View style={{height:10}}/>
      <FormField label="سبب الرفض لو مش هتقدر تنفذ" value={reason} onChangeText={setReason} placeholder="السبب..."/>
      <View style={{height:8}}/>
      <PrimaryButton label="رفض الطلب" tone="danger" disabled={reason.trim().length<3} loading={reject.isPending} onPress={()=>Alert.alert("رفض الطلب","الرفض قد يؤدي لاسترداد العميل وإلغاء الطلب.",[
        {text:"رجوع",style:"cancel"},{text:"تأكيد الرفض",style:"destructive",onPress:()=>reject.mutate()},
      ])}/>
    </>:null}
    {o.fulfillment_stage==="accepted"?<PrimaryButton label="ابدأ الطبخ" onPress={()=>action.mutate("prepare")} loading={action.isPending}/>:null}
    {o.fulfillment_stage==="preparing"?<PrimaryButton label="ابدأ التغليف" onPress={()=>action.mutate("package")} loading={action.isPending}/>:null}
    {o.fulfillment_stage==="packaging"?<PrimaryButton label="جاهز لاستلام المندوب" tone="success" onPress={()=>action.mutate("ready")} loading={action.isPending}/>:null}
    {o.fulfillment_stage==="ready"?<View style={s.done}><Text style={s.doneTitle}>الطلب جاهز ✓</Text><Text style={s.doneText}>مستني استلام المندوب. متشاركش رقم العميل أو تتواصل خارج بيتنا.</Text></View>:null}
    {o.fulfillment_stage==="rejected"?<View style={s.rejected}><Text style={s.rejectedTitle}>تم رفض الطلب</Text><Text style={s.rejectedText}>{o.rejection_reason}</Text></View>:null}

    {(action.isError||reject.isError)?<Text style={s.error}>تعذر تحديث حالة الطلب. حدّث وحاول مرة أخرى.</Text>:null}
  </Screen>;
}
const s=StyleSheet.create({
  header:{flexDirection:"row-reverse",alignItems:"center",gap:12,paddingTop:10,paddingBottom:16},back:{fontSize:26},
  title:{flex:1,fontSize:21,fontWeight:"900",color:colors.ink,textAlign:"right"},
  hero:{backgroundColor:colors.orangeSoft,borderRadius:radius.card,padding:16},stage:{fontSize:18,fontWeight:"900",color:colors.orangeDark,textAlign:"right"},
  date:{fontSize:10,color:colors.muted,textAlign:"right",marginTop:4},
  section:{fontSize:16,fontWeight:"900",color:colors.ink,textAlign:"right",marginTop:20,marginBottom:8},
  item:{flexDirection:"row-reverse",alignItems:"center",gap:10,borderBottomWidth:1,borderBottomColor:colors.border,paddingVertical:11},
  itemName:{fontWeight:"900",color:colors.ink,textAlign:"right",writingDirection:"rtl"},itemMeta:{fontSize:10,color:colors.muted,textAlign:"right",marginTop:3},
  itemPrice:{fontWeight:"900",color:colors.orangeDark},
  total:{flexDirection:"row-reverse",justifyContent:"space-between",paddingVertical:13},totalLabel:{fontWeight:"900",color:colors.ink},totalValue:{fontSize:18,fontWeight:"900",color:colors.orangeDark},
  done:{backgroundColor:colors.greenSoft,borderRadius:radius.md,padding:14},doneTitle:{fontWeight:"900",color:colors.greenDark,textAlign:"right"},
  doneText:{fontSize:10,color:colors.muted,textAlign:"right",writingDirection:"rtl",marginTop:4,lineHeight:17},
  rejected:{backgroundColor:colors.dangerSoft,borderRadius:radius.md,padding:14},rejectedTitle:{fontWeight:"900",color:colors.danger,textAlign:"right"},
  rejectedText:{fontSize:10,color:colors.muted,textAlign:"right",marginTop:4},error:{color:colors.danger,textAlign:"center",marginTop:10},
});
