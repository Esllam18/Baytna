import React,{useState} from "react";
import {useParams} from "react-router-dom";
import {useMutation,useQuery,useQueryClient} from "@tanstack/react-query";
import {adminApi} from "../api/admin";
import {keys} from "../query";
import {ErrorBox,Loading,MetricCard,PageTitle,StatusBadge,TextArea} from "../components/Ui";

export function ChefDetailPage(){
  const {chefId=""}=useParams();const qc=useQueryClient();
  const q=useQuery({queryKey:keys.chef(chefId),queryFn:()=>adminApi.chef(chefId),enabled:Boolean(chefId)});
  const [status,setStatus]=useState("active");const [reason,setReason]=useState("");
  const update=useMutation({mutationFn:()=>adminApi.updateChefStatus(chefId,status,reason.trim()||null),onSuccess:()=>qc.invalidateQueries({queryKey:keys.chef(chefId)})});
  if(q.isLoading)return <Loading/>;if(q.isError||!q.data)return <ErrorBox message="الشيف غير موجود."/>;
  const c=q.data;
  return <>
    <PageTitle title={c.display_name} subtitle={`${c.specialty} • ${c.area}`} action={<StatusBadge value={c.status}/>}/>
    <div className="metrics-grid compact">
      <MetricCard label="التقييم" value={`★ ${c.rating.toFixed(1)}`}/>
      <MetricCard label="طلبات مكتملة" value={c.delivered_orders} note={`من ${c.total_orders}`}/>
      <MetricCard label="طلبات نشطة" value={c.active_orders}/>
      <MetricCard label="الأطباق" value={c.dishes_count}/>
      <MetricCard label="التقييمات" value={c.reviews_count} note={`جودة الأكل ${c.avg_food_quality.toFixed(1)}`}/>
      <MetricCard label="دعم مفتوح" value={c.open_support_tickets} tone={c.open_support_tickets?"danger":undefined}/>
    </div>
    <section className="panel">
      <h2>تغيير حالة الشيف</h2>
      <div className="form-row"><label className="field"><span>الحالة الجديدة</span><select value={status} onChange={e=>setStatus(e.target.value)}><option>active</option><option>paused</option><option>suspended</option><option>rejected</option></select></label></div>
      <TextArea label="السبب" value={reason} onChange={e=>setReason(e.target.value)} placeholder="مطلوب عند suspended أو rejected"/>
      {update.isError?<div className="inline-error">تعذر تغيير الحالة. قد يكون السبب مطلوبًا.</div>:null}
      <button className={status==="suspended"||status==="rejected"?"danger-button":"primary"} disabled={update.isPending} onClick={()=>update.mutate()}>حفظ الحالة</button>
    </section>
  </>;
}
