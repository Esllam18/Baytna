import React,{useState} from "react";
import {Image,Pressable,StyleSheet,Text,View} from "react-native";
import {router,useLocalSearchParams} from "expo-router";
import * as ImagePicker from "expo-image-picker";
import {useMutation,useQueryClient} from "@tanstack/react-query";
import {driverApi} from "../../../src/api";
import {driverKeys} from "../../../src/query/keys";
import {uploadDeliveryProof,LocalImage} from "../../../src/media/uploadDeliveryProof";
import {useMission} from "../../../src/hooks/useDriverOps";
import {Screen} from "../../../src/ui/Screen";
import {PrimaryButton} from "../../../src/ui/PrimaryButton";
import {FormField} from "../../../src/ui/FormField";
import {ErrorState,LoadingState} from "../../../src/ui/StateViews";
import {colors,radius} from "../../../src/theme/tokens";

type ProofType="otp"|"photo"|"manual";

export default function DeliveryProofScreen(){
  const {missionId}=useLocalSearchParams<{missionId:string}>();
  const id=String(missionId??"");
  const q=useMission(id);
  const qc=useQueryClient();
  const [type,setType]=useState<ProofType>("photo");
  const [reference,setReference]=useState("");
  const [image,setImage]=useState<LocalImage|null>(null);
  const [pickerError,setPickerError]=useState("");

  const choosePhoto=async()=>{
    setPickerError("");
    const permission=await ImagePicker.requestCameraPermissionsAsync();
    if(!permission.granted){
      setPickerError("لازم تسمح بالكاميرا علشان تستخدم إثبات صورة.");
      return;
    }

    const result=await ImagePicker.launchCameraAsync({
      mediaTypes:["images"],
      quality:.75,
      allowsEditing:false,
    });
    if(result.canceled)return;

    const asset=result.assets[0];
    const mime=normalizeMime(asset.mimeType,asset.fileName);
    if(!mime){
      setPickerError("صيغة الصورة غير مدعومة. استخدم JPG أو PNG أو WebP.");
      return;
    }

    setImage({
      uri:asset.uri,
      fileName:asset.fileName??`delivery-${id}.jpg`,
      mimeType:mime,
      fileSize:asset.fileSize,
    });
  };

  const deliver=useMutation({
    mutationFn:async()=>{
      if(type==="photo"){
        if(!image)throw new Error("photo_required");
        const asset=await uploadDeliveryProof(image);
        return driverApi.deliver(id,{
          proof_type:"photo",
          media_asset_id:asset.id,
          proof_reference:null,
        });
      }
      return driverApi.deliver(id,{
        proof_type:type,
        proof_reference:reference.trim(),
        media_asset_id:null,
      });
    },
    onSuccess:async()=>{
      await Promise.all([
        qc.invalidateQueries({queryKey:driverKeys.mission(id)}),
        qc.invalidateQueries({queryKey:driverKeys.dashboard}),
        qc.invalidateQueries({queryKey:driverKeys.history}),
        qc.invalidateQueries({queryKey:driverKeys.availableMissions}),
      ]);
      router.replace(`/missions/${id}`);
    },
  });

  if(q.isLoading)return <Screen><LoadingState label="بنجهز إثبات التوصيل..."/></Screen>;
  if(q.isError||!q.data)return <Screen><ErrorState message="تعذر فتح المهمة."/></Screen>;
  if(q.data.status!=="to_customer")return <Screen><ErrorState message="إثبات التوصيل متاح فقط بعد بدء التوصيل للعميل."/></Screen>;

  const valid=type==="photo"?Boolean(image):reference.trim().length>=3;

  return <Screen>
    <View style={s.header}>
      <Text onPress={()=>router.back()} style={s.back}>→</Text>
      <Text style={s.title}>إثبات التوصيل</Text>
    </View>

    <View style={s.warning}>
      <Text style={s.warningTitle}>أنهِي المهمة بعد التسليم الفعلي فقط</Text>
      <Text style={s.warningText}>تسجيل الإثبات يحوّل الطلب إلى تم التوصيل ويعيد حالتك إلى متاح.</Text>
    </View>

    <Text style={s.section}>نوع الإثبات</Text>
    <View style={s.types}>
      <TypeChip label="صورة" icon="📷" active={type==="photo"} onPress={()=>setType("photo")}/>
      <TypeChip label="رمز OTP" icon="🔢" active={type==="otp"} onPress={()=>setType("otp")}/>
      <TypeChip label="مرجع يدوي" icon="✍" active={type==="manual"} onPress={()=>setType("manual")}/>
    </View>

    {type==="photo"?<View style={s.photoBox}>
      {image?<Image source={{uri:image.uri}} style={s.preview}/>:<View style={s.photoEmpty}><Text style={s.photoIcon}>📦</Text><Text style={s.photoText}>صوّر إثبات تسليم الطلب بدون إظهار بيانات شخصية غير لازمة.</Text></View>}
      <PrimaryButton label={image?"أعد التقاط الصورة":"التقط صورة إثبات"} tone="secondary" onPress={()=>void choosePhoto()}/>
      {pickerError?<Text style={s.error}>{pickerError}</Text>:null}
    </View>:null}

    {type==="otp"?<FormField
      label="رمز/مرجع الاستلام"
      value={reference}
      onChangeText={setReference}
      keyboardType="number-pad"
      placeholder="مثال: 4821"
    />:null}

    {type==="manual"?<FormField
      label="مرجع التوصيل"
      value={reference}
      onChangeText={setReference}
      placeholder="اكتب مرجع واضح للتسليم"
    />:null}

    <View style={s.gap}/>
    {deliver.isError?<Text style={s.error}>تعذر تسجيل إثبات التوصيل. تأكد من الإثبات والاتصال وحاول ثانية.</Text>:null}
    <PrimaryButton
      label="تأكيد التوصيل وإنهاء المهمة"
      tone="success"
      onPress={()=>deliver.mutate()}
      loading={deliver.isPending}
      disabled={!valid}
    />
  </Screen>;
}

function TypeChip({label,icon,active,onPress}:{label:string;icon:string;active:boolean;onPress():void}){
  return <Pressable onPress={onPress} style={[s.type,active&&s.typeActive]}>
    <Text style={s.typeIcon}>{icon}</Text>
    <Text style={[s.typeText,active&&s.typeTextActive]}>{label}</Text>
  </Pressable>;
}

function normalizeMime(mime?:string|null,fileName?:string|null):LocalImage["mimeType"]|null{
  if(mime==="image/jpeg"||mime==="image/png"||mime==="image/webp")return mime;
  const lower=(fileName??"").toLowerCase();
  if(lower.endsWith(".jpg")||lower.endsWith(".jpeg"))return "image/jpeg";
  if(lower.endsWith(".png"))return "image/png";
  if(lower.endsWith(".webp"))return "image/webp";
  return null;
}

const s=StyleSheet.create({
  header:{flexDirection:"row-reverse",alignItems:"center",gap:12,paddingTop:10,paddingBottom:16},
  back:{fontSize:26},title:{flex:1,fontSize:22,fontWeight:"900",color:colors.ink,textAlign:"right"},
  warning:{backgroundColor:colors.orangeSoft,borderRadius:radius.md,padding:14},
  warningTitle:{fontWeight:"900",color:colors.orangeDark,textAlign:"right",writingDirection:"rtl"},
  warningText:{fontSize:10,color:colors.muted,textAlign:"right",writingDirection:"rtl",lineHeight:17,marginTop:4},
  section:{fontSize:16,fontWeight:"900",color:colors.ink,textAlign:"right",marginTop:20,marginBottom:8},
  types:{flexDirection:"row-reverse",gap:7},
  type:{flex:1,alignItems:"center",borderWidth:1,borderColor:colors.border,borderRadius:radius.md,backgroundColor:colors.surface,paddingVertical:11},
  typeActive:{backgroundColor:colors.orangeSoft,borderColor:colors.orange},
  typeIcon:{fontSize:22},typeText:{fontSize:9,color:colors.muted,marginTop:4},typeTextActive:{color:colors.orangeDark,fontWeight:"900"},
  photoBox:{gap:10,marginTop:14},
  photoEmpty:{minHeight:180,borderWidth:1,borderStyle:"dashed",borderColor:colors.border,borderRadius:radius.card,alignItems:"center",justifyContent:"center",padding:20,backgroundColor:colors.surface},
  photoIcon:{fontSize:40},photoText:{fontSize:10,color:colors.muted,textAlign:"center",writingDirection:"rtl",lineHeight:17,marginTop:8},
  preview:{width:"100%",height:240,borderRadius:radius.card,backgroundColor:colors.soft},
  gap:{height:16},error:{color:colors.danger,textAlign:"center",writingDirection:"rtl",marginVertical:8},
});
