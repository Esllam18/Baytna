import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { useLiveOrderTracking, useOrder } from "../../../src/hooks/useCommerce";
import { Screen } from "../../../src/ui/Screen";
import { OrderStatusCard } from "../../../src/ui/OrderStatusCard";
import { ErrorState, LoadingState } from "../../../src/ui/StateViews";
import { colors, radius, spacing } from "../../../src/theme/tokens";

const steps = [
  ['confirmed','تم تأكيد طلبك'],
  ['accepted_by_chef','الشيف بدأت تجهيز أكلك'],
  ['preparing','جاري الطبخ والتغليف'],
  ['ready_for_pickup','أكلك جاهز'],
  ['assigned_to_driver','المندوب في طريقه للشيف'],
  ['picked_up','المندوب استلم الطلب'],
  ['out_for_delivery','طلبك في الطريق'],
  ['delivered','تم توصيل طلبك'],
] as const;

export default function TrackingScreen() {
  const { orderId } = useLocalSearchParams<{ orderId: string }>();
  const id=String(orderId??'');
  const tracking=useLiveOrderTracking(id);
  const order=useOrder(id);
  if (tracking.isLoading || order.isLoading) return <Screen><LoadingState label="بنتابع طلبك..."/></Screen>;
  if (tracking.isError || !tracking.data || order.isError || !order.data) return <Screen><ErrorState message="تعذر تحديث حالة الطلب."/></Screen>;
  const current=tracking.data.delivery?.order_status ?? tracking.data.fulfillment.status;
  const currentIndex=steps.findIndex(([status])=>status===current);
  const terminal=current==='cancelled'||current==='expired';
  const delivery=tracking.data.delivery;
  const promiseStart=delivery?.promised_delivery_window_start_at ?? order.data.promised_delivery_window_start_at;
  const promiseEnd=delivery?.promised_delivery_window_end_at ?? order.data.promised_delivery_window_end_at;
  const promiseZone=delivery?.promised_delivery_timezone ?? order.data.promised_delivery_timezone;
  return <Screen><View style={s.header}><Pressable onPress={()=>router.back()} style={s.back}><Text style={s.backText}>→</Text></Pressable><Text style={s.title}>تتبع الطلب</Text><Pressable onPress={()=>tracking.refetch()}><Text style={s.refresh}>تحديث</Text></Pressable></View><View style={s.live}><View style={s.liveDot}/><Text style={s.liveText}>{terminal?'تم إنهاء الطلب':'تحديث مباشر كل 10 ثوانٍ'}</Text></View><View style={s.current}><Text style={s.currentLabel}>الحالة الحالية</Text><Text style={s.currentTitle}>{delivery?.display_status ?? tracking.data.fulfillment.display_status}</Text>{(delivery?.detail ?? tracking.data.fulfillment.detail)?<Text style={s.currentDetail}>{delivery?.detail ?? tracking.data.fulfillment.detail}</Text>:null}{tracking.data.fulfillment.estimated_ready_at?<Text style={s.estimate}>الوقت المتوقع للجاهزية: {new Date(tracking.data.fulfillment.estimated_ready_at).toLocaleTimeString('ar-EG',{hour:'2-digit',minute:'2-digit'})}</Text>:null}</View>{promiseStart&&promiseEnd?<View style={s.promise}><Text style={s.promiseLabel}>موعد التوصيل المتفق عليه</Text><Text style={s.promiseTime}>{formatPromise(promiseStart,promiseEnd,promiseZone)}</Text>{delivery?.delivery_timing_status==='on_time'?<Text style={s.onTime}>تم التوصيل داخل الموعد ✓</Text>:delivery?.delivery_timing_status==='late'?<Text style={s.late}>تم التوصيل بعد الموعد بـ {delivery.late_by_minutes??0} دقيقة</Text>:null}</View>:null}<Text style={s.section}>رحلة طلبك</Text><View style={s.timeline}>{steps.map(([status,label],index)=><OrderStatusCard key={status} title={label} active={!terminal && (currentIndex<0 ? index===0 : index<=currentIndex)} />)}</View>{terminal?<View style={s.terminal}><Text style={s.terminalTitle}>{current==='cancelled'?'تم إلغاء الطلب':'انتهت مهلة الطلب'}</Text><Text style={s.terminalBody}>تقدر ترجع لطلباتك أو تبدأ طلب جديد من مطبخ بيتنا.</Text></View>:null}</Screen>;
}
function formatPromise(start:string,end:string,timeZone:string|null){
  const options:Intl.DateTimeFormatOptions={hour:'2-digit',minute:'2-digit'};
  if(timeZone)options.timeZone=timeZone;
  return `${new Date(start).toLocaleTimeString('ar-EG',options)} – ${new Date(end).toLocaleTimeString('ar-EG',options)}`;
}

const s=StyleSheet.create({header:{flexDirection:'row-reverse',justifyContent:'space-between',alignItems:'center',paddingTop:12},back:{width:42,height:42,borderRadius:21,borderWidth:1,borderColor:colors.border,backgroundColor:colors.surface,alignItems:'center',justifyContent:'center'},backText:{fontSize:24},title:{fontSize:22,fontWeight:'900',color:colors.ink,writingDirection:'rtl'},refresh:{color:colors.orangeDark,fontWeight:'800'},live:{flexDirection:'row-reverse',alignItems:'center',gap:7,alignSelf:'flex-end',marginTop:14},liveDot:{width:8,height:8,borderRadius:4,backgroundColor:colors.green},liveText:{fontSize:11,color:colors.greenDark,writingDirection:'rtl'},current:{marginTop:14,padding:18,borderRadius:radius.card,backgroundColor:colors.orangeSoft},currentLabel:{fontSize:11,color:colors.muted,textAlign:'right',writingDirection:'rtl'},currentTitle:{fontSize:22,fontWeight:'900',color:colors.orangeDark,textAlign:'right',writingDirection:'rtl',marginTop:4},currentDetail:{fontSize:12,color:colors.muted,textAlign:'right',writingDirection:'rtl',lineHeight:18,marginTop:5},estimate:{fontSize:11,fontWeight:'800',color:colors.ink,textAlign:'right',marginTop:9},promise:{marginTop:12,padding:14,borderRadius:radius.md,backgroundColor:colors.surface,borderWidth:1,borderColor:colors.border},promiseLabel:{fontSize:10,color:colors.muted,textAlign:'right',writingDirection:'rtl'},promiseTime:{fontSize:18,fontWeight:'900',color:colors.ink,textAlign:'right',marginTop:4},onTime:{fontSize:10,fontWeight:'900',color:colors.greenDark,textAlign:'right',marginTop:6},late:{fontSize:10,fontWeight:'900',color:colors.danger,textAlign:'right',marginTop:6},section:{fontSize:17,fontWeight:'900',color:colors.ink,textAlign:'right',writingDirection:'rtl',marginTop:22,marginBottom:10},timeline:{gap:8},terminal:{padding:14,borderRadius:radius.md,backgroundColor:colors.dangerSoft,marginTop:16},terminalTitle:{fontWeight:'900',color:colors.danger,textAlign:'right',writingDirection:'rtl'},terminalBody:{fontSize:12,color:colors.muted,textAlign:'right',writingDirection:'rtl',marginTop:4}});
