import React from "react";
import {Pressable,StyleSheet,Text,View} from "react-native";
import {router} from "expo-router";
import {useDriverDashboard,useAvailableMissions} from "../../src/hooks/useDriverOps";
import {Screen} from "../../src/ui/Screen";
import {BottomNav} from "../../src/ui/BottomNav";
import {EmptyState,ErrorState,LoadingState} from "../../src/ui/StateViews";
import {colors,radius} from "../../src/theme/tokens";

export default function MissionsScreen(){
  const dashboard=useDriverDashboard();
  const enabled=dashboard.data?.driver.status==="available"&&!dashboard.data?.active_mission;
  const q=useAvailableMissions(Boolean(enabled));

  return <View style={s.page}>
    <Screen>
      <View style={s.header}>
        <Text style={s.title}>المهام المتاحة</Text>
        <Text style={s.meta}>مهمة واحدة فقط في نفس الوقت</Text>
      </View>

      {dashboard.isLoading?<LoadingState label="بنراجع حالة التوفر..."/>:
       dashboard.isError?<ErrorState message="تعذر تحميل حالة المندوب."/>:
       dashboard.data?.active_mission?<Pressable onPress={()=>router.push(`/missions/${dashboard.data!.active_mission!.id}`)} style={s.active}>
        <Text style={s.activeTitle}>عندك مهمة نشطة بالفعل</Text>
        <Text style={s.activeText}>كمّل المهمة الحالية قبل قبول مهمة جديدة.</Text>
       </Pressable>:
       dashboard.data?.driver.status!=="available"?<EmptyState title="أنت غير متاح حاليًا" body="ارجع للرئيسية وفعّل حالة التوفر لعرض المهام."/>:
       q.isLoading?<LoadingState label="بنبحث عن مهام قريبة..."/>:
       q.isError?<ErrorState message="تعذر تحميل المهام المتاحة."/>:
       q.data?.length?q.data.map(m=><Pressable
         key={m.id}
         onPress={()=>router.push({pathname:"/missions/[missionId]",params:{missionId:m.id,preview:"1"}})}
         style={s.card}
       >
        <View style={s.row}>
          <View style={s.icon}><Text style={s.iconText}>🛵</Text></View>
          <View style={{flex:1}}>
            <Text style={s.name}>{m.pickup_name}</Text>
            <Text style={s.metaLine}>استلام: {m.pickup_area}</Text>
            <Text style={s.metaLine}>توصيل: {m.dropoff?.area??"العنوان غير جاهز"}</Text>
          </View>
          <Text style={s.arrow}>‹</Text>
        </View>
        <View style={s.footer}>
          <Text style={s.order}>طلب #{m.order_id.slice(0,8).toUpperCase()}</Text>
          <Text style={[s.ready,m.navigation_ready?s.readyYes:s.readyNo]}>
            {m.navigation_ready?"العنوان جاهز":"العنوان ناقص"}
          </Text>
        </View>
       </Pressable>):<EmptyState title="مفيش مهام جديدة دلوقتي" body="القائمة بتتحدث تلقائيًا. خليك متاح وهتظهر المهام أول ما تكون جاهزة."/>}
    </Screen>
    <BottomNav active="missions"/>
  </View>;
}
const s=StyleSheet.create({
  page:{flex:1,backgroundColor:colors.canvas},
  header:{paddingTop:10,paddingBottom:14},title:{fontSize:23,fontWeight:"900",color:colors.ink,textAlign:"right"},
  meta:{fontSize:10,color:colors.muted,textAlign:"right",marginTop:3},
  active:{backgroundColor:colors.orangeSoft,borderRadius:radius.card,padding:16},
  activeTitle:{fontWeight:"900",color:colors.orangeDark,textAlign:"right",writingDirection:"rtl"},
  activeText:{fontSize:10,color:colors.muted,textAlign:"right",writingDirection:"rtl",marginTop:4},
  card:{borderWidth:1,borderColor:colors.border,borderRadius:radius.md,backgroundColor:colors.surface,padding:14,marginBottom:10},
  row:{flexDirection:"row-reverse",alignItems:"center",gap:11},
  icon:{width:52,height:52,borderRadius:16,backgroundColor:colors.orangeSoft,alignItems:"center",justifyContent:"center"},
  iconText:{fontSize:26},name:{fontWeight:"900",color:colors.ink,textAlign:"right",writingDirection:"rtl"},
  metaLine:{fontSize:10,color:colors.muted,textAlign:"right",writingDirection:"rtl",marginTop:3},arrow:{fontSize:28,color:colors.muted},
  footer:{flexDirection:"row-reverse",justifyContent:"space-between",alignItems:"center",borderTopWidth:1,borderTopColor:colors.border,marginTop:11,paddingTop:9},
  order:{fontSize:9,color:colors.muted},ready:{fontSize:9,fontWeight:"900"},readyYes:{color:colors.greenDark},readyNo:{color:colors.danger},
});
