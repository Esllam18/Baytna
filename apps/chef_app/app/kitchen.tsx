import React, { useEffect, useMemo, useState } from "react";
import { Alert, Pressable, StyleSheet, Switch, Text, TextInput, View } from "react-native";
import { router } from "expo-router";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { chefApi } from "../src/api";
import { chefKeys } from "../src/query/keys";
import { useSignatureMenu, useTodayMenu } from "../src/hooks/useChefOps";
import { localDateISO } from "../src/utils/date";
import { egp } from "../src/utils/format";
import { Screen } from "../src/ui/Screen";
import { BottomNav } from "../src/ui/BottomNav";
import { PrimaryButton } from "../src/ui/PrimaryButton";
import { LoadingState, ErrorState, EmptyState } from "../src/ui/StateViews";
import { colors, radius } from "../src/theme/tokens";

type Draft = {
  selected: boolean;
  quantity: string;
  maxPerOrder: string;
};

export default function KitchenScreen() {
  const date=localDateISO();
  const today=useTodayMenu(date);
  const signature=useSignatureMenu();
  const qc=useQueryClient();
  const [draft,setDraft]=useState<Record<string,Draft>>({});

  useEffect(()=>{
    if (!signature.data) return;
    const current = new Map((today.data?.items ?? []).map(x=>[x.dish_id,x]));
    const next:Record<string,Draft>={};
    for (const dish of signature.data.filter(x=>x.is_active)) {
      const row=current.get(dish.id);
      next[dish.id]={
        selected:Boolean(row),
        quantity:String(row?.quantity_total ?? 5),
        maxPerOrder:String(row?.max_per_order ?? 5),
      };
    }
    setDraft(next);
  },[signature.data,today.data?.items]);

  const refresh=()=>Promise.all([
    qc.invalidateQueries({queryKey:chefKeys.todayMenu(date)}),
    qc.invalidateQueries({queryKey:chefKeys.dashboard(date)}),
  ]);

  const open=useMutation({
    mutationFn:()=>chefApi.openKitchen({
      service_date:date,
      cutoff_at:null,
      delivery_window_start:"12:00",
      delivery_window_end:"20:00",
    }),
    onSuccess:refresh,
  });
  const close=useMutation({
    mutationFn:()=>chefApi.closeKitchen(date),
    onSuccess:refresh,
  });
  const publish=useMutation({
    mutationFn:()=>{
      const items=(signature.data ?? [])
        .filter(d=>d.is_active && draft[d.id]?.selected)
        .map(d=>({
          dish_id:d.id,
          price_minor:null,
          quantity_total:Math.max(0,Number(draft[d.id]?.quantity||0)),
          max_per_order:Math.max(1,Number(draft[d.id]?.maxPerOrder||1)),
          is_visible:true,
        }));
      if (!items.length) throw new Error("select_at_least_one");
      return chefApi.replaceTodayMenu(date,items);
    },
    onSuccess:refresh,
  });

  if (today.isLoading||signature.isLoading) return <View style={s.page}><Screen><LoadingState label="بنجهز مطبخ اليوم..."/></Screen><BottomNav active="kitchen"/></View>;
  if (today.isError||signature.isError||!today.data) return <View style={s.page}><Screen><ErrorState message="تعذر تحميل مطبخ اليوم."/></Screen><BottomNav active="kitchen"/></View>;

  const isOpen=today.data.kitchen_status==="open";
  const selectedCount=Object.values(draft).filter(x=>x.selected).length;

  return <View style={s.page}>
    <Screen>
      <View style={s.header}>
        <View style={{flex:1}}>
          <Text style={s.title}>مطبخ اليوم</Text>
          <Text style={s.meta}>{new Date(date).toLocaleDateString("ar-EG",{weekday:"long",day:"numeric",month:"long"})}</Text>
        </View>
        <Pressable onPress={()=>router.push("/signature-menu")} style={s.signatureLink}><Text style={s.signatureText}>قائمة التخصص</Text></Pressable>
      </View>

      <View style={[s.status,isOpen?s.statusOpen:s.statusClosed]}>
        <View style={{flex:1}}>
          <Text style={s.statusTitle}>{isOpen?"المطبخ مفتوح":"المطبخ مغلق"}</Text>
          <Text style={s.statusText}>
            {isOpen
              ? `${today.data.items.length} طبق منشور • ${today.data.delivery_window_start ?? "—"}–${today.data.delivery_window_end ?? "—"}`
              :"افتح المطبخ ثم اختار أكلات وكميات اليوم."}
          </Text>
        </View>
        {isOpen?
          <Pressable onPress={()=>Alert.alert("إغلاق المطبخ","سيظل سجل اليوم محفوظًا، لكن لن يظهر كمفتوح للعملاء.",[
            {text:"رجوع",style:"cancel"},
            {text:"إغلاق",style:"destructive",onPress:()=>close.mutate()},
          ])}><Text style={s.closeText}>إغلاق</Text></Pressable>
          :<Pressable onPress={()=>open.mutate()}><Text style={s.openText}>فتح المطبخ</Text></Pressable>}
      </View>

      <View style={s.summary}>
        <Mini value={today.data.items.length} label="منشور"/>
        <Mini value={today.data.items.reduce((sum,x)=>sum+x.quantity_available,0)} label="متاح"/>
        <Mini value={today.data.items.filter(x=>x.quantity_available===0).length} label="نفد"/>
      </View>

      <Text style={s.section}>اختار أكلات اليوم</Text>
      {(signature.data?.filter(x=>x.is_active).length ?? 0)>0 ? signature.data!.filter(x=>x.is_active).map(dish=>{
        const row=draft[dish.id] ?? {selected:false,quantity:"5",maxPerOrder:"5"};
        const live=today.data!.items.find(x=>x.dish_id===dish.id);
        return <View key={dish.id} style={[s.dish,row.selected&&s.dishSelected]}>
          <View style={s.dishTop}>
            <Switch value={row.selected} onValueChange={selected=>setDraft(cur=>({...cur,[dish.id]:{...row,selected}}))}/>
            <View style={{flex:1}}>
              <Text style={s.dishName}>{dish.name}</Text>
              <Text style={s.dishMeta}>{dish.category} • {egp(dish.base_price_minor)}</Text>
              {live?<Text style={live.quantity_available>0?s.live:s.sold}>{live.availability_label}</Text>:null}
            </View>
            <Text style={s.icon}>🍲</Text>
          </View>
          {row.selected?<View style={s.inputs}>
            <View style={s.inputWrap}><Text style={s.inputLabel}>كمية اليوم</Text><TextInput keyboardType="number-pad" value={row.quantity} onChangeText={quantity=>setDraft(cur=>({...cur,[dish.id]:{...row,quantity}}))} style={s.input}/></View>
            <View style={s.inputWrap}><Text style={s.inputLabel}>حد الطلب</Text><TextInput keyboardType="number-pad" value={row.maxPerOrder} onChangeText={maxPerOrder=>setDraft(cur=>({...cur,[dish.id]:{...row,maxPerOrder}}))} style={s.input}/></View>
          </View>:null}
        </View>;
      }):<EmptyState title="قائمة التخصص فارغة" body="أضف أطباقك الأساسية الأول، وبعدها اختار منها مطبخ اليوم."/>}

      {publish.isError?<Text style={s.error}>اختار طبق واحد على الأقل وتأكد من الكميات.</Text>:null}
      <PrimaryButton
        label={`نشر مطبخ اليوم (${selectedCount})`}
        onPress={()=>publish.mutate()}
        loading={publish.isPending}
        disabled={!isOpen||selectedCount===0}
      />
    </Screen>
    <BottomNav active="kitchen"/>
  </View>;
}

function Mini({value,label}:{value:number;label:string}) {
  return <View style={s.mini}><Text style={s.miniValue}>{value}</Text><Text style={s.miniLabel}>{label}</Text></View>;
}
const s=StyleSheet.create({
  page:{flex:1,backgroundColor:colors.canvas},
  header:{flexDirection:"row-reverse",alignItems:"center",gap:12,paddingTop:10,paddingBottom:15},
  title:{fontSize:23,fontWeight:"900",color:colors.ink,textAlign:"right"},
  meta:{fontSize:10,color:colors.muted,textAlign:"right",marginTop:4},
  signatureLink:{borderWidth:1,borderColor:colors.border,borderRadius:radius.pill,paddingHorizontal:11,paddingVertical:8},
  signatureText:{fontSize:10,fontWeight:"800",color:colors.orangeDark},
  status:{flexDirection:"row-reverse",alignItems:"center",gap:12,borderRadius:radius.card,padding:15},
  statusOpen:{backgroundColor:colors.greenSoft},statusClosed:{backgroundColor:colors.soft},
  statusTitle:{fontSize:17,fontWeight:"900",color:colors.ink,textAlign:"right"},
  statusText:{fontSize:10,color:colors.muted,textAlign:"right",writingDirection:"rtl",marginTop:4},
  closeText:{color:colors.danger,fontWeight:"900"},openText:{color:colors.greenDark,fontWeight:"900"},
  summary:{flexDirection:"row-reverse",borderWidth:1,borderColor:colors.border,borderRadius:radius.md,marginTop:12,backgroundColor:colors.surface},
  mini:{flex:1,alignItems:"center",paddingVertical:11},
  miniValue:{fontSize:18,fontWeight:"900",color:colors.ink},miniLabel:{fontSize:9,color:colors.muted,marginTop:2},
  section:{fontSize:17,fontWeight:"900",color:colors.ink,textAlign:"right",marginTop:20,marginBottom:9},
  dish:{borderWidth:1,borderColor:colors.border,borderRadius:radius.md,backgroundColor:colors.surface,padding:13,marginBottom:10},
  dishSelected:{borderColor:"#F0B878",backgroundColor:"#FFF9F0"},
  dishTop:{flexDirection:"row-reverse",alignItems:"center",gap:10},
  dishName:{fontWeight:"900",color:colors.ink,textAlign:"right",writingDirection:"rtl"},
  dishMeta:{fontSize:10,color:colors.muted,textAlign:"right",marginTop:3},
  icon:{fontSize:27},live:{fontSize:9,color:colors.greenDark,textAlign:"right",marginTop:3},sold:{fontSize:9,color:colors.danger,textAlign:"right",marginTop:3},
  inputs:{flexDirection:"row-reverse",gap:9,marginTop:12},
  inputWrap:{flex:1},inputLabel:{fontSize:9,color:colors.muted,textAlign:"right",marginBottom:4},
  input:{minHeight:42,borderWidth:1,borderColor:colors.border,borderRadius:12,backgroundColor:"#fff",paddingHorizontal:10,textAlign:"center",fontWeight:"900"},
  error:{color:colors.danger,textAlign:"center",marginBottom:8,writingDirection:"rtl"},
});
