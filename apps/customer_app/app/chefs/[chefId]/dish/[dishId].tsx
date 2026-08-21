import React, { useMemo, useState } from "react";
import { Alert, Pressable, StyleSheet, Text, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Screen } from "../../../../src/ui/Screen";
import { PrimaryButton } from "../../../../src/ui/PrimaryButton";
import { useChef, useSignatureMenu, useTodayMenu } from "../../../../src/hooks/useCustomerHome";
import { customerApi } from "../../../../src/api";
import { ApiClientError } from "../../../../src/api/http";
import { LoadingState, ErrorState } from "../../../../src/ui/StateViews";
import { colors, radius, spacing } from "../../../../src/theme/tokens";
import { egp } from "../../../../src/utils/format";
import { queryKeys } from "../../../../src/query/keys";
import { FavoriteButton } from "../../../../src/ui/FavoriteButton";
export default function DishScreen(){const p=useLocalSearchParams<{chefId:string;dishId:string;dailyMenuItemId?:string}>();const chefId=String(p.chefId??"");const dishId=String(p.dishId??"");const dailyId=String(p.dailyMenuItemId??"");const chef=useChef(chefId);const today=useTodayMenu(chefId);const sig=useSignatureMenu(chefId);const [qty,setQty]=useState(1);const [addErrorText,setAddErrorText]=useState("");const qc=useQueryClient();const daily=useMemo(()=>today.data?.items.find(x=>x.id===dailyId||x.dish_id===dishId),[today.data,dailyId,dishId]);const dish=useMemo(()=>sig.data?.find(x=>x.id===dishId),[sig.data,dishId]);const add=useMutation({
  mutationFn:()=>{if(!daily)throw new Error("الوجبة غير متاحة حاليًا.");return customerApi.addCartItem(daily.id,qty)},
  onMutate:()=>setAddErrorText(""),
  onSuccess:async()=>{await qc.invalidateQueries({queryKey:queryKeys.cart});router.push("/cart")},
  onError:(error)=>{
    const message=error instanceof Error?error.message:"تعذر إضافة الوجبة للسلة.";
    setAddErrorText(message);
    if(error instanceof ApiClientError && (error.code==="cart_multiple_chefs_not_allowed" || error.code==="cart_multiple_service_dates_not_allowed")){
      Alert.alert("السلة الحالية",message,[
        {text:"إلغاء",style:"cancel"},
        {text:"تفريغ السلة وإضافة الوجبة",style:"destructive",onPress:async()=>{
          try{
            await customerApi.clearCart();
            if(!daily)return;
            const cart=await customerApi.addCartItem(daily.id,qty);
            qc.setQueryData(queryKeys.cart,cart);
            setAddErrorText("");
            router.push("/cart");
          }catch(retryError){
            setAddErrorText(retryError instanceof Error?retryError.message:"تعذر إضافة الوجبة للسلة.");
          }
        }}
      ]);
    }
  }
});if(chef.isLoading||today.isLoading||sig.isLoading)return <Screen><LoadingState label="بنجهز تفاصيل الوجبة..."/></Screen>;if(chef.isError||(!daily&&!dish))return <Screen><ErrorState message="تعذر تحميل تفاصيل الوجبة"/></Screen>;const name=daily?.name??dish!.name;const description=daily?.description??dish!.description;const category=daily?.category??dish!.category;const price=daily?.price_minor??dish!.base_price_minor;const available=Boolean(daily&&daily.quantity_available>0&&daily.status!=="sold_out");const max=daily?Math.max(1,Math.min(daily.max_per_order,daily.quantity_available)):1;return <Screen contentStyle={{paddingHorizontal:0}}><View style={s.hero}><Text style={s.heroEmoji}>🍲</Text><Pressable style={s.back} onPress={()=>router.back()}><Text style={s.backText}>→</Text></Pressable><FavoriteButton kind="dish" id={dishId}/></View><View style={s.body}><View style={s.split}><View style={{flex:1}}><Text style={s.name}>{name}</Text><Text style={s.chef}>من {chef.data?.display_name}</Text></View><Text style={s.price}>{egp(price)}</Text></View><Text style={s.description}>{description}</Text><View style={s.info}><Pill text={category}/>{daily?<Pill text={daily.availability_label}/>:null}{dish?.is_special_order_available&&!daily?<Pill text={`طلب خاص • ${dish.prep_notice_hours} ساعة`}/>:null}</View>{available?<><View style={s.qty}><Pressable onPress={()=>setQty(Math.max(1,qty-1))} style={s.qtyBtn}><Text style={s.qtyBtnText}>−</Text></Pressable><Text style={s.qtyValue}>{qty}</Text><Pressable onPress={()=>setQty(Math.min(max,qty+1))} style={s.qtyBtn}><Text style={s.qtyBtnText}>+</Text></Pressable></View>{addErrorText?<Text style={s.error}>{addErrorText}</Text>:null}<PrimaryButton label={`أضف للسلة • ${egp(price*qty)}`} onPress={()=>add.mutate()} loading={add.isPending}/>{dish?.is_special_order_available?<Pressable onPress={()=>router.push({pathname:"/special-orders/new",params:{chefId,dishId}})}><Text style={s.specialLink}>عايزها لموعد تاني؟ اعمل طلب خاص</Text></Pressable>:null}</>:<View style={s.unavailable}><Text style={s.unavailableTitle}>{daily?"نفدت الكمية اليوم":"متاحة كطلب خاص"}</Text><Text style={s.unavailableBody}>{daily?"تقدر ترجع لقائمة الشيف وتشوف وجبات تانية.":"حدد موعد مناسب وابعت الطلب للشيف للموافقة قبل الدفع."}</Text>{dish?.is_special_order_available?<View style={{marginTop:12}}><PrimaryButton label="اطلبها كطلب خاص" onPress={()=>router.push({pathname:"/special-orders/new",params:{chefId,dishId}})}/></View>:null}</View>}</View></Screen>}
function Pill({text}:{text:string}){return <View style={s.pill}><Text style={s.pillText}>{text}</Text></View>}
const s=StyleSheet.create({hero:{height:300,backgroundColor:"#FFE0BD",alignItems:"center",justifyContent:"center",position:"relative"},heroEmoji:{fontSize:112},back:{position:"absolute",top:18,right:18,width:42,height:42,borderRadius:21,backgroundColor:"rgba(255,255,255,.92)",alignItems:"center",justifyContent:"center"},backText:{fontSize:25},body:{padding:spacing.lg},split:{flexDirection:"row-reverse",justifyContent:"space-between",gap:12,alignItems:"flex-start"},name:{fontSize:24,fontWeight:"900",color:colors.ink,textAlign:"right",writingDirection:"rtl"},chef:{color:colors.muted,fontSize:12,marginTop:4,textAlign:"right",writingDirection:"rtl"},price:{color:colors.orangeDark,fontSize:21,fontWeight:"900"},description:{color:colors.muted,fontSize:14,lineHeight:22,textAlign:"right",writingDirection:"rtl",marginTop:14},info:{flexDirection:"row-reverse",flexWrap:"wrap",gap:8,marginTop:12},pill:{backgroundColor:colors.soft,borderRadius:12,paddingVertical:8,paddingHorizontal:10},pillText:{fontSize:11,color:colors.ink,writingDirection:"rtl"},qty:{flexDirection:"row",alignItems:"center",justifyContent:"center",gap:20,marginVertical:20},qtyBtn:{width:38,height:38,borderRadius:11,borderWidth:1,borderColor:colors.border,backgroundColor:colors.surface,alignItems:"center",justifyContent:"center"},qtyBtnText:{fontSize:23,color:colors.ink},qtyValue:{fontSize:20,fontWeight:"900",minWidth:24,textAlign:"center"},error:{color:colors.danger,textAlign:"center",marginBottom:10,writingDirection:"rtl"},unavailable:{marginTop:22,padding:16,borderRadius:radius.md,backgroundColor:colors.orangeSoft},unavailableTitle:{fontWeight:"900",color:colors.orangeDark,textAlign:"right",writingDirection:"rtl"},unavailableBody:{fontSize:12,color:colors.muted,textAlign:"right",writingDirection:"rtl",marginTop:5,lineHeight:19},specialLink:{color:colors.orangeDark,fontWeight:"900",fontSize:12,textAlign:"center",writingDirection:"rtl",marginTop:14}});
