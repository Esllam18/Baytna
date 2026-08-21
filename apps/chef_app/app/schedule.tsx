import React,{useEffect,useState} from "react";
import {StyleSheet,Switch,Text,TextInput,View} from "react-native";
import {router} from "expo-router";
import {useMutation,useQueryClient} from "@tanstack/react-query";
import {chefApi} from "../src/api";
import {WeeklyScheduleDay} from "../src/api/types";
import {chefKeys} from "../src/query/keys";
import {useWeeklySchedule} from "../src/hooks/useChefOps";
import {Screen} from "../src/ui/Screen";
import {PrimaryButton} from "../src/ui/PrimaryButton";
import {LoadingState,ErrorState} from "../src/ui/StateViews";
import {colors,radius} from "../src/theme/tokens";

const names=["الاثنين","الثلاثاء","الأربعاء","الخميس","الجمعة","السبت","الأحد"];
const defaults:WeeklyScheduleDay[]=Array.from({length:7},(_,weekday)=>({weekday,is_available:weekday<6,delivery_window_start:"12:00",delivery_window_end:"20:00",max_special_orders:5}));

export default function ScheduleScreen(){
 const q=useWeeklySchedule(); const qc=useQueryClient(); const [days,setDays]=useState<WeeklyScheduleDay[]>(defaults);
 useEffect(()=>{if(q.data?.length){const map=new Map(q.data.map(x=>[x.weekday,x]));setDays(defaults.map(x=>map.get(x.weekday)??x));}},[q.data]);
 const save=useMutation({mutationFn:()=>chefApi.saveWeeklySchedule(days),onSuccess:()=>qc.invalidateQueries({queryKey:chefKeys.schedule})});
 if(q.isLoading)return <Screen><LoadingState label="بنفتح جدولك..."/></Screen>;
 if(q.isError)return <Screen><ErrorState message="تعذر تحميل الجدول."/></Screen>;
 const update=(weekday:number,patch:Partial<WeeklyScheduleDay>)=>setDays(cur=>cur.map(x=>x.weekday===weekday?{...x,...patch}:x));
 return <Screen>
  <View style={s.header}><Text onPress={()=>router.back()} style={s.back}>→</Text><Text style={s.title}>جدول الطلبات الخاصة</Text></View>
  <Text style={s.note}>الجدول ده بيحدد الأيام والسعة اللي العميل يقدر يختار منها للطلبات الخاصة والحجز المسبق.</Text>
  {days.map(day=><View key={day.weekday} style={[s.card,!day.is_available&&s.off]}>
    <View style={s.top}><Switch value={day.is_available} onValueChange={is_available=>update(day.weekday,{is_available})}/><Text style={s.day}>{names[day.weekday]}</Text></View>
    {day.is_available?<View style={s.inputs}>
      <View style={{flex:1}}><Text style={s.label}>من</Text><TextInput value={day.delivery_window_start??""} onChangeText={delivery_window_start=>update(day.weekday,{delivery_window_start})} style={s.input}/></View>
      <View style={{flex:1}}><Text style={s.label}>إلى</Text><TextInput value={day.delivery_window_end??""} onChangeText={delivery_window_end=>update(day.weekday,{delivery_window_end})} style={s.input}/></View>
      <View style={{flex:1}}><Text style={s.label}>السعة</Text><TextInput value={String(day.max_special_orders)} keyboardType="number-pad" onChangeText={v=>update(day.weekday,{max_special_orders:Number(v||0)})} style={s.input}/></View>
    </View>:null}
  </View>)}
  {save.isError?<Text style={s.error}>تأكد إن وقت النهاية بعد البداية والسعة صحيحة.</Text>:null}
  <PrimaryButton label="حفظ الجدول الأسبوعي" onPress={()=>save.mutate()} loading={save.isPending}/>
 </Screen>;
}
const s=StyleSheet.create({
 header:{flexDirection:"row-reverse",alignItems:"center",gap:12,paddingTop:10,paddingBottom:14},back:{fontSize:26},title:{flex:1,fontSize:22,fontWeight:"900",color:colors.ink,textAlign:"right"},
 note:{fontSize:11,color:colors.muted,textAlign:"right",writingDirection:"rtl",lineHeight:18,marginBottom:14},
 card:{borderWidth:1,borderColor:colors.border,borderRadius:radius.md,backgroundColor:colors.surface,padding:12,marginBottom:9},off:{opacity:.6},
 top:{flexDirection:"row-reverse",alignItems:"center",gap:10},day:{flex:1,fontWeight:"900",color:colors.ink,textAlign:"right"},
 inputs:{flexDirection:"row-reverse",gap:7,marginTop:10},label:{fontSize:9,color:colors.muted,textAlign:"right",marginBottom:4},input:{minHeight:40,borderWidth:1,borderColor:colors.border,borderRadius:10,paddingHorizontal:8,textAlign:"center",backgroundColor:"#fff"},
 error:{color:colors.danger,textAlign:"center",marginBottom:10}
});
