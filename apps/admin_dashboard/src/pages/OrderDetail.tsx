import React,{useState} from "react";
import {Link,useParams} from "react-router-dom";
import {useMutation,useQuery,useQueryClient} from "@tanstack/react-query";
import {adminApi} from "../api/admin";
import {keys} from "../query";
import {ErrorBox,Loading,Money,PageTitle,StatusBadge,TextArea} from "../components/Ui";

export function OrderDetailPage(){
  const {orderId=""}=useParams();
  const qc=useQueryClient();
  const q=useQuery({queryKey:keys.order(orderId),queryFn:()=>adminApi.order(orderId),enabled:Boolean(orderId)});
  const [note,setNote]=useState("");
  const [refundEgp,setRefundEgp]=useState("");
  const [refundReason,setRefundReason]=useState("");

  const refresh=()=>qc.invalidateQueries({queryKey:keys.order(orderId)});
  const noteMutation=useMutation({mutationFn:()=>adminApi.addOrderNote(orderId,note.trim()),onSuccess:async()=>{setNote("");await refresh()}});
  const refund=useMutation({mutationFn:()=>adminApi.createRefund(orderId,Math.round(Number(refundEgp)*100),refundReason.trim()),onSuccess:async()=>{setRefundEgp("");setRefundReason("");await refresh()}});

  if(q.isLoading)return <Loading label="بنفتح الطلب..."/>;
  if(q.isError||!q.data)return <ErrorBox message="الطلب غير موجود أو تعذر تحميله."/>;
  const d=q.data,o=d.order;

  return <>
    <PageTitle title={`طلب #${o.id.slice(0,8).toUpperCase()}`} subtitle={`${o.customer_name||"عميل"} • ${o.chef_name}`} action={<StatusBadge value={o.status}/>}/>
    <div className="detail-grid">
      <section className="panel">
        <h2>ملخص الطلب</h2>
        <div className="kv"><span>الإجمالي</span><strong><Money minor={o.total_minor}/></strong></div>
        <div className="kv"><span>الخصم</span><strong><Money minor={o.discount_minor}/></strong></div>
        <div className="kv"><span>الدفع</span><StatusBadge value={o.payment_status}/></div>
        <div className="kv"><span>التوصيل</span><StatusBadge value={o.delivery_status}/></div>
        <div className="kv"><span>الخدمة</span><strong>{o.service_date}</strong></div>
        <div className="kv"><span>وعد التوصيل</span><strong>{o.promised_delivery_window_start_at&&o.promised_delivery_window_end_at?formatPromise(o.promised_delivery_window_start_at,o.promised_delivery_window_end_at,o.promised_delivery_timezone):"غير مسجل"}</strong></div>
        {d.delivery?<div className="kv"><span>نتيجة التوقيت</span><strong>{timingLabel(String(d.delivery.delivery_timing_status??""),Number(d.delivery.late_by_minutes??0))}</strong></div>:null}
      </section>
      <section className="panel"><h2>العنوان</h2><p className="rtl-copy">{d.delivery_address?Object.values(d.delivery_address).filter(Boolean).join("، "):"غير متاح"}</p><p className="muted">رقم العميل ظاهر بصيغة مخفية فقط: {o.customer_phone_masked}</p></section>
    </div>

    <section className="panel">
      <h2>الأكلات</h2>
      <div className="table-wrap"><table><thead><tr><th>الصنف</th><th>الكمية</th><th>سعر الوحدة</th><th>الإجمالي</th></tr></thead><tbody>
        {d.items.map((x,i)=><tr key={String(x.id??i)}><td>{String(x.dish_name??"")}</td><td>{String(x.quantity??"")}</td><td><Money minor={Number(x.unit_price_minor??0)}/></td><td><Money minor={Number(x.line_total_minor??0)}/></td></tr>)}
      </tbody></table></div>
    </section>

    <div className="detail-grid">
      <section className="panel"><h2>Timeline</h2><div className="timeline">{d.timeline.map((e,i)=><div key={i}><span className="timeline-dot"/><div><strong>{String(e.to_status??"")}</strong><small>{String(e.created_at??"")}</small><p>{String(e.reason??"")}</p></div></div>)}</div></section>
      <section className="panel"><h2>ملاحظات الإدارة</h2>{d.notes.map(n=><div className="note" key={n.id}><p>{n.note}</p><small>{new Date(n.created_at).toLocaleString("ar-EG")}</small></div>)}
        <TextArea label="ملاحظة جديدة" value={note} onChange={e=>setNote(e.target.value)}/>
        <button className="primary" disabled={note.trim().length<2||noteMutation.isPending} onClick={()=>noteMutation.mutate()}>إضافة ملاحظة</button>
      </section>
    </div>

    <section className="panel danger-panel">
      <h2>استرداد مالي</h2><p className="muted">الاسترداد يتم عبر مزود الدفع الحالي ويخضع لقواعد المبلغ المتاح للاسترداد.</p>
      <div className="form-row"><label className="field"><span>المبلغ بالجنيه</span><input type="number" min="0" step="0.01" value={refundEgp} onChange={e=>setRefundEgp(e.target.value)}/></label>
      <label className="field grow"><span>السبب</span><input value={refundReason} onChange={e=>setRefundReason(e.target.value)}/></label></div>
      {refund.isError?<div className="inline-error">تعذر تنفيذ الاسترداد. راجع المبلغ وحالة الدفع.</div>:null}
      <button className="danger-button" disabled={Number(refundEgp)<=0||refundReason.trim().length<3||refund.isPending} onClick={()=>refund.mutate()}>تنفيذ الاسترداد</button>
    </section>

    {d.support_tickets.length?<section className="panel"><h2>تذاكر الدعم المرتبطة</h2>{d.support_tickets.map((x,i)=><Link key={i} className="row-link" to={`/support/${String(x.id)}`}>{String(x.subject)} <StatusBadge value={String(x.status)}/></Link>)}</section>:null}
  </>;
}


function formatPromise(start:string,end:string,timeZone:string|null){
  const options:Intl.DateTimeFormatOptions={hour:"2-digit",minute:"2-digit"};
  if(timeZone)options.timeZone=timeZone;
  return `${new Date(start).toLocaleTimeString("ar-EG",options)} – ${new Date(end).toLocaleTimeString("ar-EG",options)}`;
}

function timingLabel(status:string,lateBy:number){
  if(status==="on_time")return "On time ✓";
  if(status==="late")return `Late by ${lateBy} min`;
  if(status==="unmeasurable")return "Unmeasurable";
  return "Pending";
}
