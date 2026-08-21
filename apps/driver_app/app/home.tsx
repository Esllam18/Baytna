import React from "react";
import {Pressable,StyleSheet,Switch,Text,View} from "react-native";
import {router} from "expo-router";
import {useMutation,useQueryClient} from "@tanstack/react-query";
import {driverApi} from "../src/api";
import {driverKeys} from "../src/query/keys";
import {useDriverDashboard} from "../src/hooks/useDriverOps";
import {useAuth} from "../src/auth/AuthProvider";
import {Screen} from "../src/ui/Screen";
import {BottomNav} from "../src/ui/BottomNav";
import {ErrorState,LoadingState} from "../src/ui/StateViews";
import {colors,radius} from "../src/theme/tokens";

const STATUS:Record<string,string>={
  offline:"غير متاح",
  available:"متاح للمهام",
  on_mission:"في مهمة",
};

const MISSION:Record<string,string>={
  to_pickup:"في الطريق للشيف",
  at_pickup:"وصلت للشيف",
  picked_up:"استلمت الطلب",
  to_customer:"في الطريق للعميل",
  delivery_issue:"مشكلة بالتوصيل",
};

export default function DriverHomeScreen(){
  const q=useDriverDashboard();
  const qc=useQueryClient();
  const auth=useAuth();

  const availability=useMutation({
    mutationFn:(available:boolean)=>driverApi.setAvailability(available),
    onSuccess:async()=>{
      await Promise.all([
        qc.invalidateQueries({queryKey:driverKeys.dashboard}),
        qc.invalidateQueries({queryKey:driverKeys.profile}),
        qc.invalidateQueries({queryKey:driverKeys.availableMissions}),
      ]);
    },
  });

  if(q.isLoading)return <View style={s.page}><Screen><LoadingState label="بنجهز لوحة المندوب..."/></Screen><BottomNav active="home"/></View>;
  if(q.isError||!q.data)return <View style={s.page}><Screen><ErrorState message="تعذر تحميل لوحة المندوب."/></Screen><BottomNav active="home"/></View>;

  const d=q.data;
  const available=d.driver.status==="available";
  const active=d.active_mission;

  return <View style={s.page}>
    <Screen>
      <View style={s.header}>
        <View style={{flex:1}}>
          <Text style={s.title}>أهلاً يا كابتن</Text>
          <Text style={s.phone}>{d.driver.phone} • ★ {d.driver.rating.toFixed(1)}</Text>
        </View>
        <Pressable onPress={()=>auth.signOut()} style={s.logout}><Text style={s.logoutText}>خروج</Text></Pressable>
      </View>

      <View style={[s.availability,available?s.online:d.driver.status==="on_mission"?s.missionStatus:s.offline]}>
        <Switch
          value={available}
          disabled={d.driver.status==="on_mission"||availability.isPending}
          onValueChange={(value)=>availability.mutate(value)}
          trackColor={{false:"#D8CEC6",true:"#BFE1C9"}}
          thumbColor={available?colors.greenDark:"#fff"}
        />
        <View style={{flex:1}}>
          <Text style={s.avTitle}>{STATUS[d.driver.status]??d.driver.status}</Text>
          <Text style={s.avText}>
            {d.driver.status==="on_mission"
              ?"لا يمكن إيقاف التوفر أثناء مهمة نشطة."
              :available
                ?"المهام الجديدة ممكن تظهر لك دلوقتي."
                :"فعّل التوفر علشان تشوف المهام الجديدة."}
          </Text>
        </View>
        <Text style={s.avIcon}>{d.driver.status==="on_mission"?"🛵":available?"●":"○"}</Text>
      </View>

      <View style={s.stats}>
        <Stat value={d.available_missions_count} label="مهام متاحة"/>
        <Stat value={d.completed_missions_count} label="مهمات مكتملة"/>
        <Stat value={d.driver.rating.toFixed(1)} label="التقييم"/>
      </View>

      {active?<Pressable onPress={()=>router.push(`/missions/${active.id}`)} style={s.activeCard}>
        <View style={{flex:1}}>
          <Text style={s.activeTitle}>مهمتك الحالية</Text>
          <Text style={s.activeStage}>{MISSION[active.status]??active.status}</Text>
          <Text style={s.activeMeta}>{active.pickup_name} • {active.dropoff?.area??"العنوان محفوظ"}</Text>
        </View>
        <Text style={s.arrow}>‹</Text>
      </Pressable>:null}

      {!active&&available?<Pressable onPress={()=>router.push("/missions")} style={s.offerCard}>
        <Text style={s.offerCount}>{d.available_missions_count}</Text>
        <View style={{flex:1}}>
          <Text style={s.offerTitle}>مهام جاهزة للاستلام</Text>
          <Text style={s.offerText}>افتح القائمة واختار مهمة واحدة فقط.</Text>
        </View>
        <Text style={s.arrow}>‹</Text>
      </Pressable>:null}

      <Text style={s.section}>قواعد سريعة</Text>
      <View style={s.rules}>
        <Rule icon="1" text="مهمة نشطة واحدة فقط في نفس الوقت."/>
        <Rule icon="2" text="أكد الوصول للشيف قبل تأكيد استلام الطلب."/>
        <Rule icon="3" text="إثبات التوصيل إلزامي قبل إنهاء المهمة."/>
        <Rule icon="4" text="بيانات العميل المباشرة لا تظهر للمندوب."/>
      </View>
    </Screen>
    <BottomNav active="home"/>
  </View>;
}

function Stat({value,label}:{value:number|string;label:string}){
  return <View style={s.stat}><Text style={s.statValue}>{value}</Text><Text style={s.statLabel}>{label}</Text></View>;
}
function Rule({icon,text}:{icon:string;text:string}){
  return <View style={s.rule}><View style={s.ruleIcon}><Text style={s.ruleIconText}>{icon}</Text></View><Text style={s.ruleText}>{text}</Text></View>;
}
const s=StyleSheet.create({
  page:{flex:1,backgroundColor:colors.canvas},
  header:{flexDirection:"row-reverse",alignItems:"center",gap:12,paddingTop:10,paddingBottom:16},
  title:{fontSize:24,fontWeight:"900",color:colors.ink,textAlign:"right"},phone:{fontSize:10,color:colors.muted,textAlign:"right",marginTop:4},
  logout:{borderWidth:1,borderColor:colors.border,borderRadius:radius.pill,paddingHorizontal:11,paddingVertical:7},logoutText:{fontSize:10,color:colors.muted,fontWeight:"800"},
  availability:{flexDirection:"row-reverse",alignItems:"center",gap:12,borderRadius:radius.card,padding:16},online:{backgroundColor:colors.greenSoft},offline:{backgroundColor:colors.soft},missionStatus:{backgroundColor:colors.blueSoft},
  avTitle:{fontSize:17,fontWeight:"900",color:colors.ink,textAlign:"right",writingDirection:"rtl"},avText:{fontSize:10,color:colors.muted,textAlign:"right",writingDirection:"rtl",marginTop:4,lineHeight:16},avIcon:{fontSize:26},
  stats:{flexDirection:"row-reverse",borderWidth:1,borderColor:colors.border,borderRadius:radius.md,backgroundColor:colors.surface,marginTop:12},
  stat:{flex:1,alignItems:"center",paddingVertical:12},statValue:{fontSize:19,fontWeight:"900",color:colors.ink},statLabel:{fontSize:9,color:colors.muted,marginTop:2},
  activeCard:{flexDirection:"row-reverse",alignItems:"center",gap:12,backgroundColor:colors.orangeSoft,borderRadius:radius.card,padding:16,marginTop:18},
  activeTitle:{fontSize:12,color:colors.muted,textAlign:"right"},activeStage:{fontSize:18,fontWeight:"900",color:colors.orangeDark,textAlign:"right",marginTop:3},
  activeMeta:{fontSize:10,color:colors.muted,textAlign:"right",writingDirection:"rtl",marginTop:4},arrow:{fontSize:30,color:colors.muted},
  offerCard:{flexDirection:"row-reverse",alignItems:"center",gap:12,borderWidth:1,borderColor:colors.border,borderRadius:radius.card,backgroundColor:colors.surface,padding:16,marginTop:18},
  offerCount:{fontSize:30,fontWeight:"900",color:colors.orangeDark},offerTitle:{fontWeight:"900",color:colors.ink,textAlign:"right",writingDirection:"rtl"},offerText:{fontSize:10,color:colors.muted,textAlign:"right",writingDirection:"rtl",marginTop:3},
  section:{fontSize:16,fontWeight:"900",color:colors.ink,textAlign:"right",marginTop:22,marginBottom:8},
  rules:{borderWidth:1,borderColor:colors.border,borderRadius:radius.md,backgroundColor:colors.surface,paddingHorizontal:13},
  rule:{minHeight:55,flexDirection:"row-reverse",alignItems:"center",gap:10,borderBottomWidth:1,borderBottomColor:colors.border},
  ruleIcon:{width:26,height:26,borderRadius:13,backgroundColor:colors.orangeSoft,alignItems:"center",justifyContent:"center"},ruleIconText:{fontWeight:"900",color:colors.orangeDark},
  ruleText:{flex:1,color:colors.muted,fontSize:11,textAlign:"right",writingDirection:"rtl"},
});
