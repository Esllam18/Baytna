import React from "react";
import {Pressable,StyleSheet,Text,View} from "react-native";
import {router} from "expo-router";
import {useMissionHistory} from "../src/hooks/useDriverOps";
import {Screen} from "../src/ui/Screen";
import {BottomNav} from "../src/ui/BottomNav";
import {EmptyState,ErrorState,LoadingState} from "../src/ui/StateViews";
import {colors,radius} from "../src/theme/tokens";

export default function DriverHistoryScreen(){
  const q=useMissionHistory();

  return <View style={s.page}>
    <Screen>
      <View style={s.header}>
        <Text style={s.title}>سجل المهام</Text>
        <Text style={s.meta}>المهام المكتملة والملغية المرتبطة بحسابك</Text>
      </View>
      {q.isLoading?<LoadingState label="بنجيب سجل المهام..."/>:
       q.isError?<ErrorState message="تعذر تحميل السجل."/>:
       q.data?.length?q.data.map(m=><Pressable key={m.id} onPress={()=>router.push(`/missions/${m.id}`)} style={s.card}>
        <View style={s.row}>
          <View style={{flex:1}}>
            <Text style={s.name}>{m.pickup_name}</Text>
            <Text style={s.metaLine}>{m.pickup_area} → {m.dropoff?.area??"—"}</Text>
          </View>
          <View style={[s.badge,m.status==="delivered"?s.done:s.cancelled]}>
            <Text style={s.badgeText}>{m.status==="delivered"?"تم التوصيل":"ملغية"}</Text>
          </View>
        </View>
        <View style={s.footer}>
          <Text style={s.order}>#{m.order_id.slice(0,8).toUpperCase()}</Text>
          <Text style={s.date}>{new Date(m.delivered_at??m.created_at).toLocaleString("ar-EG")}</Text>
        </View>
        {m.delivery_proof_type?<Text style={s.proof}>إثبات: {m.delivery_proof_type}</Text>:null}
       </Pressable>):<EmptyState title="لسه مفيش مهام مكتملة" body="بعد أول توصيل ناجح هتلاقي تفاصيل المهمة هنا."/>}
    </Screen>
    <BottomNav active="history"/>
  </View>;
}
const s=StyleSheet.create({
  page:{flex:1,backgroundColor:colors.canvas},
  header:{paddingTop:10,paddingBottom:14},title:{fontSize:23,fontWeight:"900",color:colors.ink,textAlign:"right"},
  meta:{fontSize:10,color:colors.muted,textAlign:"right",writingDirection:"rtl",marginTop:3},
  card:{borderWidth:1,borderColor:colors.border,borderRadius:radius.md,backgroundColor:colors.surface,padding:14,marginBottom:10},
  row:{flexDirection:"row-reverse",alignItems:"center",gap:10},name:{fontWeight:"900",color:colors.ink,textAlign:"right",writingDirection:"rtl"},
  metaLine:{fontSize:10,color:colors.muted,textAlign:"right",writingDirection:"rtl",marginTop:3},
  badge:{borderRadius:radius.pill,paddingHorizontal:9,paddingVertical:6},done:{backgroundColor:colors.greenSoft},cancelled:{backgroundColor:colors.dangerSoft},
  badgeText:{fontSize:9,fontWeight:"900",color:colors.ink},
  footer:{flexDirection:"row-reverse",justifyContent:"space-between",borderTopWidth:1,borderTopColor:colors.border,marginTop:10,paddingTop:9},
  order:{fontSize:9,color:colors.muted},date:{fontSize:9,color:colors.muted},
  proof:{fontSize:9,color:colors.orangeDark,fontWeight:"800",textAlign:"right",marginTop:6},
});
