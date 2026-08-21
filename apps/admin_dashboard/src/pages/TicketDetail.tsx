import React,{useState} from "react";
import {useParams} from "react-router-dom";
import {useMutation,useQuery,useQueryClient} from "@tanstack/react-query";
import {adminApi} from "../api/admin";
import {keys} from "../query";
import {ErrorBox,Loading,PageTitle,StatusBadge,TextArea} from "../components/Ui";

export function TicketDetailPage(){
  const {ticketId=""}=useParams();const qc=useQueryClient();
  const q=useQuery({queryKey:keys.ticket(ticketId),queryFn:()=>adminApi.ticket(ticketId),enabled:Boolean(ticketId),refetchInterval:15_000});
  const [body,setBody]=useState("");const [internal,setInternal]=useState(false);
  const [status,setStatus]=useState("investigating");const [resolutionCode,setResolutionCode]=useState("");const [resolutionNote,setResolutionNote]=useState("");

  const refresh=()=>Promise.all([qc.invalidateQueries({queryKey:keys.ticket(ticketId)}),qc.invalidateQueries({queryKey:keys.support}),qc.invalidateQueries({queryKey:["admin","tickets"]})]);
  const assign=useMutation({mutationFn:async()=>{const me=await adminApi.profile();return adminApi.assignTicket(ticketId,me.id)},onSuccess:refresh});
  const message=useMutation({mutationFn:()=>adminApi.messageTicket(ticketId,body.trim(),internal),onSuccess:async()=>{setBody("");await refresh()}});
  const update=useMutation({mutationFn:()=>adminApi.updateTicketStatus(ticketId,status,resolutionCode,resolutionNote),onSuccess:refresh});

  if(q.isLoading)return <Loading/>;if(q.isError||!q.data)return <ErrorBox message="التذكرة غير موجودة."/>;
  const t=q.data;const closed=["resolved","closed"].includes(t.status);

  return <>
    <PageTitle title={t.subject} subtitle={`${t.category} • ${t.priority}`} action={<StatusBadge value={t.status}/>}/>
    <div className="detail-grid">
      <section className="panel">
        <h2>وصف المشكلة</h2><p className="rtl-copy">{t.description}</p>
        <div className="kv"><span>العميل</span><strong>{t.customer_id}</strong></div>
        <div className="kv"><span>الطلب</span><strong>{t.order_id??"غير مرتبط"}</strong></div>
        <div className="kv"><span>المسؤول</span><strong>{t.assigned_admin_id??"غير معيّن"}</strong></div>
        {!t.assigned_admin_id?<button className="primary" onClick={()=>assign.mutate()} disabled={assign.isPending}>تعيين لنفسي</button>:null}
      </section>
      <section className="panel">
        <h2>تغيير الحالة</h2>
        <label className="field"><span>الحالة</span><select value={status} onChange={e=>setStatus(e.target.value)}><option>assigned</option><option>investigating</option><option>awaiting_customer</option><option>awaiting_internal</option><option>resolved</option><option>closed</option></select></label>
        {["resolved","closed"].includes(status)?<><label className="field"><span>كود الحل</span><input value={resolutionCode} onChange={e=>setResolutionCode(e.target.value)}/></label><TextArea label="ملاحظات الحل" value={resolutionNote} onChange={e=>setResolutionNote(e.target.value)}/></>:null}
        <button className="primary" onClick={()=>update.mutate()} disabled={update.isPending}>حفظ الحالة</button>
      </section>
    </div>

    <section className="panel">
      <h2>المحادثة</h2>
      <div className="messages">{t.messages.map(m=><div className={`message ${m.is_internal?"internal":m.sender_role==="customer"?"customer":"admin"}`} key={m.id}>
        <div className="message-head"><strong>{m.is_internal?"ملاحظة داخلية":m.sender_role==="customer"?"العميل":"فريق بيتنا"}</strong><small>{new Date(m.created_at).toLocaleString("ar-EG")}</small></div>
        <p>{m.body}</p>
      </div>)}</div>
      {!closed?<div className="reply-box">
        <TextArea label={internal?"ملاحظة داخلية — لا تظهر للعميل":"رد للعميل"} value={body} onChange={e=>setBody(e.target.value)}/>
        <label className="check"><input type="checkbox" checked={internal} onChange={e=>setInternal(e.target.checked)}/> ملاحظة داخلية</label>
        <button className={internal?"secondary-button":"primary"} onClick={()=>message.mutate()} disabled={body.trim().length<1||message.isPending}>{internal?"حفظ ملاحظة داخلية":"إرسال الرد"}</button>
      </div>:<div className="resolved-box">التذكرة مغلقة. {t.resolution_note??""}</div>}
    </section>
  </>;
}
