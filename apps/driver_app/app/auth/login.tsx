import React,{useState} from "react";
import {StyleSheet,Text,TextInput,View} from "react-native";
import {router} from "expo-router";
import {useMutation} from "@tanstack/react-query";
import {driverApi} from "../../src/api";
import {Screen} from "../../src/ui/Screen";
import {PrimaryButton} from "../../src/ui/PrimaryButton";
import {colors,radius} from "../../src/theme/tokens";

export default function DriverLoginScreen(){
  const [phone,setPhone]=useState("");
  const send=useMutation({
    mutationFn:()=>driverApi.sendOtp(phone.trim()),
    onSuccess:(result)=>router.push({
      pathname:"/auth/verify",
      params:{phone:phone.trim(),developmentOtp:result.development_otp??""},
    }),
  });

  return <Screen>
    <View style={s.hero}>
      <Text style={s.logo}>🛵</Text>
      <Text style={s.title}>بيتنا للمندوب</Text>
      <Text style={s.subtitle}>استلم المهمة، وصل الطلب، وسجّل إثبات التوصيل.</Text>
    </View>
    <Text style={s.label}>رقم الهاتف</Text>
    <TextInput
      value={phone}
      onChangeText={setPhone}
      keyboardType="phone-pad"
      placeholder="01xxxxxxxxx"
      placeholderTextColor="#A2968C"
      style={s.input}
      textAlign="right"
    />
    {send.isError?<Text style={s.error}>تعذر إرسال رمز الدخول.</Text>:null}
    <PrimaryButton label="إرسال رمز الدخول" onPress={()=>send.mutate()} loading={send.isPending} disabled={phone.trim().length<10}/>
  </Screen>;
}
const s=StyleSheet.create({
  hero:{alignItems:"center",paddingVertical:48},logo:{fontSize:64},
  title:{fontSize:28,fontWeight:"900",color:colors.ink,marginTop:10},
  subtitle:{fontSize:12,color:colors.muted,textAlign:"center",writingDirection:"rtl",marginTop:6},
  label:{fontWeight:"900",color:colors.ink,textAlign:"right",writingDirection:"rtl",marginBottom:7},
  input:{minHeight:52,borderWidth:1,borderColor:colors.border,borderRadius:radius.md,backgroundColor:colors.surface,paddingHorizontal:14,fontSize:16,marginBottom:12},
  error:{color:colors.danger,textAlign:"center",marginBottom:10},
});
