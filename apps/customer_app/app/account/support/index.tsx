import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { router } from "expo-router";
import { Screen } from "../../../src/ui/Screen";
import { PrimaryButton } from "../../../src/ui/PrimaryButton";
import { EmptyState, ErrorState, LoadingState } from "../../../src/ui/StateViews";
import { useSupportTickets } from "../../../src/hooks/useAccount";
import { colors, radius, spacing } from "../../../src/theme/tokens";

const STATUS_LABELS: Record<string, string> = {
  new: "جديد",
  assigned: "تم التعيين",
  investigating: "قيد المراجعة",
  awaiting_customer: "بانتظار ردك",
  awaiting_internal: "مراجعة داخلية",
  resolved: "تم الحل",
  closed: "مغلق",
};

export default function SupportListScreen() {
  const q = useSupportTickets();

  if (q.isLoading) return <Screen><LoadingState label="بنجيب طلبات الدعم..." /></Screen>;
  if (q.isError) return <Screen><ErrorState message="تعذر تحميل الدعم." /></Screen>;

  return (
    <Screen>
      <View style={s.header}>
        <Text onPress={() => router.back()} style={s.back}>→</Text>
        <Text style={s.title}>الدعم والمساعدة</Text>
      </View>

      <PrimaryButton label="+ افتح طلب دعم" onPress={() => router.push("/account/support/new")} />

      <View style={s.list}>
        {q.data?.length ? q.data.map((ticket) => (
          <Pressable key={ticket.id} onPress={() => router.push(`/account/support/${ticket.id}`)} style={s.card}>
            <View style={s.row}>
              <View style={{ flex: 1 }}>
                <Text style={s.subject}>{ticket.subject}</Text>
                <Text style={s.meta}>{categoryLabel(ticket.category)} • {new Date(ticket.created_at).toLocaleDateString("ar-EG")}</Text>
              </View>
              <View style={[s.status, ["resolved", "closed"].includes(ticket.status) && s.statusDone]}>
                <Text style={[s.statusText, ["resolved", "closed"].includes(ticket.status) && s.statusDoneText]}>
                  {STATUS_LABELS[ticket.status] ?? ticket.status}
                </Text>
              </View>
            </View>
            <Text style={s.description} numberOfLines={2}>{ticket.description}</Text>
          </Pressable>
        )) : <EmptyState title="مفيش طلبات دعم" body="لو حصلت مشكلة في طلب أو دفع، افتح تذكرة وهنتابعها معاك." />}
      </View>
    </Screen>
  );
}

function categoryLabel(category: string) {
  const labels: Record<string, string> = {
    food_quality: "جودة الأكل", missing_item: "عنصر ناقص", wrong_item: "طلب خاطئ",
    late_delivery: "تأخير", delivery_issue: "مشكلة توصيل", refund: "استرداد",
    payment: "دفع", app_issue: "التطبيق", other: "أخرى",
  };
  return labels[category] ?? category;
}

const s=StyleSheet.create({
  header:{flexDirection:"row-reverse",alignItems:"center",gap:12,paddingTop:14,paddingBottom:18},
  back:{fontSize:26},title:{flex:1,fontSize:22,fontWeight:"900",color:colors.ink,textAlign:"right"},
  list:{gap:12,marginTop:18},
  card:{borderWidth:1,borderColor:colors.border,borderRadius:radius.md,backgroundColor:colors.surface,padding:14},
  row:{flexDirection:"row-reverse",alignItems:"flex-start",gap:10},
  subject:{fontWeight:"900",color:colors.ink,textAlign:"right",writingDirection:"rtl"},
  meta:{fontSize:10,color:colors.muted,textAlign:"right",marginTop:4,writingDirection:"rtl"},
  description:{color:colors.muted,fontSize:12,lineHeight:18,textAlign:"right",writingDirection:"rtl",marginTop:10},
  status:{backgroundColor:colors.orangeSoft,borderRadius:radius.pill,paddingHorizontal:9,paddingVertical:5},
  statusText:{color:colors.orangeDark,fontSize:9,fontWeight:"800"},
  statusDone:{backgroundColor:colors.greenSoft},statusDoneText:{color:colors.greenDark},
});
