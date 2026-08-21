import React, { useEffect, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { useQuery } from "@tanstack/react-query";
import { customerApi } from "../../src/api";
import { queryKeys } from "../../src/query/keys";
import { Screen } from "../../src/ui/Screen";
import { PrimaryButton } from "../../src/ui/PrimaryButton";
import { ErrorState, LoadingState } from "../../src/ui/StateViews";
import { colors, radius, spacing } from "../../src/theme/tokens";
import { clearPendingPaymentOrder, getPendingPaymentOrder } from "../../src/payment/pendingPayment";
import { egp } from "../../src/utils/format";

export default function PaymentResultScreen() {
  const params = useLocalSearchParams<{ orderId?: string }>();
  const [orderId, setOrderId] = useState(String(params.orderId ?? ''));

  useEffect(() => {
    if (orderId) return;
    void getPendingPaymentOrder().then(id => { if (id) setOrderId(id); });
  }, [orderId]);

  const state = useQuery({
    queryKey: ['payment-result', orderId],
    enabled: Boolean(orderId),
    queryFn: async () => {
      const [payment, order] = await Promise.all([
        customerApi.payment(orderId),
        customerApi.order(orderId),
      ]);
      return { payment, order };
    },
    refetchInterval: (query) => {
      const status = query.state.data?.payment.status;
      return status === 'succeeded' || status === 'failed' || status === 'cancelled' ? false : 4_000;
    },
  });

  useEffect(() => {
    const status = state.data?.payment.status;
    if (status === 'succeeded' || status === 'failed' || status === 'cancelled') {
      void clearPendingPaymentOrder();
    }
  }, [state.data?.payment.status]);

  if (!orderId) return <Screen><ErrorState message="لم نقدر نحدد الطلب المرتبط بالدفع."/><PrimaryButton label="اذهب للطلبات" onPress={() => router.replace('/orders')} /></Screen>;
  if (state.isLoading) return <Screen><LoadingState label="بنراجع نتيجة الدفع مع بيتنا..." /></Screen>;
  if (state.isError || !state.data) return <Screen><ErrorState message="تعذر التأكد من حالة الدفع. افتح طلباتك وحاول مرة أخرى."/><PrimaryButton label="عرض الطلبات" onPress={() => router.replace('/orders')} /></Screen>;

  const { payment, order } = state.data;
  const success = payment.status === 'succeeded';
  const failed = payment.status === 'failed' || payment.status === 'cancelled';

  return <Screen contentStyle={s.center}>
    <View style={[s.iconWrap, success ? s.successBg : failed ? s.failBg : s.waitBg]}><Text style={s.icon}>{success ? '✓' : failed ? '!' : '…'}</Text></View>
    <Text style={s.title}>{success ? 'تم الدفع بنجاح' : failed ? 'الدفع لم يكتمل' : 'بنأكد الدفع'}</Text>
    <Text style={s.body}>{success ? 'طلبك اتأكد، والشيف هيبدأ تجهيز أكلك حسب حالة الطلب.' : failed ? 'لم يتم تأكيد الدفع. لم نعتبر التحويل ناجحًا من صفحة الرجوع فقط.' : 'مستنيين تأكيد Paymob على الـBackend. الصفحة بتتحدث تلقائيًا.'}</Text>
    <View style={s.summary}><Row label="رقم الطلب" value={order.id.slice(0,8).toUpperCase()} /><Row label="المبلغ" value={egp(payment.amount_minor)} /><Row label="حالة الدفع" value={payment.status} /></View>
    {success ? <PrimaryButton label="تابع طلبك لحظة بلحظة" onPress={() => router.replace(`/orders/${order.id}/tracking`)} /> : <PrimaryButton label="عرض تفاصيل الطلب" onPress={() => router.replace(`/orders/${order.id}`)} />}
    {!success && !failed ? <Pressable onPress={() => state.refetch()}><Text style={s.link}>تحقق الآن</Text></Pressable> : null}
  </Screen>;
}
function Row({label,value}:{label:string;value:string}){return <View style={s.row}><Text style={s.label}>{label}</Text><Text style={s.value}>{value}</Text></View>}
const s=StyleSheet.create({center:{justifyContent:'center',paddingTop:40},iconWrap:{width:78,height:78,borderRadius:39,alignSelf:'center',alignItems:'center',justifyContent:'center'},successBg:{backgroundColor:colors.greenSoft},failBg:{backgroundColor:colors.dangerSoft},waitBg:{backgroundColor:colors.orangeSoft},icon:{fontSize:38,fontWeight:'900',color:colors.ink},title:{fontSize:25,fontWeight:'900',color:colors.ink,textAlign:'center',writingDirection:'rtl',marginTop:18},body:{fontSize:13,lineHeight:21,color:colors.muted,textAlign:'center',writingDirection:'rtl',marginTop:8,marginBottom:18},summary:{borderWidth:1,borderColor:colors.border,borderRadius:radius.md,backgroundColor:colors.surface,padding:spacing.md,gap:10,marginBottom:20},row:{flexDirection:'row-reverse',justifyContent:'space-between'},label:{color:colors.muted,writingDirection:'rtl'},value:{fontWeight:'900',color:colors.ink},link:{color:colors.orangeDark,fontWeight:'900',textAlign:'center',marginTop:16,writingDirection:'rtl'}});
