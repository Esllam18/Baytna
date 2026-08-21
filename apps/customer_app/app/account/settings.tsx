import React, { useEffect, useState } from "react";
import { Alert, StyleSheet, Switch, Text, View } from "react-native";
import { router } from "expo-router";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Screen } from "../../src/ui/Screen";
import { PrimaryButton } from "../../src/ui/PrimaryButton";
import { LoadingState } from "../../src/ui/StateViews";
import { useNotificationPreferences, useCurrentSubscription, useSubscriptionPlans } from "../../src/hooks/useAccount";
import { customerApi } from "../../src/api";
import { useAuth } from "../../src/auth/AuthProvider";
import { queryKeys } from "../../src/query/keys";
import { egp } from "../../src/utils/format";
import { colors, radius, spacing } from "../../src/theme/tokens";

export default function SettingsScreen() {
  const prefs = useNotificationPreferences();
  const subscription = useCurrentSubscription();
  const plans = useSubscriptionPlans();
  const qc = useQueryClient();
  const auth = useAuth();

  const [state, setState] = useState({
    user_id: "",
    push_enabled: true,
    sms_enabled: false,
    order_updates: true,
    support_updates: true,
    marketing_enabled: false,
  });

  useEffect(() => {
    if (prefs.data) setState(prefs.data);
  }, [prefs.data]);

  const savePrefs = useMutation({
    mutationFn: () => customerApi.updateNotificationPreferences(state),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.notificationPreferences }),
  });
  const cancelSub = useMutation({
    mutationFn: () => customerApi.cancelSubscription(),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.currentSubscription }),
  });

  if (prefs.isLoading) return <Screen><LoadingState /></Screen>;

  const toggle = (key: keyof typeof state) => {
    if (key === "user_id") return;
    setState((current) => ({ ...current, [key]: !current[key] }));
  };

  return (
    <Screen>
      <View style={s.header}><Text onPress={() => router.back()} style={s.back}>→</Text><Text style={s.title}>الإعدادات</Text></View>

      <Text style={s.section}>الإشعارات</Text>
      <View style={s.card}>
        <Toggle label="Push Notifications" note="التحديثات الفورية على الجهاز" value={state.push_enabled} onChange={() => toggle("push_enabled")} />
        <Toggle label="SMS" note="رسائل للحالات المهمة فقط" value={state.sms_enabled} onChange={() => toggle("sms_enabled")} />
        <Toggle label="تحديثات الطلب" note="تجهيز، مندوب، توصيل" value={state.order_updates} onChange={() => toggle("order_updates")} />
        <Toggle label="تحديثات الدعم" note="ردود فريق بيتنا على التذاكر" value={state.support_updates} onChange={() => toggle("support_updates")} />
        <Toggle label="عروض وتسويق" note="مغلق افتراضيًا ويمكنك تشغيله" value={state.marketing_enabled} onChange={() => toggle("marketing_enabled")} />
      </View>
      <PrimaryButton label="حفظ إعدادات الإشعارات" onPress={() => savePrefs.mutate()} loading={savePrefs.isPending} />

      <Text style={s.section}>اشتراك بيتنا</Text>
      <View style={s.subscription}>
        {subscription.data ? (
          <>
            <Text style={s.subName}>{subscription.data.plan_name}</Text>
            <Text style={s.subMeta}>فعال حتى {new Date(subscription.data.ends_at).toLocaleDateString("ar-EG")}</Text>
            <Text
              onPress={() => Alert.alert("إلغاء الاشتراك", "سيتم إيقاف الاشتراك الحالي حسب قواعد الخطة.", [
                { text: "رجوع", style: "cancel" },
                { text: "إلغاء الاشتراك", style: "destructive", onPress: () => cancelSub.mutate() },
              ])}
              style={s.cancelSub}
            >
              إلغاء الاشتراك
            </Text>
          </>
        ) : (
          <>
            <Text style={s.subName}>لا يوجد اشتراك نشط</Text>
            <Text style={s.subMeta}>الخطط المتاحة تظهر هنا للتعريف بالمزايا.</Text>
          </>
        )}
        {plans.data?.map((plan) => (
          <View key={plan.id} style={s.plan}>
            <View style={{ flex: 1 }}>
              <Text style={s.planName}>{plan.name}</Text>
              <Text style={s.planMeta}>{plan.description}</Text>
            </View>
            <Text style={s.planPrice}>{egp(plan.price_minor)}</Text>
          </View>
        ))}
      </View>

      <Text style={s.section}>الجلسة</Text>
      <View style={s.signoutBox}>
        <Text style={s.signoutText}>تسجيل الخروج يمسح الجلسة من الجهاز ويلغي Refresh Token الحالي.</Text>
        <Text onPress={() => auth.signOut()} style={s.signout}>تسجيل الخروج</Text>
      </View>
    </Screen>
  );
}

function Toggle({ label, note, value, onChange }: { label: string; note: string; value: boolean; onChange(): void }) {
  return (
    <View style={s.toggle}>
      <Switch
        value={value}
        onValueChange={onChange}
        trackColor={{ false: "#D9D0C7", true: "#FFD6AF" }}
        thumbColor={value ? colors.orange : "#F7F2ED"}
      />
      <View style={{ flex: 1 }}>
        <Text style={s.toggleLabel}>{label}</Text>
        <Text style={s.toggleNote}>{note}</Text>
      </View>
    </View>
  );
}

const s=StyleSheet.create({
  header:{flexDirection:"row-reverse",alignItems:"center",gap:12,paddingTop:14,paddingBottom:18},
  back:{fontSize:26},title:{flex:1,fontSize:22,fontWeight:"900",color:colors.ink,textAlign:"right"},
  section:{fontSize:16,fontWeight:"900",color:colors.ink,textAlign:"right",marginTop:18,marginBottom:8},
  card:{borderWidth:1,borderColor:colors.border,borderRadius:radius.md,backgroundColor:colors.surface,paddingHorizontal:13,marginBottom:12},
  toggle:{minHeight:64,flexDirection:"row-reverse",alignItems:"center",gap:12,borderBottomWidth:1,borderBottomColor:colors.border},
  toggleLabel:{fontWeight:"900",color:colors.ink,textAlign:"right",writingDirection:"rtl"},
  toggleNote:{fontSize:10,color:colors.muted,textAlign:"right",writingDirection:"rtl",marginTop:2},
  subscription:{borderWidth:1,borderColor:colors.border,borderRadius:radius.md,backgroundColor:colors.surface,padding:14},
  subName:{fontWeight:"900",fontSize:16,color:colors.ink,textAlign:"right",writingDirection:"rtl"},
  subMeta:{fontSize:11,color:colors.muted,textAlign:"right",writingDirection:"rtl",marginTop:4},
  cancelSub:{color:colors.danger,fontSize:11,fontWeight:"800",textAlign:"right",marginTop:10},
  plan:{flexDirection:"row-reverse",alignItems:"center",gap:10,borderTopWidth:1,borderTopColor:colors.border,paddingTop:12,marginTop:12},
  planName:{fontWeight:"900",color:colors.ink,textAlign:"right",writingDirection:"rtl"},
  planMeta:{fontSize:10,color:colors.muted,textAlign:"right",writingDirection:"rtl",marginTop:2},
  planPrice:{fontWeight:"900",color:colors.orangeDark},
  signoutBox:{backgroundColor:colors.dangerSoft,borderRadius:radius.md,padding:14},
  signoutText:{fontSize:11,color:colors.muted,textAlign:"right",writingDirection:"rtl",lineHeight:18},
  signout:{color:colors.danger,fontWeight:"900",textAlign:"right",marginTop:10}
});
