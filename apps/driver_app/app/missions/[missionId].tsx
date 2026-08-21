import React,{useEffect,useState} from "react";
import {Alert,Pressable,StyleSheet,Text,View} from "react-native";
import {router,useLocalSearchParams} from "expo-router";
import {useMutation,useQueryClient} from "@tanstack/react-query";
import {driverApi} from "../../src/api";
import {driverKeys} from "../../src/query/keys";
import {useAvailableMission,useMission} from "../../src/hooks/useDriverOps";
import {navigateToDropoff,navigateToPickup} from "../../src/navigation/maps";
import {Screen} from "../../src/ui/Screen";
import {PrimaryButton} from "../../src/ui/PrimaryButton";
import {FormField} from "../../src/ui/FormField";
import {ErrorState,LoadingState} from "../../src/ui/StateViews";
import {colors,radius} from "../../src/theme/tokens";

const STATUS:Record<string,string>={
  unassigned:"مهمة متاحة",
  to_pickup:"في الطريق للشيف",
  at_pickup:"وصلت عند الشيف",
  picked_up:"تم استلام الطلب",
  to_customer:"في الطريق للعميل",
  delivery_issue:"مشكلة بالتوصيل",
  delivered:"تم التوصيل",
  cancelled:"ملغية",
};

export default function MissionDetailScreen(){
  const params=useLocalSearchParams<{missionId:string;preview?:string}>();
  const id=String(params.missionId??"");
  const preview=String(params.preview??"")==="1";
  const previewQuery=useAvailableMission(id,preview);
  const ownedQuery=useMission(id,!preview);
  const q=preview?previewQuery:ownedQuery;
  const qc=useQueryClient();
  const [issueOpen,setIssueOpen]=useState(false);
  const [issueCode,setIssueCode]=useState("customer_unreachable");
  const [issueNote,setIssueNote]=useState("");

  const refresh=async()=>{
    await Promise.all([
      qc.invalidateQueries({queryKey:driverKeys.dashboard}),
      qc.invalidateQueries({queryKey:driverKeys.availableMissions}),
      qc.invalidateQueries({queryKey:driverKeys.mission(id)}),
      qc.invalidateQueries({queryKey:driverKeys.currentMission}),
      qc.invalidateQueries({queryKey:driverKeys.history}),
    ]);
  };

  const accept=useMutation({
    mutationFn:()=>driverApi.acceptMission(id),
    onSuccess:async()=>{await refresh();router.replace(`/missions/${id}`);},
  });
  const transition=useMutation({
    mutationFn:async(action:"arrive"|"pickup"|"start"|"resume")=>{
      if(action==="arrive")return driverApi.arrivePickup(id);
      if(action==="pickup")return driverApi.confirmPickup(id);
      if(action==="start")return driverApi.startDelivery(id);
      return driverApi.resumeMission(id);
    },
    onSuccess:refresh,
  });
  const issue=useMutation({
    mutationFn:()=>driverApi.reportIssue(id,{issue_code:issueCode,note:issueNote.trim()}),
    onSuccess:async()=>{setIssueOpen(false);setIssueNote("");await refresh();},
  });

  if(q.isLoading)return <Screen><LoadingState label="بنفتح المهمة..."/></Screen>;
  if(q.isError||!q.data)return <Screen><ErrorState message={preview?"المهمة لم تعد متاحة.":"تعذر فتح المهمة."}/></Screen>;
  const m=q.data;

  return <Screen>
    <View style={s.header}>
      <Text onPress={()=>router.back()} style={s.back}>→</Text>
      <View style={{flex:1}}>
        <Text style={s.title}>مهمة #{m.id.slice(0,8).toUpperCase()}</Text>
        <Text style={s.status}>{STATUS[m.status]??m.status}</Text>
      </View>
    </View>

    <View style={s.route}>
      <Stop
        icon="👩‍🍳"
        title="الاستلام من الشيف"
        main={m.pickup_name}
        detail={m.pickup_area}
        active={["unassigned","to_pickup","at_pickup"].includes(m.status)}
      />
      <View style={s.routeLine}/>
      <Stop
        icon="🏠"
        title="التوصيل للعميل"
        main={m.dropoff?.label||"عنوان التوصيل"}
        detail={addressText(m.dropoff)}
        active={["picked_up","to_customer","delivery_issue"].includes(m.status)}
      />
    </View>

    {m.promised_delivery_window_start_at&&m.promised_delivery_window_end_at?<View style={[s.promiseCard,isPromiseLate(m.promised_delivery_window_end_at)&&m.status!=="delivered"&&s.promiseLate]}>
      <Text style={s.promiseLabel}>موعد التسليم المستهدف</Text>
      <Text style={s.promiseTime}>{formatPromise(m.promised_delivery_window_start_at,m.promised_delivery_window_end_at,m.promised_delivery_timezone)}</Text>
      {m.status!=="delivered"?<Text style={s.promiseHint}>{promiseHint(m.promised_delivery_window_end_at)}</Text>:m.delivery_timing_status==="on_time"?<Text style={s.promiseOnTime}>تم التسليم داخل الوعد ✓</Text>:m.delivery_timing_status==="late"?<Text style={s.promiseLateText}>تأخر {m.late_by_minutes??0} دقيقة</Text>:null}
    </View>:null}

    <View style={s.privacy}>
      <Text style={s.privacyTitle}>خصوصية العميل</Text>
      <Text style={s.privacyText}>رقم الهاتف ووسائل الاتصال المباشرة غير معروضة. أي مشكلة تتسجل من داخل المهمة.</Text>
    </View>

    {m.status==="unassigned"?<>
      <PrimaryButton
        label="قبول المهمة"
        tone="success"
        onPress={()=>accept.mutate()}
        loading={accept.isPending}
        disabled={!m.navigation_ready}
      />
      {!m.navigation_ready?<Text style={s.error}>لا يمكن قبول المهمة قبل اكتمال عنوان التوصيل.</Text>:null}
    </>:null}

    {m.status==="to_pickup"?<>
      <PrimaryButton label="افتح الملاحة للشيف" tone="secondary" onPress={()=>navigateToPickup(m.pickup_name,m.pickup_area)}/>
      <View style={s.gap}/>
      <PrimaryButton label="وصلت عند الشيف" onPress={()=>transition.mutate("arrive")} loading={transition.isPending}/>
    </>:null}

    {m.status==="at_pickup"?<>
      <View style={s.check}><Text style={s.checkTitle}>راجع الطلب قبل الاستلام</Text><Text style={s.checkText}>تأكد من التغليف وعدد الأكياس قبل ما تؤكد الاستلام.</Text></View>
      <PrimaryButton label="تأكيد استلام الطلب" tone="success" onPress={()=>transition.mutate("pickup")} loading={transition.isPending}/>
    </>:null}

    {m.status==="picked_up"?<>
      {m.dropoff?<PrimaryButton label="افتح عنوان العميل" tone="secondary" onPress={()=>navigateToDropoff(m.dropoff!)}/>:null}
      <View style={s.gap}/>
      <PrimaryButton label="ابدأ التوصيل للعميل" onPress={()=>transition.mutate("start")} loading={transition.isPending}/>
    </>:null}

    {m.status==="to_customer"?<>
      {m.dropoff?<PrimaryButton label="الملاحة إلى العميل" tone="secondary" onPress={()=>navigateToDropoff(m.dropoff!)}/>:null}
      <View style={s.gap}/>
      <PrimaryButton label="وصلت — سجّل إثبات التوصيل" tone="success" onPress={()=>router.push(`/missions/${id}/proof`)}/>
      <Pressable onPress={()=>setIssueOpen(!issueOpen)}><Text style={s.issueLink}>في مشكلة أثناء التوصيل؟</Text></Pressable>
    </>:null}

    {m.status==="delivery_issue"?<View style={s.issueCard}>
      <Text style={s.issueTitle}>مشكلة مسجلة</Text>
      <Text style={s.issueText}>{m.issue_code}</Text>
      {m.issue_note?<Text style={s.issueText}>{m.issue_note}</Text>:null}
      <View style={s.gap}/>
      <PrimaryButton label="تم حل المشكلة — استئناف المهمة" onPress={()=>transition.mutate("resume")} loading={transition.isPending}/>
    </View>:null}

    {issueOpen&&m.status!=="delivery_issue"?<View style={s.issueForm}>
      <Text style={s.section}>تسجيل مشكلة</Text>
      <FormField label="كود المشكلة" value={issueCode} onChangeText={setIssueCode} placeholder="customer_unreachable"/>
      <View style={s.gap}/>
      <FormField label="التفاصيل" value={issueNote} onChangeText={setIssueNote} multiline placeholder="اكتب اللي حصل بوضوح..."/>
      <View style={s.gap}/>
      <PrimaryButton label="تسجيل المشكلة" tone="danger" onPress={()=>issue.mutate()} loading={issue.isPending} disabled={issueNote.trim().length<3}/>
    </View>:null}

    {m.status==="delivered"?<View style={s.done}>
      <Text style={s.doneTitle}>تم توصيل الطلب ✓</Text>
      <Text style={s.doneText}>إثبات التوصيل: {m.delivery_proof_type??"مسجل"}</Text>
      <PrimaryButton label="ارجع للرئيسية" onPress={()=>router.replace("/home")}/>
    </View>:null}

    {(accept.isError||transition.isError||issue.isError)?<Text style={s.error}>تعذر تحديث المهمة. حدّث وحاول مرة أخرى.</Text>:null}
  </Screen>;
}

function formatPromise(start:string,end:string,timeZone:string|null){
  const options:Intl.DateTimeFormatOptions={hour:"2-digit",minute:"2-digit"};
  if(timeZone)options.timeZone=timeZone;
  return `${new Date(start).toLocaleTimeString("ar-EG",options)} – ${new Date(end).toLocaleTimeString("ar-EG",options)}`;
}
function isPromiseLate(end:string){return Date.now()>new Date(end).getTime();}
function promiseHint(end:string){
  const minutes=Math.ceil((new Date(end).getTime()-Date.now())/60000);
  if(minutes<0)return `متأخر عن الوعد بحوالي ${Math.abs(minutes)} دقيقة`;
  if(minutes<=20)return `متبقي حوالي ${minutes} دقيقة`;
  return "رتّب خط سيرك علشان توصل داخل الموعد.";
}

function Stop({icon,title,main,detail,active}:{icon:string;title:string;main:string;detail:string;active:boolean}){
  return <View style={[s.stop,active&&s.stopActive]}>
    <View style={s.stopIcon}><Text style={s.stopIconText}>{icon}</Text></View>
    <View style={{flex:1}}>
      <Text style={s.stopTitle}>{title}</Text>
      <Text style={s.stopMain}>{main}</Text>
      <Text style={s.stopDetail}>{detail}</Text>
    </View>
  </View>;
}

function addressText(a:{area:string;street:string|null;building:string|null;floor:string|null;apartment:string|null}|null){
  if(!a)return "العنوان غير متاح";
  return [a.area,a.street,a.building&&`مبنى ${a.building}`,a.floor&&`دور ${a.floor}`,a.apartment&&`شقة ${a.apartment}`].filter(Boolean).join("، ");
}

const s=StyleSheet.create({
  header:{flexDirection:"row-reverse",alignItems:"center",gap:12,paddingTop:10,paddingBottom:16},
  back:{fontSize:26},title:{fontSize:20,fontWeight:"900",color:colors.ink,textAlign:"right"},status:{fontSize:11,color:colors.orangeDark,fontWeight:"900",textAlign:"right",marginTop:3},
  route:{borderWidth:1,borderColor:colors.border,borderRadius:radius.card,backgroundColor:colors.surface,padding:14},
  stop:{flexDirection:"row-reverse",alignItems:"center",gap:12,paddingVertical:8,opacity:.65},stopActive:{opacity:1},
  stopIcon:{width:48,height:48,borderRadius:15,backgroundColor:colors.orangeSoft,alignItems:"center",justifyContent:"center"},stopIconText:{fontSize:24},
  stopTitle:{fontSize:9,color:colors.muted,textAlign:"right"},stopMain:{fontWeight:"900",color:colors.ink,textAlign:"right",writingDirection:"rtl",marginTop:2},
  stopDetail:{fontSize:10,color:colors.muted,textAlign:"right",writingDirection:"rtl",marginTop:3,lineHeight:16},
  routeLine:{height:20,width:2,backgroundColor:colors.border,alignSelf:"flex-end",marginRight:23},
  promiseCard:{backgroundColor:colors.greenSoft,borderRadius:radius.md,padding:13,marginBottom:12,borderWidth:1,borderColor:colors.border},promiseLate:{backgroundColor:colors.dangerSoft},promiseLabel:{fontSize:9,color:colors.muted,textAlign:'right',writingDirection:'rtl'},promiseTime:{fontSize:18,fontWeight:'900',color:colors.ink,textAlign:'right',marginTop:3},promiseHint:{fontSize:10,color:colors.orangeDark,fontWeight:'800',textAlign:'right',marginTop:5,writingDirection:'rtl'},promiseOnTime:{fontSize:10,color:colors.greenDark,fontWeight:'900',textAlign:'right',marginTop:5},promiseLateText:{fontSize:10,color:colors.danger,fontWeight:'900',textAlign:'right',marginTop:5},privacy:{backgroundColor:colors.blueSoft,borderRadius:radius.md,padding:13,marginVertical:14},
  privacyTitle:{fontWeight:"900",color:colors.blueDark,textAlign:"right",writingDirection:"rtl"},privacyText:{fontSize:10,color:colors.muted,textAlign:"right",writingDirection:"rtl",marginTop:4,lineHeight:17},
  gap:{height:10},check:{backgroundColor:colors.orangeSoft,borderRadius:radius.md,padding:13,marginBottom:12},
  checkTitle:{fontWeight:"900",color:colors.orangeDark,textAlign:"right",writingDirection:"rtl"},checkText:{fontSize:10,color:colors.muted,textAlign:"right",writingDirection:"rtl",marginTop:4},
  issueLink:{color:colors.danger,fontWeight:"900",fontSize:11,textAlign:"center",marginTop:15,writingDirection:"rtl"},
  issueCard:{backgroundColor:colors.dangerSoft,borderRadius:radius.md,padding:14},issueTitle:{fontWeight:"900",color:colors.danger,textAlign:"right"},issueText:{fontSize:10,color:colors.muted,textAlign:"right",writingDirection:"rtl",marginTop:4},
  issueForm:{marginTop:14,borderWidth:1,borderColor:colors.border,borderRadius:radius.md,padding:14,backgroundColor:colors.surface},
  section:{fontSize:16,fontWeight:"900",color:colors.ink,textAlign:"right",marginBottom:10},
  done:{backgroundColor:colors.greenSoft,borderRadius:radius.card,padding:16,gap:9},doneTitle:{fontSize:18,fontWeight:"900",color:colors.greenDark,textAlign:"right",writingDirection:"rtl"},
  doneText:{fontSize:10,color:colors.muted,textAlign:"right",writingDirection:"rtl"},error:{color:colors.danger,textAlign:"center",writingDirection:"rtl",marginTop:10},
});
