import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { router } from "expo-router";
import { Screen } from "../../src/ui/Screen";
import { EmptyState, ErrorState, LoadingState } from "../../src/ui/StateViews";
import { useLoyalty } from "../../src/hooks/useCommerce";
import { colors, radius, spacing } from "../../src/theme/tokens";

export default function LoyaltyScreen() {
  const q = useLoyalty();
  if (q.isLoading) return <Screen><LoadingState label="بنحسب نقاطك..." /></Screen>;
  if (q.isError || !q.data) return <Screen><ErrorState message="تعذر تحميل النقاط." /></Screen>;
  const data = q.data;
  return (
    <Screen>
      <View style={s.header}><Text onPress={() => router.back()} style={s.back}>→</Text><Text style={s.title}>نقاط بيتنا</Text></View>
      <View style={s.hero}>
        <Text style={s.heroLabel}>رصيدك الحالي</Text>
        <Text style={s.points}>{data.balance_points}</Text>
        <Text style={s.heroLabel}>نقطة</Text>
      </View>
      <View style={s.stats}>
        <Stat value={data.lifetime_earned_points} label="إجمالي المكتسب" />
        <Stat value={data.lifetime_redeemed_points} label="إجمالي المستخدم" />
      </View>
      <Text style={s.section}>سجل النقاط</Text>
      {data.transactions.length ? data.transactions.map((tx) => (
        <View key={tx.id} style={s.row}>
          <View style={{ flex: 1 }}>
            <Text style={s.desc}>{tx.description}</Text>
            <Text style={s.date}>{new Date(tx.created_at).toLocaleDateString("ar-EG")}</Text>
          </View>
          <Text style={[s.amount, tx.points < 0 && s.minus]}>{tx.points > 0 ? "+" : ""}{tx.points}</Text>
        </View>
      )) : <EmptyState title="لسه مفيش حركة نقاط" body="النقاط بتظهر بعد توصيل الطلبات المؤهلة." />}
    </Screen>
  );
}

function Stat({ value, label }: { value: number; label: string }) {
  return <View style={s.stat}><Text style={s.statValue}>{value}</Text><Text style={s.statLabel}>{label}</Text></View>;
}
const s=StyleSheet.create({
  header:{flexDirection:"row-reverse",alignItems:"center",gap:12,paddingTop:14,paddingBottom:18},
  back:{fontSize:26},title:{flex:1,fontSize:22,fontWeight:"900",color:colors.ink,textAlign:"right"},
  hero:{backgroundColor:colors.orange,borderRadius:radius.card,padding:24,alignItems:"center"},
  heroLabel:{color:"#FFF4E8",fontSize:12},points:{color:"#fff",fontSize:44,fontWeight:"900",marginVertical:2},
  stats:{flexDirection:"row-reverse",borderWidth:1,borderColor:colors.border,borderRadius:radius.md,marginTop:14,backgroundColor:colors.surface},
  stat:{flex:1,alignItems:"center",paddingVertical:13},statValue:{fontWeight:"900",fontSize:17,color:colors.ink},statLabel:{fontSize:10,color:colors.muted,marginTop:3},
  section:{fontSize:17,fontWeight:"900",color:colors.ink,textAlign:"right",marginTop:22,marginBottom:8},
  row:{flexDirection:"row-reverse",alignItems:"center",gap:12,borderBottomWidth:1,borderBottomColor:colors.border,paddingVertical:12},
  desc:{fontWeight:"800",color:colors.ink,textAlign:"right",writingDirection:"rtl"},date:{fontSize:10,color:colors.muted,textAlign:"right",marginTop:3},
  amount:{fontSize:17,fontWeight:"900",color:colors.greenDark},minus:{color:colors.danger}
});
