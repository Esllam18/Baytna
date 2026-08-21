import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { router } from "expo-router";
import { Screen } from "../src/ui/Screen";
import { BottomNav } from "../src/ui/BottomNav";
import { LoadingState, ErrorState } from "../src/ui/StateViews";
import { useChefDashboard } from "../src/hooks/useChefOps";
import { useAuth } from "../src/auth/AuthProvider";
import { colors, radius, spacing } from "../src/theme/tokens";
import { localDateISO } from "../src/utils/date";

export default function ChefHomeScreen() {
  const date=localDateISO();
  const q=useChefDashboard(date);
  const auth=useAuth();

  if (q.isLoading) return <View style={s.page}><Screen><LoadingState label="بنجهز لوحة المطبخ..."/></Screen><BottomNav active="home"/></View>;
  if (q.isError||!q.data) return <View style={s.page}><Screen><ErrorState message="تعذر تحميل لوحة الشيف."/></Screen><BottomNav active="home"/></View>;

  const d=q.data;
  const activeOrders=d.orders_new+d.orders_accepted+d.orders_preparing+d.orders_packaging+d.orders_ready;
  const specialNeedsAction=d.special_review+d.special_counter_offer;

  return <View style={s.page}>
    <Screen>
      <View style={s.header}>
        <View style={{flex:1}}>
          <Text style={s.hello}>أهلاً، {d.chef.display_name}</Text>
          <Text style={s.meta}>{d.chef.specialty} • {d.chef.area}</Text>
        </View>
        <Pressable onPress={()=>auth.signOut()} style={s.logout}><Text style={s.logoutText}>خروج</Text></Pressable>
      </View>

      <View style={[s.kitchen,d.kitchen_status==="open"?s.open:s.closed]}>
        <View style={{flex:1}}>
          <Text style={s.kitchenTitle}>
            {d.kitchen_status==="open"?"مطبخك مفتوح النهارده":"المطبخ مغلق النهارده"}
          </Text>
          <Text style={s.kitchenText}>
            {d.today_items} طبق • {d.available_quantity} وحدة متاحة • {d.sold_out_items} نفدت
          </Text>
        </View>
        <Text style={s.kitchenIcon}>{d.kitchen_status==="open"?"🔥":"🌙"}</Text>
      </View>

      <Text style={s.section}>الطلبات الحالية</Text>
      <View style={s.grid}>
        <Metric label="جديدة" value={d.orders_new} tone="orange"/>
        <Metric label="مقبولة" value={d.orders_accepted}/>
        <Metric label="جاري الطبخ" value={d.orders_preparing}/>
        <Metric label="تغليف" value={d.orders_packaging}/>
        <Metric label="جاهزة" value={d.orders_ready} tone="green"/>
        <Metric label="الكل" value={activeOrders}/>
      </View>

      <Text style={s.section}>إجراءات سريعة</Text>
      <View style={s.actions}>
        <Action icon="🍲" title="مطبخ اليوم" note={`${d.today_items} طبق منشور`} onPress={()=>router.push("/kitchen")}/>
        <Action icon="▤" title="طلبات التنفيذ" note={`${activeOrders} طلب في المسار`} onPress={()=>router.push("/orders")}/>
        <Action icon="★" title="طلبات خاصة" note={`${specialNeedsAction} تحتاج مراجعة`} onPress={()=>router.push("/special-orders")}/>
        <Action icon="📅" title="جدول الطلبات الخاصة" note={`${d.special_scheduled} مجدولة`} onPress={()=>router.push("/schedule")}/>
        <Action icon="📖" title="قائمة التخصص" note={`${d.signature_dishes} طبق`} onPress={()=>router.push("/signature-menu")}/>
      </View>

      {specialNeedsAction>0?<Pressable onPress={()=>router.push("/special-orders")} style={s.alert}>
        <Text style={s.alertTitle}>عندك {specialNeedsAction} طلب خاص محتاج رد</Text>
        <Text style={s.alertText}>راجع الموعد والسعر قبل انتهاء انتظار العميل.</Text>
      </Pressable>:null}
    </Screen>
    <BottomNav active="home"/>
  </View>;
}

function Metric({label,value,tone}:{label:string;value:number;tone?:"orange"|"green"}) {
  return <View style={[s.metric,tone==="orange"&&s.metricOrange,tone==="green"&&s.metricGreen]}>
    <Text style={s.metricValue}>{value}</Text>
    <Text style={s.metricLabel}>{label}</Text>
  </View>;
}
function Action({icon,title,note,onPress}:{icon:string;title:string;note:string;onPress():void}) {
  return <Pressable onPress={onPress} style={s.action}>
    <Text style={s.actionIcon}>{icon}</Text>
    <View style={{flex:1}}>
      <Text style={s.actionTitle}>{title}</Text>
      <Text style={s.actionNote}>{note}</Text>
    </View>
    <Text style={s.arrow}>‹</Text>
  </Pressable>;
}
const s=StyleSheet.create({
  page:{flex:1,backgroundColor:colors.canvas},
  header:{flexDirection:"row-reverse",alignItems:"center",gap:12,paddingTop:10,paddingBottom:16},
  hello:{fontSize:23,fontWeight:"900",color:colors.ink,textAlign:"right",writingDirection:"rtl"},
  meta:{fontSize:11,color:colors.muted,textAlign:"right",writingDirection:"rtl",marginTop:4},
  logout:{borderWidth:1,borderColor:colors.border,borderRadius:radius.pill,paddingHorizontal:11,paddingVertical:7},
  logoutText:{fontSize:10,color:colors.muted,fontWeight:"800"},
  kitchen:{flexDirection:"row-reverse",alignItems:"center",borderRadius:radius.card,padding:17},
  open:{backgroundColor:colors.greenSoft},closed:{backgroundColor:colors.soft},
  kitchenTitle:{fontSize:17,fontWeight:"900",color:colors.ink,textAlign:"right",writingDirection:"rtl"},
  kitchenText:{fontSize:10,color:colors.muted,textAlign:"right",writingDirection:"rtl",marginTop:4},
  kitchenIcon:{fontSize:34},
  section:{fontSize:17,fontWeight:"900",color:colors.ink,textAlign:"right",writingDirection:"rtl",marginTop:22,marginBottom:9},
  grid:{flexDirection:"row-reverse",flexWrap:"wrap",gap:8},
  metric:{width:"31%",backgroundColor:colors.surface,borderWidth:1,borderColor:colors.border,borderRadius:radius.md,paddingVertical:12,alignItems:"center"},
  metricOrange:{backgroundColor:colors.orangeSoft,borderColor:"#F1C08C"},
  metricGreen:{backgroundColor:colors.greenSoft,borderColor:"#BADCC5"},
  metricValue:{fontSize:20,fontWeight:"900",color:colors.ink},
  metricLabel:{fontSize:9,color:colors.muted,marginTop:2},
  actions:{borderWidth:1,borderColor:colors.border,borderRadius:radius.card,backgroundColor:colors.surface,paddingHorizontal:13},
  action:{minHeight:68,flexDirection:"row-reverse",alignItems:"center",gap:11,borderBottomWidth:1,borderBottomColor:colors.border},
  actionIcon:{fontSize:24},actionTitle:{fontWeight:"900",color:colors.ink,textAlign:"right",writingDirection:"rtl"},
  actionNote:{fontSize:10,color:colors.muted,textAlign:"right",writingDirection:"rtl",marginTop:2},
  arrow:{fontSize:27,color:colors.muted},
  alert:{backgroundColor:colors.orangeSoft,borderRadius:radius.md,padding:14,marginTop:16},
  alertTitle:{color:colors.orangeDark,fontWeight:"900",textAlign:"right",writingDirection:"rtl"},
  alertText:{color:colors.muted,fontSize:10,textAlign:"right",writingDirection:"rtl",marginTop:4},
});
