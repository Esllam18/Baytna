import React, { useEffect, useMemo, useState } from "react";
import { Linking, Pressable, StyleSheet, Text, TextInput, View } from "react-native";
import { router } from "expo-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { customerApi } from "../src/api";
import { useAddresses, useCart, useLoyalty } from "../src/hooks/useCommerce";
import { queryKeys } from "../src/query/keys";
import { Screen } from "../src/ui/Screen";
import { PrimaryButton } from "../src/ui/PrimaryButton";
import { PriceSummary } from "../src/ui/PriceSummary";
import { EmptyState, ErrorState, LoadingState } from "../src/ui/StateViews";
import { colors, radius, spacing } from "../src/theme/tokens";
import { setPendingPaymentOrder } from "../src/payment/pendingPayment";

export default function CheckoutScreen() {
  const cart = useCart();
  const addresses = useAddresses();
  const loyalty = useLoyalty();
  const qc = useQueryClient();
  const [selectedAddress, setSelectedAddress] = useState<string>('');
  const [couponDraft, setCouponDraft] = useState('');
  const [loyaltyDraft, setLoyaltyDraft] = useState('0');
  const [coupon, setCoupon] = useState('');
  const [points, setPoints] = useState(0);
  const [showNewAddress, setShowNewAddress] = useState(false);
  const [createdOrderId, setCreatedOrderId] = useState('');
  const [newAddress, setNewAddress] = useState({ label: 'البيت', area: '6 أكتوبر', street: '', building: '', floor: '', apartment: '' });

  useEffect(() => {
    if (!selectedAddress && addresses.data?.length) {
      setSelectedAddress((addresses.data.find(x => x.is_default) ?? addresses.data[0]).id);
    }
  }, [addresses.data, selectedAddress]);

  const cartId = cart.data?.id ?? '';
  const quote = useQuery({
    queryKey: queryKeys.pricing(cartId, coupon, points),
    queryFn: () => customerApi.pricingQuote(cartId, coupon || null, points),
    enabled: Boolean(cartId && cart.data?.items.length),
  });

  const createAddress = useMutation({
    mutationFn: () => customerApi.createAddress({ ...newAddress, is_default: !addresses.data?.length }),
    onSuccess: async (created) => {
      await qc.invalidateQueries({ queryKey: queryKeys.addresses });
      setSelectedAddress(created.id);
      setShowNewAddress(false);
    },
  });

  const checkout = useMutation({
    mutationFn: async () => {
      if (!cart.data?.items.length) throw new Error('empty_cart');
      if (!selectedAddress) throw new Error('address_required');
      const order = await customerApi.createOrder(cart.data.id, selectedAddress, coupon || null, points);
      setCreatedOrderId(order.id);
      const payment = await customerApi.createPaymentIntent(order.id, `mobile-checkout-${order.id}-${Date.now()}`);
      await setPendingPaymentOrder(order.id);
      return { order, payment };
    },
    onSuccess: async ({ order, payment }) => {
      await Promise.all([
        qc.invalidateQueries({ queryKey: queryKeys.cart }),
        qc.invalidateQueries({ queryKey: queryKeys.orders }),
      ]);
      if (payment.checkout_url) {
        await Linking.openURL(payment.checkout_url);
      }
      router.replace({ pathname: '/payment/result', params: { orderId: order.id } });
    },
  });

  if (cart.isLoading || addresses.isLoading || loyalty.isLoading) return <Screen><LoadingState label="بنحسب الطلب..." /></Screen>;
  if (cart.isError || addresses.isError || !cart.data) return <Screen><ErrorState message="تعذر تجهيز صفحة الدفع." /></Screen>;
  if (!cart.data.items.length) return <Screen><EmptyState title="السلة فاضية" /><PrimaryButton label="ارجع للسلة" onPress={() => router.replace('/cart')} /></Screen>;

  const maxPoints = Math.max(0, Math.min(Number(loyalty.data?.balance_points ?? 0), 1_000_000));
  const checkoutErrorCode = (checkout.error as { code?: string } | null)?.code;
  const checkoutErrorMessage = checkoutErrorCode === 'expansion_capacity_unavailable'
    ? 'المنطقة وصلت لحد التشغيل الحالي أو لسه خارج نسبة الـRollout. جرّب مرة تانية بعد شوية.'
    : checkoutErrorCode === 'delivery_address_required'
      ? 'اختار عنوان التوصيل قبل تأكيد الطلب.'
      : createdOrderId
        ? 'تم إنشاء الطلب لكن تعذر بدء الدفع. افتح الطلب لإعادة المحاولة بدون إنشاء طلب جديد.'
        : 'تعذر إنشاء الطلب أو بدء الدفع. راجع العنوان والسعر وحاول مرة أخرى.';

  return <Screen>
    <View style={s.header}><Pressable onPress={() => router.back()} style={s.back}><Text style={s.backText}>→</Text></Pressable><Text style={s.title}>إتمام الطلب</Text><View style={{width:42}} /></View>

    <Text style={s.sectionTitle}>عنوان التوصيل</Text>
    {addresses.data?.map(a => <Pressable key={a.id} onPress={() => setSelectedAddress(a.id)} style={[s.address, selectedAddress === a.id && s.addressSelected]}>
      <View style={[s.radio, selectedAddress === a.id && s.radioActive]} />
      <View style={{ flex: 1 }}><Text style={s.addressTitle}>{a.label || 'عنوان التوصيل'}</Text><Text style={s.addressBody}>{[a.area,a.street,a.building ? `مبنى ${a.building}` : null,a.apartment ? `شقة ${a.apartment}` : null].filter(Boolean).join('، ')}</Text></View>
    </Pressable>)}
    <Pressable onPress={() => setShowNewAddress(!showNewAddress)}><Text style={s.link}>+ أضف عنوان جديد</Text></Pressable>
    {showNewAddress ? <View style={s.form}>
      <Input placeholder="اسم العنوان" value={newAddress.label} onChangeText={v => setNewAddress(x => ({...x,label:v}))} />
      <Input placeholder="المنطقة" value={newAddress.area} onChangeText={v => setNewAddress(x => ({...x,area:v}))} />
      <Input placeholder="الشارع" value={newAddress.street} onChangeText={v => setNewAddress(x => ({...x,street:v}))} />
      <View style={s.inline}><Input compact placeholder="المبنى" value={newAddress.building} onChangeText={v => setNewAddress(x => ({...x,building:v}))} /><Input compact placeholder="الشقة" value={newAddress.apartment} onChangeText={v => setNewAddress(x => ({...x,apartment:v}))} /></View>
      {createAddress.isError ? <Text style={s.error}>تعذر حفظ العنوان.</Text> : null}
      <PrimaryButton label="حفظ العنوان" loading={createAddress.isPending} disabled={!newAddress.area.trim()} onPress={() => createAddress.mutate()} />
    </View> : null}

    <Text style={s.sectionTitle}>الخصومات</Text>
    <View style={s.fieldRow}><TextInput value={couponDraft} onChangeText={setCouponDraft} placeholder="كود الخصم" autoCapitalize="characters" style={s.field}/><Pressable style={s.apply} onPress={() => setCoupon(couponDraft.trim().toUpperCase())}><Text style={s.applyText}>تطبيق</Text></Pressable></View>
    <Text style={s.helper}>رصيد نقاطك: {maxPoints} نقطة</Text>
    <View style={s.fieldRow}><TextInput value={loyaltyDraft} onChangeText={setLoyaltyDraft} placeholder="0" keyboardType="number-pad" style={s.field}/><Pressable style={s.apply} onPress={() => setPoints(Math.min(maxPoints, Math.max(0, Number.parseInt(loyaltyDraft || '0',10) || 0)))}><Text style={s.applyText}>استخدم</Text></Pressable></View>

    <Text style={s.sectionTitle}>ملخص السعر</Text>
    {quote.isLoading ? <LoadingState label="بنحسب السعر النهائي..." /> : quote.isError || !quote.data ? <ErrorState message="الكوبون أو نقاط الولاء غير صالحة، أو تعذر حساب السعر." /> : <PriceSummary quote={quote.data} />}

    <View style={s.paybox}><Text style={s.payTitle}>الدفع الآمن عبر Paymob</Text><Text style={s.payBody}>هنفتح صفحة الدفع المستضافة. بيتنا لا يخزن بيانات البطاقة، والـBackend هو اللي يؤكد نجاح الدفع من الـwebhook.</Text></View>
    {checkout.isError ? <><Text style={s.error}>{checkoutErrorMessage}</Text>{createdOrderId ? <Pressable onPress={() => router.replace(`/orders/${createdOrderId}`)}><Text style={s.link}>افتح الطلب وكمّل الدفع</Text></Pressable> : null}</> : null}
    <PrimaryButton label="أنشئ الطلب وادفع" loading={checkout.isPending} disabled={!selectedAddress || !quote.data || quote.isFetching || Boolean(createdOrderId)} onPress={() => checkout.mutate()} />
  </Screen>;
}

function Input({ compact, ...props }: React.ComponentProps<typeof TextInput> & { compact?: boolean }) { return <TextInput {...props} style={[s.input, compact && { flex: 1 }]} textAlign="right" />; }
const s=StyleSheet.create({header:{flexDirection:'row-reverse',justifyContent:'space-between',alignItems:'center',paddingTop:12},back:{width:42,height:42,borderRadius:21,borderWidth:1,borderColor:colors.border,backgroundColor:colors.surface,alignItems:'center',justifyContent:'center'},backText:{fontSize:24},title:{fontSize:22,fontWeight:'900',color:colors.ink,writingDirection:'rtl'},sectionTitle:{fontSize:17,fontWeight:'900',color:colors.ink,textAlign:'right',writingDirection:'rtl',marginTop:spacing.xl,marginBottom:10},address:{flexDirection:'row-reverse',gap:12,alignItems:'center',borderWidth:1,borderColor:colors.border,borderRadius:radius.md,backgroundColor:colors.surface,padding:13,marginBottom:9},addressSelected:{borderColor:colors.orange,backgroundColor:colors.orangePale},radio:{width:18,height:18,borderRadius:9,borderWidth:2,borderColor:colors.border},radioActive:{borderColor:colors.orange,backgroundColor:colors.orange},addressTitle:{fontWeight:'900',textAlign:'right',writingDirection:'rtl',color:colors.ink},addressBody:{fontSize:11,color:colors.muted,textAlign:'right',writingDirection:'rtl',marginTop:3},link:{color:colors.orangeDark,fontWeight:'800',textAlign:'right',writingDirection:'rtl',paddingVertical:8},form:{gap:9,padding:12,borderRadius:radius.md,backgroundColor:colors.soft,marginTop:5},input:{height:46,borderWidth:1,borderColor:colors.border,borderRadius:12,backgroundColor:colors.surface,paddingHorizontal:12,color:colors.ink,writingDirection:'rtl'},inline:{flexDirection:'row-reverse',gap:8},fieldRow:{flexDirection:'row-reverse',gap:8},field:{flex:1,height:46,borderWidth:1,borderColor:colors.border,borderRadius:12,backgroundColor:colors.surface,paddingHorizontal:12,textAlign:'right',writingDirection:'rtl'},apply:{minWidth:74,height:46,borderRadius:12,backgroundColor:colors.orangeSoft,alignItems:'center',justifyContent:'center'},applyText:{fontWeight:'900',color:colors.orangeDark},helper:{fontSize:11,color:colors.muted,textAlign:'right',writingDirection:'rtl',marginVertical:7},paybox:{padding:13,borderRadius:radius.md,backgroundColor:colors.greenSoft,marginVertical:18},payTitle:{fontWeight:'900',color:colors.greenDark,textAlign:'right',writingDirection:'rtl'},payBody:{fontSize:11,lineHeight:18,color:colors.muted,textAlign:'right',writingDirection:'rtl',marginTop:4},error:{color:colors.danger,textAlign:'center',writingDirection:'rtl',marginVertical:8}});
