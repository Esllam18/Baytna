import React from "react";
import { Alert, Pressable, StyleSheet, Text, View } from "react-native";
import { router } from "expo-router";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { customerApi } from "../src/api";
import { useCart } from "../src/hooks/useCommerce";
import { queryKeys } from "../src/query/keys";
import { Screen } from "../src/ui/Screen";
import { CartLineItem } from "../src/ui/CartLineItem";
import { PrimaryButton } from "../src/ui/PrimaryButton";
import { EmptyState, ErrorState, LoadingState } from "../src/ui/StateViews";
import { colors, radius, spacing } from "../src/theme/tokens";
import { egp } from "../src/utils/format";

export default function CartScreen() {
  const cart = useCart();
  const qc = useQueryClient();
  const update = useMutation({
    mutationFn: ({ id, quantity }: { id: string; quantity: number }) => customerApi.updateCartItem(id, quantity),
    onSuccess: (data) => qc.setQueryData(queryKeys.cart, data),
  });
  const remove = useMutation({
    mutationFn: (id: string) => customerApi.removeCartItem(id),
    onSuccess: (data) => qc.setQueryData(queryKeys.cart, data),
  });
  const clear = useMutation({
    mutationFn: () => customerApi.clearCart(),
    onSuccess: (data) => qc.setQueryData(queryKeys.cart, data),
  });

  if (cart.isLoading) return <Screen><LoadingState label="بنفتح سلتك..." /></Screen>;
  if (cart.isError || !cart.data) return <Screen><ErrorState message="تعذر تحميل السلة." /></Screen>;
  const data = cart.data;
  const busy = update.isPending || remove.isPending || clear.isPending;

  if (!data.items.length) {
    return <Screen>
      <Header title="سلة بيتنا" />
      <EmptyState title="السلة فاضية" body="اختار شيف ووجبة من مطبخ اليوم وارجع لنا هنا." />
      <PrimaryButton label="شوف الشيفات" onPress={() => router.replace('/chefs')} />
    </Screen>;
  }

  return <Screen>
    <Header title="سلة بيتنا" action="تفريغ" onAction={() => Alert.alert('تفريغ السلة', 'متأكد إنك عايز تحذف كل الوجبات؟', [
      { text: 'إلغاء', style: 'cancel' },
      { text: 'تفريغ', style: 'destructive', onPress: () => clear.mutate() },
    ])} />
    <View style={s.info}><Text style={s.infoText}>طلبك من شيف واحد • تاريخ الخدمة {data.service_date ?? 'اليوم'}</Text></View>
    <View style={{ marginTop: spacing.md }}>
      {data.items.map(item => <CartLineItem
        key={item.id}
        item={item}
        busy={busy}
        onQuantity={(quantity) => update.mutate({ id: item.id, quantity: Math.min(quantity, item.max_per_order) })}
        onRemove={() => remove.mutate(item.id)}
      />)}
    </View>
    {(update.isError || remove.isError || clear.isError) ? <Text style={s.error}>تعذر تحديث السلة. حاول مرة أخرى.</Text> : null}
    <View style={s.total}><Text style={s.totalLabel}>إجمالي الوجبات</Text><Text style={s.totalValue}>{egp(data.subtotal_minor)}</Text></View>
    <PrimaryButton label="كمّل للعنوان والدفع" onPress={() => router.push('/checkout')} disabled={busy} />
    <Pressable onPress={() => router.push('/chefs')}><Text style={s.more}>+ أضف وجبات تانية</Text></Pressable>
  </Screen>;
}

function Header({ title, action, onAction }: { title: string; action?: string; onAction?: () => void }) {
  return <View style={s.header}><Pressable onPress={() => router.back()} style={s.back}><Text style={s.backText}>→</Text></Pressable><Text style={s.title}>{title}</Text>{action ? <Pressable onPress={onAction}><Text style={s.action}>{action}</Text></Pressable> : <View style={{ width: 42 }} />}</View>;
}

const s = StyleSheet.create({
  header:{flexDirection:'row-reverse',alignItems:'center',justifyContent:'space-between',paddingTop:12,marginBottom:12},back:{width:42,height:42,borderRadius:21,backgroundColor:colors.surface,borderWidth:1,borderColor:colors.border,alignItems:'center',justifyContent:'center'},backText:{fontSize:24,color:colors.ink},title:{fontSize:22,fontWeight:'900',color:colors.ink,writingDirection:'rtl'},action:{color:colors.danger,fontWeight:'800'},info:{padding:12,borderRadius:radius.md,backgroundColor:colors.orangeSoft},infoText:{color:colors.orangeDark,textAlign:'right',writingDirection:'rtl',fontSize:12},error:{color:colors.danger,textAlign:'center',writingDirection:'rtl',marginVertical:8},total:{flexDirection:'row-reverse',justifyContent:'space-between',alignItems:'center',paddingVertical:18,borderTopWidth:1,borderTopColor:colors.border},totalLabel:{fontWeight:'900',fontSize:16,color:colors.ink,writingDirection:'rtl'},totalValue:{fontWeight:'900',fontSize:20,color:colors.orangeDark},more:{color:colors.orangeDark,fontWeight:'800',textAlign:'center',marginTop:16,writingDirection:'rtl'}
});
