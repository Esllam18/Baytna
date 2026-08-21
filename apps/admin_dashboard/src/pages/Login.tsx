import React,{useState} from "react";
import {useMutation} from "@tanstack/react-query";
import {Navigate} from "react-router-dom";
import {adminApi} from "../api/admin";
import {ApiError} from "../api/http";
import {useAuth} from "../auth/AuthProvider";

export function LoginPage(){
  const auth=useAuth();
  const [phone,setPhone]=useState("");
  const [code,setCode]=useState("");
  const [devOtp,setDevOtp]=useState("");
  const [step,setStep]=useState<"phone"|"code">("phone");

  const send=useMutation({
    mutationFn:()=>adminApi.sendOtp(phone.trim()),
    onSuccess:r=>{setDevOtp(r.development_otp??"");setCode(r.development_otp??"");setStep("code")},
  });
  const verify=useMutation({
    mutationFn:()=>adminApi.verifyOtp(phone.trim(),code.trim()),
    onSuccess:()=>void auth.reload(),
  });

  if(auth.authenticated)return <Navigate to="/" replace/>;

  return <div className="login-page">
    <div className="login-card">
      <div className="login-logo">🏠</div>
      <h1>لوحة إدارة بيتنا</h1>
      <p>دخول فريق العمليات والإدارة فقط.</p>
      {step==="phone"?<>
        <label className="field"><span>رقم الهاتف</span><input value={phone} onChange={e=>setPhone(e.target.value)} placeholder="01xxxxxxxxx" dir="ltr"/></label>
        {send.isError?<div className="inline-error">تعذر إرسال رمز الدخول.</div>:null}
        <button className="primary" disabled={phone.trim().length<10||send.isPending} onClick={()=>send.mutate()}>{send.isPending?"جاري الإرسال...":"إرسال رمز الدخول"}</button>
      </>:<>
        <label className="field"><span>رمز الدخول</span><input value={code} onChange={e=>setCode(e.target.value)} placeholder="••••••" dir="ltr"/></label>
        {devOtp?<small className="dev-note">Development OTP: {devOtp}</small>:null}
        {verify.isError?<div className="inline-error">{verify.error instanceof ApiError&&verify.error.code==="admin_role_required"?"الحساب ده مش حساب إدارة.":"الرمز غير صحيح أو انتهت صلاحيته."}</div>:null}
        <button className="primary" disabled={code.trim().length<4||verify.isPending} onClick={()=>verify.mutate()}>{verify.isPending?"جاري الدخول...":"دخول"}</button>
        <button className="ghost" onClick={()=>setStep("phone")}>تغيير الرقم</button>
      </>}
    </div>
  </div>;
}
