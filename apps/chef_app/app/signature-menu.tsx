import React, { useState } from "react";
import { Image, Pressable, StyleSheet, Switch, Text, View } from "react-native";
import { router } from "expo-router";
import * as ImagePicker from "expo-image-picker";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { chefApi } from "../src/api";
import { chefKeys } from "../src/query/keys";
import { useSignatureMenu } from "../src/hooks/useChefOps";
import { uploadDishImage, LocalDishImage } from "../src/media/uploadDishImage";
import { egp } from "../src/utils/format";
import { Screen } from "../src/ui/Screen";
import { PrimaryButton } from "../src/ui/PrimaryButton";
import { FormField } from "../src/ui/FormField";
import { ErrorState, LoadingState } from "../src/ui/StateViews";
import { colors, radius } from "../src/theme/tokens";

export default function SignatureMenuScreen() {
  const q=useSignatureMenu();
  const qc=useQueryClient();
  const [showForm,setShowForm]=useState(false);
  const [name,setName]=useState("");
  const [description,setDescription]=useState("");
  const [category,setCategory]=useState("أطباق رئيسية");
  const [price,setPrice]=useState("");
  const [notice,setNotice]=useState("24");
  const [special,setSpecial]=useState(true);
  const [uploadingDishId,setUploadingDishId]=useState<string|null>(null);
  const [localPreview,setLocalPreview]=useState<Record<string,string>>({});
  const [mediaError,setMediaError]=useState("");

  const refresh=()=>qc.invalidateQueries({queryKey:chefKeys.signatureMenu});
  const create=useMutation({
    mutationFn:()=>chefApi.createDish({
      name:name.trim(),description:description.trim(),category:category.trim(),
      base_price_minor:Math.round(Number(price)*100),
      prep_notice_hours:Number(notice||0),
      is_special_order_available:special,
      display_order:0,
    }),
    onSuccess:async()=>{await refresh();setShowForm(false);setName("");setDescription("");setPrice("");},
  });
  const toggle=useMutation({
    mutationFn:({id,active}:{id:string;active:boolean})=>chefApi.updateDish(id,{is_active:active}),
    onSuccess:refresh,
  });
  const media=useMutation({
    mutationFn:({dishId,image}:{dishId:string;image:LocalDishImage})=>uploadDishImage(dishId,image),
    onSuccess:async()=>{setUploadingDishId(null);await refresh();},
    onError:()=>setUploadingDishId(null),
  });

  const chooseDishImage=async(dishId:string)=>{
    setMediaError("");
    const permission=await ImagePicker.requestMediaLibraryPermissionsAsync();
    if(!permission.granted){
      setMediaError("اسمح بالوصول للصور علشان تضيف صورة للطبق.");
      return;
    }
    const result=await ImagePicker.launchImageLibraryAsync({
      mediaTypes:["images"],
      quality:.82,
      allowsEditing:true,
      aspect:[4,3],
    });
    if(result.canceled)return;
    const asset=result.assets[0];
    const mimeType=normalizeMime(asset.mimeType,asset.fileName);
    if(!mimeType){
      setMediaError("الصيغة غير مدعومة. استخدم JPG أو PNG أو WebP.");
      return;
    }
    setLocalPreview(cur=>({...cur,[dishId]:asset.uri}));
    setUploadingDishId(dishId);
    media.mutate({
      dishId,
      image:{
        uri:asset.uri,
        fileName:asset.fileName??`dish-${dishId}.jpg`,
        mimeType,
        fileSize:asset.fileSize,
      },
    });
  };

  if (q.isLoading) return <Screen><LoadingState label="بنجيب قائمة التخصص..."/></Screen>;
  if (q.isError) return <Screen><ErrorState message="تعذر تحميل القائمة."/></Screen>;

  return <Screen>
    <View style={s.header}>
      <Text onPress={()=>router.back()} style={s.back}>→</Text>
      <Text style={s.title}>قائمة التخصص</Text>
    </View>

    <PrimaryButton label={showForm?"إخفاء الإضافة":"+ أضف طبق"} onPress={()=>setShowForm(!showForm)}/>

    {showForm?<View style={s.form}>
      <FormField label="اسم الطبق" value={name} onChangeText={setName}/>
      <FormField label="الوصف" value={description} onChangeText={setDescription} multiline/>
      <FormField label="التصنيف" value={category} onChangeText={setCategory}/>
      <View style={s.two}>
        <View style={{flex:1}}>
          <FormField label="السعر بالجنيه" value={price} onChangeText={setPrice} keyboardType="decimal-pad"/>
        </View>
        <View style={{flex:1}}>
          <FormField label="مهلة التحضير (ساعة)" value={notice} onChangeText={setNotice} keyboardType="number-pad"/>
        </View>
      </View>
      <View style={s.switchRow}>
        <Switch value={special} onValueChange={setSpecial}/>
        <Text style={s.switchText}>متاح كطلب خاص</Text>
      </View>
      {create.isError?<Text style={s.error}>راجع اسم الطبق والسعر.</Text>:null}
      <PrimaryButton
        label="حفظ الطبق"
        onPress={()=>create.mutate()}
        loading={create.isPending}
        disabled={!name.trim()||Number(price)<=0}
      />
    </View>:null}

    <Text style={s.section}>الأطباق ({q.data?.length ?? 0})</Text>
    {mediaError?<Text style={s.error}>{mediaError}</Text>:null}

    {q.data?.map(d=><View key={d.id} style={[s.card,!d.is_active&&s.inactive]}>
      <View style={s.row}>
        <Switch value={d.is_active} onValueChange={active=>toggle.mutate({id:d.id,active})}/>
        <View style={{flex:1}}>
          <Text style={s.name}>{d.name}</Text>
          <Text style={s.meta}>{d.category} • تحضير {d.prep_notice_hours} ساعة</Text>
          <Text style={s.special}>{d.is_special_order_available?"متاح للطلبات الخاصة":"غير متاح كطلب خاص"}</Text>
          <Text style={d.media_asset_id?s.imageReady:s.imageMissing}>
            {d.media_asset_id?"صورة الطبق مضافة ✓":"أضف صورة حقيقية قبل الطيار"}
          </Text>
        </View>
        <Text style={s.price}>{egp(d.base_price_minor)}</Text>
      </View>

      <View style={s.mediaRow}>
        {localPreview[d.id]?<Image source={{uri:localPreview[d.id]}} style={s.preview}/>:<View style={s.placeholder}><Text style={s.placeholderText}>🍲</Text></View>}
        <Pressable
          disabled={uploadingDishId===d.id}
          onPress={()=>void chooseDishImage(d.id)}
          style={s.mediaButton}
        >
          <Text style={s.mediaButtonText}>
            {uploadingDishId===d.id?"جاري رفع الصورة...":d.media_asset_id?"تغيير الصورة":"إضافة صورة"}
          </Text>
        </Pressable>
      </View>
    </View>)}
  </Screen>;
}

function normalizeMime(
  mime?:string|null,
  fileName?:string|null,
):LocalDishImage["mimeType"]|null{
  if(mime==="image/jpeg"||mime==="image/png"||mime==="image/webp")return mime;
  const lower=(fileName??"").toLowerCase();
  if(lower.endsWith(".jpg")||lower.endsWith(".jpeg"))return "image/jpeg";
  if(lower.endsWith(".png"))return "image/png";
  if(lower.endsWith(".webp"))return "image/webp";
  return null;
}

const s=StyleSheet.create({
  header:{flexDirection:"row-reverse",alignItems:"center",gap:12,paddingTop:10,paddingBottom:16},
  back:{fontSize:26},
  title:{flex:1,fontSize:22,fontWeight:"900",color:colors.ink,textAlign:"right"},
  form:{gap:12,marginTop:14,borderWidth:1,borderColor:colors.border,borderRadius:radius.card,backgroundColor:colors.surface,padding:14},
  two:{flexDirection:"row-reverse",gap:8},
  switchRow:{flexDirection:"row-reverse",alignItems:"center",gap:10},
  switchText:{fontWeight:"800",color:colors.ink,writingDirection:"rtl"},
  error:{color:colors.danger,textAlign:"center",writingDirection:"rtl",marginBottom:8},
  section:{fontSize:17,fontWeight:"900",color:colors.ink,textAlign:"right",marginTop:20,marginBottom:9},
  card:{borderWidth:1,borderColor:colors.border,borderRadius:radius.md,backgroundColor:colors.surface,padding:13,marginBottom:9},
  inactive:{opacity:.55},
  row:{flexDirection:"row-reverse",alignItems:"center",gap:10},
  name:{fontWeight:"900",color:colors.ink,textAlign:"right",writingDirection:"rtl"},
  meta:{fontSize:10,color:colors.muted,textAlign:"right",writingDirection:"rtl",marginTop:3},
  special:{fontSize:9,color:colors.orangeDark,textAlign:"right",marginTop:3},
  imageReady:{fontSize:9,color:colors.greenDark,textAlign:"right",marginTop:3,fontWeight:"800"},
  imageMissing:{fontSize:9,color:colors.danger,textAlign:"right",marginTop:3},
  price:{fontWeight:"900",color:colors.orangeDark},
  mediaRow:{flexDirection:"row-reverse",alignItems:"center",gap:10,borderTopWidth:1,borderTopColor:colors.border,marginTop:11,paddingTop:11},
  preview:{width:58,height:48,borderRadius:11,backgroundColor:colors.soft},
  placeholder:{width:58,height:48,borderRadius:11,backgroundColor:colors.orangeSoft,alignItems:"center",justifyContent:"center"},
  placeholderText:{fontSize:24},
  mediaButton:{flex:1,borderWidth:1,borderColor:colors.orange,borderRadius:12,paddingVertical:10,alignItems:"center",backgroundColor:colors.orangeSoft},
  mediaButtonText:{fontSize:10,color:colors.orangeDark,fontWeight:"900"},
});
