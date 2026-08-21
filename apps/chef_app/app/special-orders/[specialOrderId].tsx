import React,{useState} from "react";
import {Alert,Pressable,StyleSheet,Text,View} from "react-native";
import {router,useLocalSearchParams} from "expo-router";
import {useMutation,useQueryClient} from "@tanstack/react-query";
import {chefApi} from "../../src/api";
import {chefKeys} from "../../src/query/keys";
import {useChefSpecialOrder} from "../../src/hooks/useChefOps";
import {Screen} from "../../src/ui/Screen";
import {PrimaryButton} from "../../src/ui/PrimaryButton";
import {FormField} from "../../src/ui/FormField";
import {ErrorState,LoadingState} from "../../src/ui/StateViews";
import {egp} from "../../src/utils/format";
import {colors,radius} from "../../src/theme/tokens";

const labels:Record<string,string>={chef_review:"تحتاج مراجعة",counter_offer:"بانتظار قرار العميل",awaiting_payment:"بانتظار الدفع",scheduled:"تمت الجدولة",rejected:"مرفوضة",cancelled:"ملغية",expired:"منتهية"};

export default function ChefSpecialOrderDetail(){
 const {specialOrderId}=useLocalSearchParams<{specialOrderId:string}>(); const id=String(specialOrderId??"");
 const q=useChefSpecialOrder(id); const qc=useQueryClient();
 const [mode,setMode]=useState<"accept"|"counter">("accept");
 const [price,setPrice]=useState(""); const [date,setDate]=useState(""); const [start,setStart]=useState(""); const [end,setEnd]=useState(""); const [note,setNote]=useState(""); const [reason,setReason]=useState("");
 const refresh=()=>Promise.all([qc.invalidateQueries({queryKey:chefKeys.specialOrder(id)}),qc.invalidateQueries({queryKey:["chef","special-orders"]}),qc.invalidateQueries({queryKey:["chef","dashboard"]})]);
 const act=useMutation({
  mutationFn:async()=>{
   if(!q.data) throw new Error("missing");
   if(mode==="accept") return chefApi.acceptSpecialOrder(id,{
    unit_price_minor:price?Math.round(Number(price)*100):null,
    delivery_window_start:start||null,delivery_window_end:end||null,chef_note:note||null,
   });
   return chefApi.counterSpecialOrder(id,{
    proposed_service_date:date||q.data.requested_service_date,
    proposed_unit_price_minor:Math.round(Number(price)*100),
    proposed_window_start:start||null,proposed_window_end:end||null,chef_note:note||null,
   });
  },onSuccess:refresh
 });
 const reject=useMutation({mutationFn:()=>chefApi.rejectSpecialOrder(id,reason.trim()),onSuccess:refresh});
 if(q.isLoading)return <Screen><LoadingState label="بنفتح الطلب الخاص..."/></Screen>;
 if(q.isError||!q.data)return <Screen><ErrorState message="تعذر فتح الطلب الخاص."/></Screen>;
 const x=q.data;
 return <Screen>
  <View style={s.header}><Text onPress={()=>router.back()} style={s.back}>→</Text><Text style={s.title}>{x.dish_name}</Text></View>
  <View style={s.hero}><Text style={s.status}>{labels[x.status]??x.status}</Text><Text style={s.meta}>{x.quantity} وحدة • {new Date(x.requested_service_date).toLocaleDateString("ar-EG")}</Text><Text style={s.price}>{egp(x.requested_unit_price_minor*x.quantity)}</Text></View>
  <Text style={s.section}>طلب العميل</Text>
  <View style={s.card}><Row label="النوع" value={x.request_type==="preorder"?"طلب مسبق":"طلب خاص"}/><Row label="الموعد" value={new Date(x.requested_service_date).toLocaleDateString("ar-EG")}/><Row label="النافذة" value={x.requested_window_start&&x.requested_window_end?`${x.requested_window_start}–${x.requested_window_end}`:"غير محددة"}/>{x.customer_note?<Text style={s.note}>{x.customer_note}</Text>:null}</View>
  {x.status==="chef_review"?<>
    <Text style={s.section}>قرارك</Text>
    <View style={s.modeRow}><Mode label="قبول" active={mode==="accept"} onPress={()=>setMode("accept")}/><Mode label="عرض بديل" active={mode==="counter"} onPress={()=>setMode("counter")}/></View>
    {mode==="counter"?<FormField label="موعد بديل YYYY-MM-DD" value={date} onChangeText={setDate} placeholder={x.requested_service_date}/>:null}
    <FormField label={mode==="accept"?"سعر بديل اختياري بالجنيه":"السعر المقترح بالجنيه"} value={price} onChangeText={setPrice} keyboardType="decimal-pad" placeholder={String(x.requested_unit_price_minor/100)}/>
    <View style={s.two}><View style={{flex:1}}><FormField label="من" value={start} onChangeText={setStart} placeholder={x.requested_window_start??"12:00"}/></View><View style={{flex:1}}><FormField label="إلى" value={end} onChangeText={setEnd} placeholder={x.requested_window_end??"20:00"}/></View></View>
    <FormField label="ملاحظة للعميل" value={note} onChangeText={setNote} multiline/>
    <PrimaryButton label={mode==="accept"?"قبول وإرسال عرض الدفع":"إرسال العرض البديل"} onPress={()=>act.mutate()} loading={act.isPending} disabled={mode==="counter"&&Number(price)<=0}/>
    <Text style={s.section}>أو ارفض الطلب</Text><FormField label="سبب الرفض" value={reason} onChangeText={setReason}/>
    <PrimaryButton label="رفض الطلب" tone="danger" disabled={reason.trim().length<3} loading={reject.isPending} onPress={()=>Alert.alert("رفض الطلب","سيصل سبب الرفض للعميل.",[{text:"رجوع",style:"cancel"},{text:"رفض",style:"destructive",onPress:()=>reject.mutate()}])}/>
  </>:null}
  {x.status==="counter_offer"?<View style={s.wait}><Text style={s.waitTitle}>العرض البديل اتبعت</Text><Text style={s.waitText}>بانتظار موافقة العميل. السعر المقترح {x.proposed_unit_price_minor?egp(x.proposed_unit_price_minor):"—"}.</Text></View>:null}
  {x.status==="awaiting_payment"?<View style={s.wait}><Text style={s.waitTitle}>العميل وافق / العرض جاهز</Text><Text style={s.waitText}>بانتظار الدفع. لا تبدأ التحضير قبل تحول الحالة إلى مجدولة بعد نجاح الدفع.</Text></View>:null}
  {x.status==="scheduled"?<View style={s.done}><Text style={s.doneTitle}>تمت الجدولة ✓</Text><Text style={s.waitText}>الطلب دخل مسار التنفيذ. {x.order_id?"افتح الطلب من قائمة التنفيذ عند ظهوره.":""}</Text></View>:null}
  <Text style={s.section}>سجل الحالة</Text>{x.events.map((e,i)=><View key={`${e.created_at}-${i}`} style={s.event}><View style={s.dot}/><View style={{flex:1}}><Text style={s.eventTitle}>{labels[e.to_status]??e.to_status}</Text><Text style={s.eventTime}>{new Date(e.created_at).toLocaleString("ar-EG")}</Text></View></View>)}
  {(act.isError||reject.isError)?<Text style={s.error}>راجع الموعد والسعر ونافذة التوصيل ثم حاول ثانية.</Text>:null}
 </Screen>;
}
function Row({label,value}:{label:string;value:string}){return <View style={s.row}><Text style={s.rowLabel}>{label}</Text><Text style={s.rowValue}>{value}</Text></View>}
function Mode({label,active,onPress}:{label:string;active:boolean;onPress():void}){return <Pressable onPress={onPress} style={[s.mode,active&&s.modeActive]}><Text style={[s.modeText,active&&s.modeTextActive]}>{label}</Text></Pressable>}
const s=StyleSheet.create({
 header:{flexDirection:"row-reverse",alignItems:"center",gap:12,paddingTop:10,paddingBottom:16},back:{fontSize:26},title:{flex:1,fontSize:22,fontWeight:"900",color:colors.ink,textAlign:"right"},
 hero:{backgroundColor:colors.orangeSoft,borderRadius:radius.card,padding:16},status:{fontSize:18,fontWeight:"900",color:colors.orangeDark,textAlign:"right"},meta:{fontSize:10,color:colors.muted,textAlign:"right",marginTop:4},price:{fontSize:19,fontWeight:"900",color:colors.ink,textAlign:"right",marginTop:7},
 section:{fontSize:16,fontWeight:"900",color:colors.ink,textAlign:"right",marginTop:20,marginBottom:8},card:{borderWidth:1,borderColor:colors.border,borderRadius:radius.md,backgroundColor:colors.surface,padding:14,gap:8},
 row:{flexDirection:"row-reverse",justifyContent:"space-between"},rowLabel:{color:colors.muted},rowValue:{fontWeight:"800",color:colors.ink},note:{borderTopWidth:1,borderTopColor:colors.border,paddingTop:8,color:colors.muted,fontSize:11,textAlign:"right",writingDirection:"rtl"},
 modeRow:{flexDirection:"row-reverse",gap:8,marginBottom:10},mode:{flex:1,paddingVertical:10,borderRadius:radius.md,backgroundColor:colors.soft,alignItems:"center"},modeActive:{backgroundColor:colors.orangeSoft},modeText:{color:colors.muted},modeTextActive:{color:colors.orangeDark,fontWeight:"900"},
 two:{flexDirection:"row-reverse",gap:8,marginVertical:10},wait:{backgroundColor:colors.orangeSoft,borderRadius:radius.md,padding:14,marginTop:16},done:{backgroundColor:colors.greenSoft,borderRadius:radius.md,padding:14,marginTop:16},waitTitle:{fontWeight:"900",color:colors.orangeDark,textAlign:"right"},doneTitle:{fontWeight:"900",color:colors.greenDark,textAlign:"right"},waitText:{fontSize:10,color:colors.muted,textAlign:"right",writingDirection:"rtl",marginTop:4,lineHeight:17},
 event:{flexDirection:"row-reverse",gap:9,borderBottomWidth:1,borderBottomColor:colors.border,paddingVertical:9},dot:{width:9,height:9,borderRadius:5,backgroundColor:colors.orange,marginTop:3},eventTitle:{fontWeight:"800",color:colors.ink,textAlign:"right"},eventTime:{fontSize:9,color:colors.muted,textAlign:"right",marginTop:2},error:{color:colors.danger,textAlign:"center",marginTop:10}
});
