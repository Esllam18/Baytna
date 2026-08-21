import React,{useState} from "react";
import {StyleSheet,Text,TextInput,View} from "react-native";
import {router,useLocalSearchParams} from "expo-router";
import {useMutation} from "@tanstack/react-query";
import {driverApi} from "../../src/api";
import {ApiClientError} from "../../src/api/http";
import {useAuth} from "../../src/auth/AuthProvider";
import {Screen} from "../../src/ui/Screen";
import {PrimaryButton} from "../../src/ui/PrimaryButton";
import {colors,radius} from "../../src/theme/tokens";

export default function VerifyDriverScreen(){
  const params=useLocalSearchParams<{phone:string;developmentOtp?:string}>();
  const phone=String(params.phone??"");
  const [code,setCode]=useState(String(params.developmentOtp??""));
  const auth=useAuth();

  const verify=useMutation({
    mutationFn:()=>driverApi.verifyOtp(phone,code.trim()),
    onSuccess:async()=>{await auth.reload();router.replace("/home");},
  });

  return <Screen>
    <View style={s.hero}>
      <Text style={s.icon}>🔐</Text>
      <Text style={s.title}>أدخل رمز الدخول</Text>
      <Text style={s.text}>بعتنا الرمز على {phone}</Text>
    </View>
    <TextInput
      value={code}
      onChangeText={setCode}
      keyboardType="number-pad"
      maxLength={6}
      style={s.input}
      textAlign="center"
      placeholder="••••••"
      placeholderTextColor="#A2968C"
    />
    {verify.isError?<Text style={s.error}>
      {verify.error instanceof ApiClientError && verify.error.code==="driver_role_required"
        ?"الحساب ده مش حساب مندوب في بيتنا."
        :"رمز الدخول غير صحيح أو انتهت صلاحيته."}
    </Text>:null}
    <PrimaryButton label="دخول" onPress={()=>verify.mutate()} loading={verify.isPending} disabled={code.trim().length<4}/>
  </Screen>;
}
const s=StyleSheet.create({
  hero:{alignItems:"center",paddingVertical:48},icon:{fontSize:52},
  title:{fontSize:24,fontWeight:"900",color:colors.ink,marginTop:10},
  text:{fontSize:12,color:colors.muted,marginTop:5},
  input:{minHeight:58,borderWidth:1,borderColor:colors.border,borderRadius:radius.md,backgroundColor:colors.surface,fontSize:24,fontWeight:"900",letterSpacing:8,marginBottom:12},
  error:{color:colors.danger,textAlign:"center",writingDirection:"rtl",marginBottom:10},
});
